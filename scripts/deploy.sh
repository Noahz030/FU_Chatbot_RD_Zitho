#!/usr/bin/env bash
set -euo pipefail

# Arena Deployment Script
# Manages full deployment lifecycle: build, start, stop, healthcheck, backup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_ROOT}/.env"
LOG_FILE="/var/log/arena-deploy.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_requirements() {
    log "Checking requirements..."
    
    [[ -f "$COMPOSE_FILE" ]] || error "docker-compose.prod.yml not found at $COMPOSE_FILE"
    [[ -f "$ENV_FILE" ]] || error ".env file not found at $ENV_FILE"
    
    command -v docker >/dev/null 2>&1 || error "Docker not installed"
    command -v docker-compose >/dev/null 2>&1 || error "Docker Compose not installed"
    
    log "✅ All requirements met"
}

# Build images
build_images() {
    log "Building Docker images..."
    cd "$PROJECT_ROOT"
    
    docker-compose -f "$COMPOSE_FILE" build --no-cache || error "Build failed"
    
    log "✅ Images built successfully"
}

# Start services
start_services() {
    log "Starting services..."
    cd "$PROJECT_ROOT"
    
    docker-compose -f "$COMPOSE_FILE" up -d || error "Failed to start services"
    
    log "⏳ Waiting for services to be healthy..."
    sleep 10
    
    log "✅ Services started"
}

# Stop services
stop_services() {
    log "Stopping services..."
    cd "$PROJECT_ROOT"
    
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans || error "Failed to stop services"
    
    log "✅ Services stopped"
}

# Health check
healthcheck() {
    log "Running health checks..."
    
    local api_health
    local ui_health
    
    api_health=$(curl -fsS http://127.0.0.1:8001/health || echo "FAIL")
    ui_health=$(curl -fsS http://127.0.0.1:8002/ | head -1 | grep -q "<!DOCTYPE" && echo "OK" || echo "FAIL")
    
    if [[ "$api_health" == "FAIL" ]]; then
        error "API health check failed"
    fi
    
    if [[ "$ui_health" != "OK" ]]; then
        error "UI health check failed"
    fi
    
    log "✅ All health checks passed"
    
    # Show stats
    log "Arena Statistics:"
    curl -fsS http://127.0.0.1:8001/arena/statistics | python -m json.tool | head -20
}

# Status
status() {
    log "Service status:"
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" ps
}

# Logs
logs() {
    cd "$PROJECT_ROOT"
    docker-compose -f "$COMPOSE_FILE" logs -f "$@"
}

# Backup JSONL
backup() {
    local backup_dir="/var/backups/arena"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="${backup_dir}/arena_votes_${timestamp}.jsonl"
    
    log "Creating backup: $backup_file"
    
    mkdir -p "$backup_dir"
    
    docker run --rm \
        -v fu_arena_data:/data \
        -v "$backup_dir:/bkp" \
        alpine \
        sh -c "cp /data/arena_votes.jsonl /bkp/arena_votes_${timestamp}.jsonl" || \
        error "Backup failed"
    
    # Keep only last 30 days of backups
    find "$backup_dir" -name "arena_votes_*.jsonl" -mtime +30 -delete
    
    log "✅ Backup created: $backup_file"
}

# Restore from backup
restore() {
    local backup_file="$1"
    
    [[ -f "$backup_file" ]] || error "Backup file not found: $backup_file"
    
    log "Restoring from: $backup_file"
    
    docker run --rm \
        -v fu_arena_data:/data \
        -v "$(dirname "$backup_file"):/bkp" \
        alpine \
        sh -c "cp /bkp/$(basename "$backup_file") /data/arena_votes.jsonl" || \
        error "Restore failed"
    
    log "✅ Backup restored"
}

# Deploy (full cycle)
deploy() {
    log "🚀 Starting full deployment..."
    check_requirements
    build_images
    stop_services || true
    start_services
    healthcheck
    log "🎉 Deployment complete!"
}

# Usage
usage() {
    cat << EOF
Usage: $0 {command} [args]

Commands:
    deploy          Full deployment (build, start, health)
    build           Build Docker images
    start           Start all services
    stop            Stop all services
    status          Show service status
    logs [service]  View logs (optional: specify service)
    health          Run health checks
    backup          Create backup of arena_votes.jsonl
    restore <file>  Restore backup from file
    help            Show this help message

Examples:
    $0 deploy
    $0 logs arena-api
    $0 backup
    $0 restore /var/backups/arena/arena_votes_20250101-120000.jsonl

EOF
}

# Main
main() {
    local command="${1:-help}"
    
    case "$command" in
        deploy)
            deploy
            ;;
        build)
            check_requirements
            build_images
            ;;
        start)
            check_requirements
            start_services
            ;;
        stop)
            stop_services
            ;;
        status)
            status
            ;;
        logs)
            logs "${2:-}"
            ;;
        health)
            healthcheck
            ;;
        backup)
            backup
            ;;
        restore)
            restore "${2:-}"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            error "Unknown command: $command"
            ;;
    esac
}

main "$@"
