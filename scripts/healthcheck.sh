#!/usr/bin/env bash
set -euo pipefail

# Arena Health Check & Monitoring Script
# Regular monitoring with optional alerting (email, Slack, etc.)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="${API_URL:-http://127.0.0.1:8001}"
UI_URL="${UI_URL:-http://127.0.0.1:8002}"
LOG_FILE="${LOG_FILE:-/var/log/arena-health.log}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

# Check API health
check_api() {
    log "Checking API health: $API_URL/health"
    
    local response
    response=$(curl -fsS \
        --max-time 5 \
        --connect-timeout 3 \
        "${API_URL}/health" 2>&1) || {
        error "API health check failed"
        return 1
    }
    
    log "✅ API health: OK"
    return 0
}

# Check UI health
check_ui() {
    log "Checking UI health: $UI_URL/"
    
    local response
    response=$(curl -fsS \
        --max-time 5 \
        --connect-timeout 3 \
        "${UI_URL}/" 2>&1) || {
        error "UI health check failed"
        return 1
    }
    
    echo "$response" | grep -q "<!DOCTYPE" || {
        error "UI response invalid"
        return 1
    }
    
    log "✅ UI health: OK"
    return 0
}

# Get Arena statistics
get_stats() {
    log "Fetching Arena statistics..."
    
    local stats
    stats=$(curl -fsS \
        --max-time 5 \
        "${API_URL}/arena/statistics") || {
        error "Failed to get statistics"
        return 1
    }
    
    echo "$stats" | python3 -m json.tool | tee -a "$LOG_FILE"
    
    # Parse and check
    local total=$(echo "$stats" | python3 -c "import json, sys; print(json.load(sys.stdin)['total_comparisons'])")
    local voted=$(echo "$stats" | python3 -c "import json, sys; print(json.load(sys.stdin)['voted'])")
    local unvoted=$(echo "$stats" | python3 -c "import json, sys; print(json.load(sys.stdin)['unvoted'])")
    
    log "📊 Stats: $total total | $voted voted | $unvoted unvoted"
    
    return 0
}

# Check Docker containers
check_docker() {
    log "Checking Docker services..."
    
    local containers=("fu-arena-api" "fu-arena-ui" "fu-arena-nginx" "fu-arena-postgres" "fu-arena-certbot")
    local failed=0
    
    for container in "${containers[@]}"; do
        local status
        status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
        
        if [[ "$status" == "running" ]]; then
            log "  ✅ $container: running"
        elif [[ "$status" == "missing" ]]; then
            warn "  ⚠️ $container: not created (OK for first deployment)"
        else
            error "  ❌ $container: $status"
            ((failed++))
        fi
    done
    
    [[ $failed -eq 0 ]] && return 0 || return 1
}

# Check disk space
check_disk() {
    log "Checking disk space..."
    
    # Check /var/backups/arena
    local backup_usage
    backup_usage=$(du -sh /var/backups/arena 2>/dev/null | cut -f1 || echo "0")
    
    # Check /data volume
    local data_usage
    if docker volume inspect fu_chatbot_rd_zitho_arena_data >/dev/null 2>&1; then
        data_usage=$(docker run --rm \
            -v fu_chatbot_rd_zitho_arena_data:/data \
            alpine \
            du -sh /data | cut -f1) || data_usage="unknown"
    else
        data_usage="no volume"
    fi
    
    log "  Backups: $backup_usage"
    log "  Arena data: $data_usage"
}

# Send alert
send_alert() {
    local subject="$1"
    local message="$2"
    
    # Email alert
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || \
            warn "Failed to send email alert"
    fi
    
    # Slack alert
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -fsS -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"$subject\",
                \"attachments\": [{
                    \"color\": \"danger\",
                    \"text\": \"$message\",
                    \"ts\": $(date +%s)
                }]
            }" 2>/dev/null || \
            warn "Failed to send Slack alert"
    fi
}

# Full health check
full_check() {
    log "🏥 Starting full health check..."
    
    local failed=0
    
    check_api || ((failed++))
    check_ui || ((failed++))
    check_docker || ((failed++))
    check_disk
    get_stats || ((failed++))
    
    if [[ $failed -eq 0 ]]; then
        log "✅ All checks passed"
        return 0
    else
        error "❌ $failed check(s) failed"
        send_alert "Arena Health Check Failed" "Failed: $failed check(s). See logs for details."
        return 1
    fi
}

# Usage
usage() {
    cat << EOF
Usage: $0 {command}

Commands:
    api             Check API health
    ui              Check UI health
    docker          Check Docker containers
    disk            Check disk usage
    stats           Get Arena statistics
    all             Run all checks (default)
    help            Show this help message

Environment Variables:
    API_URL         API base URL (default: http://127.0.0.1:8001)
    UI_URL          UI base URL (default: http://127.0.0.1:8002)
    LOG_FILE        Log file (default: /var/log/arena-health.log)
    ALERT_EMAIL     Email for alerts (optional)
    SLACK_WEBHOOK   Slack webhook for alerts (optional)

Examples:
    $0 all
    $0 api
    ALERT_EMAIL=admin@example.com $0 all
    $0 stats

EOF
}

# Main
main() {
    local command="${1:-all}"
    
    case "$command" in
        api)
            check_api
            ;;
        ui)
            check_ui
            ;;
        docker)
            check_docker
            ;;
        disk)
            check_disk
            ;;
        stats)
            get_stats
            ;;
        all)
            full_check
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
