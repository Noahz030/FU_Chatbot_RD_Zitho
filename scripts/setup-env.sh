#!/bin/bash
#
# setup-env.sh - Environment configuration setup script
#
# This script helps generate a production-ready .env file from template,
# validates required settings, and generates secure secrets.
#
# Usage:
#   ./scripts/setup-env.sh [--validate-only] [--generate-secrets]
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
log() { echo -e "${GREEN}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

# Check if .env already exists
if [ -f .env ]; then
    warning ".env file already exists"
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Keeping existing .env file"
        exit 0
    fi
fi

# Initialize .env from template
log "Creating .env from template..."
if [ -f .env.prod.example ]; then
    cp .env.prod.example .env
    chmod 600 .env
    log "Created .env with restricted permissions (600)"
else
    error ".env.prod.example not found"
    exit 1
fi

# Function to prompt for value
prompt_value() {
    local var_name=$1
    local description=$2
    local current_value=$3
    local is_secret=$4
    
    if [ -z "$current_value" ]; then
        current_value="(required)"
    fi
    
    echo ""
    info "$description"
    if [ "$is_secret" == "true" ]; then
        echo -n "Enter ${var_name} [${current_value}] (hidden): "
        read -s value
        echo
    else
        echo -n "Enter ${var_name} [${current_value}]: "
        read value
    fi
    
    if [ -n "$value" ]; then
        # Escape special characters for sed
        value=$(printf '%s\n' "$value" | sed -e 's/[\/&]/\\&/g')
        sed -i.bak "s/^${var_name}=.*/${var_name}=${value}/" .env
        log "Set $var_name"
    fi
}

# Function to generate secure secret
generate_secret() {
    local var_name=$1
    local length=${2:-32}
    
    local secret=$(openssl rand -hex $((length / 2)))
    secret=$(printf '%s\n' "$secret" | sed -e 's/[\/&]/\\&/g')
    sed -i.bak "s/^${var_name}=.*/${var_name}=${secret}/" .env
    log "Generated secure ${var_name}: ${secret:0:16}..."
}

# Function to validate required variables
validate_env() {
    local required_vars=(
        "ENVIRONMENT"
        "DOMAIN_NAME"
        "POSTGRES_PASSWORD"
        "ARENA_API_KEY"
        "AZURE_OPENAI_URL"
        "AZURE_OPENAI_API_KEY"
        "PROD_QDRANT_URL"
        "PROD_QDRANT_API_KEY"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env || grep "^${var}=.*placeholder\|^${var}=.*your_\|^${var}=.*change_\|^${var}=$" .env >/dev/null; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        error "Missing or placeholder values for:"
        for var in "${missing_vars[@]}"; do
            echo "  • $var"
        done
        return 1
    fi
    
    return 0
}

# Main flow
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Arena Production Environment Configuration Setup     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for --generate-secrets flag
if [[ "$*" == *"--generate-secrets"* ]]; then
    log "Generating secure secrets..."
    generate_secret "POSTGRES_PASSWORD" 32
    generate_secret "ARENA_API_KEY" 32
    log "Secrets generated successfully"
fi

# Interactive configuration
read -p "Start interactive configuration? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Starting interactive configuration..."
    
    echo ""
    echo -e "${YELLOW}=== GENERAL CONFIGURATION ===${NC}"
    
    prompt_value "DOMAIN_NAME" "What is your domain name?" "arena.ki-campus.org"
    
    echo ""
    echo -e "${YELLOW}=== SECURITY CONFIGURATION ===${NC}"
    
    # Check if secrets already have placeholder values
    current_postgres=$(grep "^POSTGRES_PASSWORD=" .env | cut -d= -f2)
    if [[ $current_postgres == *"your_"* ]] || [[ $current_postgres == *"change_"* ]]; then
        read -p "Auto-generate secure POSTGRES_PASSWORD? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            generate_secret "POSTGRES_PASSWORD" 32
        else
            prompt_value "POSTGRES_PASSWORD" "PostgreSQL password (min 32 chars)" "" "true"
        fi
    fi
    
    current_arena=$(grep "^ARENA_API_KEY=" .env | cut -d= -f2)
    if [[ $current_arena == *"your_"* ]] || [[ $current_arena == *"change_"* ]]; then
        read -p "Auto-generate secure ARENA_API_KEY? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            generate_secret "ARENA_API_KEY" 32
        else
            prompt_value "ARENA_API_KEY" "Arena API Key (min 32 chars)" "" "true"
        fi
    fi
    
    prompt_value "REST_API_KEYS" "REST API Keys (comma-separated)"
    prompt_value "CORS_ORIGINS" "CORS Origins (comma-separated)" "https://arena.ki-campus.org"
    
    echo ""
    echo -e "${YELLOW}=== AZURE OPENAI CONFIGURATION ===${NC}"
    
    prompt_value "AZURE_OPENAI_URL" "Azure OpenAI URL" "https://your-resource.openai.azure.com/"
    prompt_value "AZURE_OPENAI_API_KEY" "Azure OpenAI API Key" "" "true"
    
    echo ""
    echo -e "${YELLOW}=== QDRANT CONFIGURATION ===${NC}"
    
    prompt_value "PROD_QDRANT_URL" "Qdrant Production URL" "https://your-qdrant-instance.cloud.qdrant.io"
    prompt_value "PROD_QDRANT_API_KEY" "Qdrant API Key" "" "true"
    
    echo ""
    echo -e "${YELLOW}=== AZURE KEY VAULT (OPTIONAL) ===${NC}"
    
    prompt_value "USE_KEY_VAULT" "Use Azure Key Vault? (true/false)" "true"
    prompt_value "KEY_VAULT_NAME" "Key Vault name (if enabled)" "kicwa-keyvault-prod"
    
    echo ""
    echo -e "${YELLOW}=== OPTIONAL SERVICES ===${NC}"
    
    read -p "Configure optional services? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        prompt_value "LANGFUSE_HOST" "Langfuse Host (optional)" "https://cloud.langfuse.com"
        prompt_value "LANGFUSE_PUBLIC_KEY" "Langfuse Public Key (optional)" "" "true"
        prompt_value "LANGFUSE_SECRET_KEY" "Langfuse Secret Key (optional)" "" "true"
        
        prompt_value "DRUPAL_URL" "Drupal URL (optional)"
        prompt_value "DRUPAL_CLIENT_ID" "Drupal Client ID (optional)" "" "true"
        prompt_value "DRUPAL_CLIENT_SECRET" "Drupal Client Secret (optional)" "" "true"
    fi
fi

# Cleanup backup files
rm -f .env.bak

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Validate configuration
log "Validating configuration..."
if validate_env; then
    log "✓ All required variables are configured"
    
    echo ""
    echo -e "${GREEN}✓ Configuration complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Verify .env file contents:"
    echo "     cat .env | grep -v '^#' | grep -v '^$'"
    echo ""
    echo "  2. Copy .env to your VM:"
    echo "     scp .env ubuntu@your-vm-ip:~/FU_Chatbot_RD_Zitho/"
    echo ""
    echo "  3. On the VM, initialize SSL:"
    echo "     ./scripts/init-ssl.sh ${DOMAIN_NAME} admin@example.com"
    echo ""
    echo "  4. Start Docker services:"
    echo "     docker compose -f docker/docker-compose.prod.yml up -d"
    echo ""
    echo "IMPORTANT: Keep .env file secure!"
    echo "  chmod 600 .env"
    echo "  Never commit to Git!"
    echo ""
    
    # Security check
    if grep -q "your_\|change_\|placeholder" .env; then
        warning "⚠ Some values still contain placeholders!"
        echo "Please review and update these values before deploying."
    fi
    
    exit 0
else
    error "✗ Configuration validation failed"
    echo ""
    echo "Please fill in all required values before deploying."
    echo "Edit .env file manually or run this script again."
    echo ""
    exit 1
fi
