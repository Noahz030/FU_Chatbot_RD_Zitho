#!/bin/bash
#
# gen-secrets.sh - Generiert sichere Secrets für Production
#
# Usage:
#   ./scripts/gen-secrets.sh                    # Generiert 5 Secrets
#   ./scripts/gen-secrets.sh --count 10         # Generiert 10 Secrets
#   ./scripts/gen-secrets.sh --for postgres     # Generiert Postgres-Passwort
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }

# Defaults
COUNT=5
PURPOSE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --count)
            COUNT=$2
            shift 2
            ;;
        --for)
            PURPOSE=$2
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
info "🔐 Secret Generator für Arena Production"
echo ""

if [ -z "$PURPOSE" ]; then
    # Generate multiple random secrets
    echo "Generating $COUNT secure secrets (32 bytes each):"
    echo ""
    
    for ((i=1; i<=COUNT; i++)); do
        secret=$(openssl rand -hex 32)
        echo "  Secret $i: $secret"
    done
else
    # Generate specific secret based on purpose
    case $PURPOSE in
        postgres)
            info "Postgresql Password (32 Bytes)"
            echo ""
            echo "  POSTGRES_PASSWORD=$(openssl rand -hex 32)"
            ;;
        arena)
            info "Arena API Key (32 Bytes)"
            echo ""
            echo "  ARENA_API_KEY=$(openssl rand -hex 32)"
            ;;
        rest)
            info "REST API Key (32 Bytes)"
            echo ""
            echo "  $(openssl rand -hex 32)"
            ;;
        *)
            echo "Unknown purpose: $PURPOSE"
            echo "Available: postgres, arena, rest"
            exit 1
            ;;
    esac
fi

echo ""
info "💡 Verwendung:"
echo "   1. Secret kopieren"
echo "   2. In .env eintragen: VAR_NAME=<secret>"
echo "   3. Oder direkt in .env schreiben:"
echo "      sed -i \"s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 32)/\" .env"
echo ""
info "⚠️  Wichtig:"
echo "   • Niemals Secrets in Logs oder Terminal-History speichern"
echo "   • .env Datei niemals in Git committen"
echo "   • chmod 600 .env aufführen"
echo "   • In Production: Nutze Azure Key Vault statt .env"
echo ""
