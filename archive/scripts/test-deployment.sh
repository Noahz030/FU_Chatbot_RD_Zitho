#!/bin/bash
#
# test-deployment.sh - End-to-End Deployment Test (Local)
#
# Führt kompletten Deployment-Flow lokal durch mit self-signed SSL
# Testet alle Production-Features ohne echte VM
#
# Usage:
#   ./scripts/test-deployment.sh [--clean]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1" >&2; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

# Check for --clean flag
CLEAN_START=false
if [[ "$1" == "--clean" ]]; then
    CLEAN_START=true
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Arena End-to-End Deployment Test (Local)             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Prerequisites
info "Step 1/9: Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { error "Docker not installed"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { error "Docker Compose not installed"; exit 1; }
command -v openssl >/dev/null 2>&1 || { error "OpenSSL not installed"; exit 1; }
command -v curl >/dev/null 2>&1 || { error "curl not installed"; exit 1; }
log "All prerequisites met"

# Step 2: Clean up (if requested)
if [ "$CLEAN_START" = true ]; then
    info "Step 2/9: Cleaning up previous test environment..."
    docker compose -f docker-compose.local.yml down -v 2>/dev/null || true
    rm -rf nginx/ssl/*.pem 2>/dev/null || true
    log "Cleanup complete"
else
    info "Step 2/9: Skipping cleanup (use --clean for fresh start)"
fi

# Step 3: Generate self-signed SSL certificates
info "Step 3/9: Generating self-signed SSL certificates..."
if [ ! -f nginx/ssl/fullchain.pem ] || [ ! -f nginx/ssl/privkey.pem ]; then
    ./scripts/gen-local-certs.sh localhost >/dev/null 2>&1
    log "SSL certificates generated"
else
    log "SSL certificates already exist"
fi

# Step 4: Validate .env file
info "Step 4/9: Validating .env configuration..."
if [ ! -f .env ]; then
    error ".env file not found. Run: cp .env.example .env"
    exit 1
fi

# Check required variables
required_vars=("AZURE_OPENAI_URL" "AZURE_OPENAI_API_KEY" "PROD_QDRANT_URL" "PROD_QDRANT_API_KEY")
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env; then
        warn "Missing ${var} in .env"
    fi
done
log ".env file exists"

# Step 5: Build Docker images
info "Step 5/9: Building Docker images..."
docker compose -f docker-compose.local.yml build --quiet 2>&1 | grep -i error || true
log "Docker images built"

# Step 6: Start services
info "Step 6/9: Starting services..."
docker compose -f docker-compose.local.yml up -d
sleep 5
log "Services started"

# Step 7: Wait for services to be healthy
info "Step 7/9: Waiting for services to become healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker compose -f docker-compose.local.yml ps | grep -q "healthy"; then
        log "Services are healthy"
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    error "Services did not become healthy in time"
    docker compose -f docker-compose.local.yml logs --tail=50
    exit 1
fi
echo ""

# Step 8: Run health checks
info "Step 8/9: Running comprehensive health checks..."

# Check HTTP redirect
http_redirect=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
if [ "$http_redirect" == "301" ]; then
    log "HTTP → HTTPS redirect working"
else
    warn "HTTP redirect: $http_redirect (expected 301)"
fi

# Check HTTPS with self-signed cert (insecure is OK for testing)
https_status=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/ || echo "000")
if [ "$https_status" == "200" ]; then
    log "HTTPS UI accessible"
else
    error "HTTPS UI failed: $https_status"
fi

# Check API health
api_health=$(curl -k -s https://localhost/health || echo "FAIL")
if echo "$api_health" | grep -q "healthy"; then
    log "API health check passed"
else
    error "API health check failed"
fi

# Check Arena statistics
stats=$(curl -k -s https://localhost/arena/statistics || echo "{}")
total_comparisons=$(echo "$stats" | python3 -c "import json, sys; print(json.load(sys.stdin).get('total_comparisons', 0))" 2>/dev/null || echo "0")
log "Arena statistics: $total_comparisons comparisons"

# Check Docker containers
containers=("arena-api-local" "arena-ui-local" "arena-nginx-local" "arena-postgres-local")
all_running=true
for container in "${containers[@]}"; do
    status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
    if [ "$status" == "running" ]; then
        log "  ✓ $container: running"
    else
        error "  ✗ $container: $status"
        all_running=false
    fi
done

# Step 9: Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$all_running" = true ] && [ "$https_status" == "200" ]; then
    echo -e "${GREEN}✅ DEPLOYMENT TEST PASSED!${NC}"
    echo ""
    info "🌐 Local Arena is accessible at:"
    echo "   • HTTPS: https://localhost/"
    echo "   • Voting UI: https://localhost/"
    echo "   • Results: https://localhost/results"
    echo "   • API: https://localhost/arena/statistics"
    echo ""
    warn "⚠️  Browser will show SSL warning (normal for self-signed certs)"
    echo "   Click 'Advanced' → 'Proceed to localhost (unsafe)'"
    echo ""
    info "📊 Next steps:"
    echo "   1. Test voting: https://localhost/"
    echo "   2. Check logs: docker compose -f docker-compose.local.yml logs"
    echo "   3. View stats: curl -k https://localhost/arena/statistics | python3 -m json.tool"
    echo "   4. Stop services: docker compose -f docker-compose.local.yml down"
    echo ""
    exit 0
else
    echo -e "${RED}❌ DEPLOYMENT TEST FAILED!${NC}"
    echo ""
    error "Some services are not healthy. Check logs:"
    echo "   docker compose -f docker-compose.local.yml logs"
    echo ""
    exit 1
fi
