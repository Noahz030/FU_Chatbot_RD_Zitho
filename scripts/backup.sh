#!/usr/bin/env bash
set -euo pipefail

# Arena Backup & Recovery Script
# Daily backups with automatic retention (30-day rolling window)
# Supports S3 upload for offsite backup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/arena}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
LOG_FILE="${LOG_FILE:-/var/log/arena-backup.log}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/arena_votes_${TIMESTAMP}.jsonl"

# Optional S3 config
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-arena-backups}"

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
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$LOG_FILE"
}

# Create local backup
backup_local() {
    log "Creating local backup: $BACKUP_FILE"
    
    mkdir -p "$BACKUP_DIR"
    
    docker run --rm \
        -v fu_arena_arena_data:/data \
        -v "$BACKUP_DIR:/bkp" \
        alpine \
        sh -c "cp /data/arena_votes.jsonl /bkp/arena_votes_${TIMESTAMP}.jsonl && \
                chmod 640 /bkp/arena_votes_${TIMESTAMP}.jsonl" || \
        error "Local backup failed"
    
    # Verify backup
    local file_size=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null)
    if [[ $file_size -gt 0 ]]; then
        log "✅ Local backup created ($(numfmt --to=iec $file_size 2>/dev/null || echo "$file_size bytes"))"
    else
        error "Backup file is empty!"
    fi
}

# Upload to S3
backup_s3() {
    if [[ -z "$S3_BUCKET" ]]; then
        warn "S3_BUCKET not configured, skipping S3 upload"
        return 0
    fi
    
    log "Uploading backup to S3: s3://${S3_BUCKET}/${S3_PREFIX}/"
    
    aws s3 cp "$BACKUP_FILE" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/arena_votes_${TIMESTAMP}.jsonl" \
        --sse AES256 \
        --metadata "backup-date=${TIMESTAMP}" || \
        error "S3 upload failed"
    
    log "✅ S3 backup uploaded"
}

# Cleanup old local backups
cleanup_old() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    local deleted_count=0
    while IFS= read -r old_file; do
        rm -f "$old_file"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "arena_votes_*.jsonl" -mtime +${RETENTION_DAYS})
    
    if [[ $deleted_count -gt 0 ]]; then
        log "✅ Deleted $deleted_count old backup(s)"
    else
        log "ℹ️ No old backups to delete"
    fi
}

# List backups
list_backups() {
    log "Available local backups:"
    ls -lh "$BACKUP_DIR"/arena_votes_*.jsonl 2>/dev/null | \
        awk '{print "  " $9 " (" $5 ", " $6 " " $7 " " $8 ")"}' || \
        error "No backups found"
}

# Restore from backup
restore() {
    local backup_file="$1"
    
    [[ -f "$backup_file" ]] || error "Backup file not found: $backup_file"
    
    log "Restoring from: $backup_file"
    
    docker run --rm \
        -v fu_arena_arena_data:/data \
        -v "$(dirname "$backup_file"):/bkp" \
        alpine \
        sh -c "cp /bkp/$(basename "$backup_file") /data/arena_votes.jsonl" || \
        error "Restore failed"
    
    log "✅ Backup restored successfully"
}

# Full backup cycle
backup_all() {
    log "🔄 Starting backup cycle..."
    backup_local
    backup_s3
    cleanup_old
    list_backups
    log "✅ Backup cycle complete"
}

# Usage
usage() {
    cat << EOF
Usage: $0 {command} [args]

Commands:
    backup          Create local backup (+ S3 if configured)
    list            List available backups
    restore <file>  Restore from backup file
    verify <file>   Verify backup integrity
    help            Show this help message

Environment Variables:
    BACKUP_DIR      Backup directory (default: /var/backups/arena)
    RETENTION_DAYS  Keep backups for N days (default: 30)
    LOG_FILE        Log file (default: /var/log/arena-backup.log)
    S3_BUCKET       S3 bucket for offsite backup (optional)
    S3_PREFIX       S3 key prefix (default: arena-backups)

Examples:
    $0 backup
    $0 list
    $0 restore /var/backups/arena/arena_votes_20250101-120000.jsonl
    S3_BUCKET=my-backups $0 backup

EOF
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    [[ -f "$backup_file" ]] || error "Backup file not found: $backup_file"
    
    log "Verifying backup: $backup_file"
    
    # Check file size
    local file_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)
    [[ $file_size -gt 0 ]] || error "Backup file is empty"
    
    # Check JSON validity
    python3 << EOF || error "Invalid JSON in backup"
import json
try:
    with open("$backup_file", "r") as f:
        for line in f:
            json.loads(line.strip())
    print("✅ JSON valid")
except Exception as e:
    print(f"❌ JSON error: {e}")
    exit(1)
EOF
}

# Main
main() {
    local command="${1:-help}"
    
    case "$command" in
        backup)
            backup_all
            ;;
        list)
            list_backups
            ;;
        restore)
            restore "${2:-}" || usage
            ;;
        verify)
            verify_backup "${2:-}" || usage
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
