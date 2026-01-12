#!/bin/bash
#
# init-ssl.sh - Initialize SSL certificates with Let's Encrypt
# 
# Usage:
#   ./scripts/init-ssl.sh <domain> <email>
#
# Example:
#   ./scripts/init-ssl.sh arena.example.com admin@example.com
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - Domain DNS pointing to server IP
#   - Ports 80/443 open in firewall
#

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check arguments
if [ "$#" -ne 2 ]; then
    error "Usage: $0 <domain> <email>"
    echo ""
    echo "Example: $0 arena.example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

log "🔐 Initializing SSL certificates for ${BLUE}${DOMAIN}${NC}"

# Validate domain format
if [[ ! $DOMAIN =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$ ]]; then
    error "Invalid domain format: ${DOMAIN}"
    exit 1
fi

# Validate email format
if [[ ! $EMAIL =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
    error "Invalid email format: ${EMAIL}"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    warning ".env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log "Created .env from .env.example"
    else
        error "No .env or .env.example file found. Please create one."
        exit 1
    fi
fi

# Update DOMAIN_NAME in .env
if grep -q "^DOMAIN_NAME=" .env; then
    sed -i.bak "s/^DOMAIN_NAME=.*/DOMAIN_NAME=${DOMAIN}/" .env
    log "Updated DOMAIN_NAME in .env"
else
    echo "DOMAIN_NAME=${DOMAIN}" >> .env
    log "Added DOMAIN_NAME to .env"
fi

# Create temporary nginx config for HTTP-only (ACME challenge)
log "📝 Creating temporary HTTP-only nginx configuration..."

cat > nginx/nginx.conf.tmp << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;

    server {
        listen 80;
        server_name _;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 'SSL initialization in progress...';
            add_header Content-Type text/plain;
        }
    }
}
EOF

# Backup original nginx config
if [ -f nginx/nginx.conf ]; then
    cp nginx/nginx.conf nginx/nginx.conf.backup
    log "Backed up original nginx.conf"
fi

# Use temporary config
cp nginx/nginx.conf.tmp nginx/nginx.conf

# Start nginx with temporary config
log "🚀 Starting nginx for ACME challenge..."
docker compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx to be ready
sleep 5

# Request certificate from Let's Encrypt
log "📜 Requesting SSL certificate from Let's Encrypt..."
log "Domain: ${DOMAIN}"
log "Email: ${EMAIL}"

docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email ${EMAIL} \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d ${DOMAIN}

# Check if certificate was created
if docker compose -f docker-compose.prod.yml exec certbot test -d "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"; then
    log "✅ Certificate successfully obtained!"
else
    error "Certificate creation failed. Please check the logs above."
    
    # Restore original config
    if [ -f nginx/nginx.conf.backup ]; then
        mv nginx/nginx.conf.backup nginx/nginx.conf
        log "Restored original nginx.conf"
    fi
    
    exit 1
fi

# Restore original nginx config with SSL
if [ -f nginx/nginx.conf.backup ]; then
    mv nginx/nginx.conf.backup nginx/nginx.conf
    log "Restored SSL-enabled nginx.conf"
fi

# Update nginx config with actual domain name
sed -i.bak "s/server_name _;/server_name ${DOMAIN};/g" nginx/nginx.conf
log "Updated server_name in nginx.conf to ${DOMAIN}"

# Restart services with SSL enabled
log "🔄 Restarting services with SSL enabled..."
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
log "⏳ Waiting for services to become healthy..."
sleep 10

# Verify SSL
log "🔍 Verifying SSL configuration..."

if curl -fsS --max-time 5 https://${DOMAIN}/health >/dev/null 2>&1; then
    echo ""
    log "✅ ${GREEN}SSL setup complete!${NC}"
    echo ""
    log "🌐 Your services are now available at:"
    echo "   • https://${DOMAIN} (Voting UI)"
    echo "   • https://${DOMAIN}/arena/ (Arena API)"
    echo "   • https://${DOMAIN}/results (Results Page)"
    echo ""
    log "🔐 Certificate details:"
    docker compose -f docker-compose.prod.yml exec certbot certbot certificates
    echo ""
    log "♻️  Auto-renewal: Enabled (certbot container runs renewal check every 12h)"
    echo ""
else
    warning "SSL configuration completed, but HTTPS verification failed."
    warning "This might be a DNS propagation issue. Please verify manually:"
    echo ""
    echo "   curl -I https://${DOMAIN}/health"
    echo ""
fi

# Cleanup
rm -f nginx/nginx.conf.tmp
rm -f nginx/nginx.conf.bak

log "🎉 SSL initialization complete!"
