#!/bin/bash
#
# gen-local-certs.sh - Generiere Self-Signed SSL Zertifikate für lokales Testing
#
# Diese Zertifikate sind NUR für Development/Testing gedacht!
# Für Production nutze Let's Encrypt (./scripts/init-ssl.sh)
#
# Usage:
#   ./scripts/gen-local-certs.sh [domain]
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

# Domain (default: localhost)
DOMAIN="${1:-localhost}"
SSL_DIR="nginx/ssl"
CERT_FILE="${SSL_DIR}/fullchain.pem"
KEY_FILE="${SSL_DIR}/privkey.pem"

echo ""
info "🔐 Generating Self-Signed SSL Certificate for ${DOMAIN}"
echo ""

# Create SSL directory
mkdir -p "$SSL_DIR"

# Generate private key
log "Generating private key..."
openssl genrsa -out "$KEY_FILE" 2048 2>/dev/null

# Generate certificate signing request (CSR)
log "Generating certificate signing request..."
openssl req -new -key "$KEY_FILE" \
    -out "${SSL_DIR}/cert.csr" \
    -subj "/C=DE/ST=Berlin/L=Berlin/O=KI-Campus/OU=Arena/CN=${DOMAIN}" \
    2>/dev/null

# Generate self-signed certificate (valid for 365 days)
log "Generating self-signed certificate (valid for 365 days)..."
openssl x509 -req \
    -days 365 \
    -in "${SSL_DIR}/cert.csr" \
    -signkey "$KEY_FILE" \
    -out "$CERT_FILE" \
    -extfile <(printf "subjectAltName=DNS:${DOMAIN},DNS:*.${DOMAIN},DNS:localhost,IP:127.0.0.1") \
    2>/dev/null

# Cleanup CSR
rm -f "${SSL_DIR}/cert.csr"

# Set permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo ""
log "✅ Self-signed SSL certificate created!"
echo ""
info "📁 Certificate files:"
echo "   • Certificate: $CERT_FILE"
echo "   • Private Key: $KEY_FILE"
echo ""
info "🔍 Certificate details:"
openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Issuer:|Not Before|Not After|DNS:)" | sed 's/^/   /'
echo ""
warn "⚠️  Browser Warning:"
echo "   Your browser will show a security warning because this is"
echo "   a self-signed certificate. This is NORMAL for local testing."
echo ""
echo "   To trust the certificate:"
echo "   • Chrome: Click 'Advanced' → 'Proceed to localhost (unsafe)'"
echo "   • Firefox: Click 'Advanced' → 'Accept the Risk and Continue'"
echo "   • Safari: Click 'Show Details' → 'visit this website'"
echo ""
info "🚀 Next steps:"
echo "   1. Use docker-compose.local.yml for testing:"
echo "      docker compose -f docker-compose.local.yml up -d"
echo ""
echo "   2. Access your local Arena:"
echo "      https://${DOMAIN}/"
echo ""
echo "   3. For production, use Let's Encrypt:"
echo "      ./scripts/init-ssl.sh your-domain.com admin@example.com"
echo ""
