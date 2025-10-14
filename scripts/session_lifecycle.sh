#!/usr/bin/env bash
# =============================================================================
# Session Lifecycle Management CLI
# =============================================================================
# Convenience script for managing session lifecycle operations.
#
# Usage:
#   ./scripts/session_lifecycle.sh [command] [options]
#
# Commands:
#   migrate          Run migration 005 (add session lifecycle)
#   cleanup          Run full cleanup job (all 6 tasks)
#   archive          Archive inactive sessions only
#   stats            Show session retention statistics
#   gdpr-export      Export user data (GDPR compliance)
#   gdpr-delete      Delete user data (GDPR compliance)
#   help             Show this help message
#
# Author: Lab01-MCP Team
# Created: 2025-10-13
# Version: 1.0.0
# =============================================================================

set -euo pipefail  # Strict mode: exit on error, undefined vars, pipe failures

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/session_lifecycle.log"

# Colors for output
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'  # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# =============================================================================
# Helper Functions
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

info() {
    echo -e "${GREEN}✓${NC} $*"
    log "INFO" "$*"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $*"
    log "WARN" "$*"
}

error() {
    echo -e "${RED}✗${NC} $*" >&2
    log "ERROR" "$*"
}

header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $*${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

confirm() {
    local prompt="$1"
    local response

    echo -e "${YELLOW}⚠ ${prompt}${NC}"
    read -r -p "Continue? [y/N] " response

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        error "python3 not found. Please install Python 3.8+"
        exit 1
    fi
}

setup_env() {
    # Create logs directory if it doesn't exist
    mkdir -p "$LOG_DIR"

    # Check if we're in a virtual environment
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        warn "Not in a virtual environment. Trying to activate..."

        if [[ -f "$PROJECT_ROOT/venv/bin/activate" ]]; then
            # shellcheck disable=SC1091
            source "$PROJECT_ROOT/venv/bin/activate"
            info "Virtual environment activated: $PROJECT_ROOT/venv"
        else
            warn "No virtual environment found. Using system Python."
        fi
    fi

    # Add project paths to PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT/mcp_server:$PROJECT_ROOT/agent/src:${PYTHONPATH:-}"
}

# =============================================================================
# Command Functions
# =============================================================================

cmd_migrate() {
    header "Running Migration 005: Session Lifecycle"

    check_python
    setup_env

    info "Executing migration runner..."
    echo ""

    if python3 "$PROJECT_ROOT/SQL/src/run_session_lifecycle_migration.py"; then
        echo ""
        info "Migration completed successfully!"
        info "Next: Run './scripts/session_lifecycle.sh stats' to see current state"
    else
        error "Migration failed. Check logs for details."
        exit 1
    fi
}

cmd_cleanup() {
    local dry_run="${1:-}"

    header "Session Lifecycle Cleanup Job"

    check_python
    setup_env

    if [[ "$dry_run" == "--dry-run" ]]; then
        warn "DRY RUN MODE: No data will be deleted"
        info "Running cleanup preview..."
        echo ""

        python3 "$PROJECT_ROOT/scripts/cleanup_expired_memories.py" --dry-run
    else
        if ! confirm "This will archive/delete old sessions according to policy."; then
            info "Operation cancelled"
            exit 0
        fi

        info "Running cleanup job..."
        echo ""

        python3 "$PROJECT_ROOT/scripts/cleanup_expired_memories.py"

        echo ""
        info "Cleanup completed!"
        info "Check logs at: $LOG_FILE"
    fi
}

cmd_archive() {
    header "Archive Inactive Sessions"

    check_python
    setup_env

    info "Archiving sessions inactive for 90+ days..."
    echo ""

    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/mcp_server')
from multi_agent import MemoryManager

memory = MemoryManager()
result = memory.archive_inactive_sessions()

print(f'✓ Archived {result[\"archived_count\"]} sessions')

if result['archived_count'] > 0:
    print('\nArchived sessions:')
    for session in result['sessions'][:5]:  # Show first 5
        email = session['customer_email'] or '(anonymous)'
        days = session['days_inactive']
        print(f'  - {email}: {days} days inactive')

    if result['archived_count'] > 5:
        print(f'  ... and {result[\"archived_count\"] - 5} more')
"

    echo ""
    info "Archive operation completed!"
}

cmd_stats() {
    header "Session Retention Statistics"

    check_python
    setup_env

    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/mcp_server')
from multi_agent import MemoryManager

memory = MemoryManager()
stats = memory.get_session_retention_stats()

if not stats:
    print('No statistics available')
    sys.exit(1)

print('Session Overview:')
print(f'  Active sessions:   {stats.get(\"active_sessions\", {}).get(\"count\", 0):>6} ({stats.get(\"active_sessions\", {}).get(\"percentage\", 0):>5.1f}%)')
print(f'  Archived sessions: {stats.get(\"archived_sessions\", {}).get(\"count\", 0):>6} ({stats.get(\"archived_sessions\", {}).get(\"percentage\", 0):>5.1f}%)')
print(f'  With email:        {stats.get(\"with_email\", {}).get(\"count\", 0):>6} ({stats.get(\"with_email\", {}).get(\"percentage\", 0):>5.1f}%)')
print(f'  Anonymous:         {stats.get(\"anonymous\", {}).get(\"count\", 0):>6} ({stats.get(\"anonymous\", {}).get(\"percentage\", 0):>5.1f}%)')
print()
print('Recent Activity:')
print(f'  Active (7 days):   {stats.get(\"active_7d\", {}).get(\"count\", 0):>6}')
print(f'  Active (30 days):  {stats.get(\"active_30d\", {}).get(\"count\", 0):>6}')
print()
print('Lifecycle Management:')
print(f'  Eligible archive:  {stats.get(\"eligible_archive\", {}).get(\"count\", 0):>6} (90+ days inactive)')
print(f'  Eligible delete:   {stats.get(\"eligible_delete\", {}).get(\"count\", 0):>6} (365+ days archived)')
"

    echo ""
    info "Use './scripts/session_lifecycle.sh cleanup --dry-run' to preview cleanup"
}

cmd_gdpr_export() {
    local email="${1:-}"

    if [[ -z "$email" ]]; then
        error "Email required"
        echo "Usage: $0 gdpr-export <email>"
        exit 1
    fi

    header "GDPR Data Export: $email"

    check_python
    setup_env

    info "Exporting user data..."
    echo ""

    python3 "$PROJECT_ROOT/scripts/gdpr_delete_user_data.py" \
        --email "$email" \
        --export \
        --export-path "$PROJECT_ROOT/gdpr_exports"

    echo ""
    info "Export completed! Check: $PROJECT_ROOT/gdpr_exports/"
}

cmd_gdpr_delete() {
    local email="${1:-}"

    if [[ -z "$email" ]]; then
        error "Email required"
        echo "Usage: $0 gdpr-delete <email>"
        exit 1
    fi

    header "GDPR Data Deletion: $email"

    check_python
    setup_env

    warn "This will PERMANENTLY delete ALL data for: $email"
    warn "This action is IRREVERSIBLE"
    echo ""
    echo "Recommended: Export data first with:"
    echo "  $0 gdpr-export $email"
    echo ""

    if ! confirm "Delete all data for $email?"; then
        info "Operation cancelled"
        exit 0
    fi

    info "Deleting user data..."
    echo ""

    python3 "$PROJECT_ROOT/scripts/gdpr_delete_user_data.py" \
        --email "$email" \
        --confirm

    echo ""
    info "Deletion completed!"
}

cmd_help() {
    cat << EOF
${BLUE}Session Lifecycle Management CLI${NC}
${BLUE}================================${NC}

${GREEN}USAGE:${NC}
  $0 [command] [options]

${GREEN}COMMANDS:${NC}
  ${YELLOW}migrate${NC}
      Run migration 005 to add session lifecycle management.
      Creates archived column, functions, and indexes.

  ${YELLOW}cleanup [--dry-run]${NC}
      Run full cleanup job (all 6 tasks):
        1. Auto-sync inactive sessions
        2. Cleanup expired session memory blocks
        3. Cleanup expired user memory blocks
        4. Archive inactive sessions (90+ days)
        5. Delete archived sessions (365+ days)
        6. Delete anonymous sessions (30+ days)

      Use --dry-run to preview without deleting.

  ${YELLOW}archive${NC}
      Archive inactive sessions only (90+ days).
      Soft delete: marks as archived, excludes from queries.

  ${YELLOW}stats${NC}
      Show session retention statistics.
      Displays active/archived/anonymous counts and percentages.

  ${YELLOW}gdpr-export <email>${NC}
      Export all user data to JSON (GDPR Article 20).
      Saved to: ./gdpr_exports/

  ${YELLOW}gdpr-delete <email>${NC}
      Permanently delete all user data (GDPR Article 17).
      ${RED}IRREVERSIBLE${NC} - export first recommended.

  ${YELLOW}help${NC}
      Show this help message.

${GREEN}EXAMPLES:${NC}
  # Run migration (first time setup)
  $0 migrate

  # Check current statistics
  $0 stats

  # Preview cleanup (safe, no deletion)
  $0 cleanup --dry-run

  # Run actual cleanup
  $0 cleanup

  # Export user data
  $0 gdpr-export user@example.com

  # Delete user data (after confirmation)
  $0 gdpr-delete user@example.com

${GREEN}CONFIGURATION:${NC}
  Edit mcp_server/config/settings.py or .env:
    SESSION_SOFT_ARCHIVE_DAYS=90        # Archive after inactivity
    SESSION_HARD_DELETE_DAYS=365        # Delete after archiving
    SESSION_ANONYMOUS_DELETE_DAYS=30    # Delete anonymous fast

${GREEN}CRON SETUP:${NC}
  Daily cleanup at 3:00 AM:
    0 3 * * * $PROJECT_ROOT/scripts/session_lifecycle.sh cleanup >> /var/log/cleanup.log 2>&1

${GREEN}LOGS:${NC}
  $LOG_FILE

${GREEN}DOCUMENTATION:${NC}
  docs/SESSION_LIFECYCLE_POLICY.md

EOF
}

# =============================================================================
# Main
# =============================================================================

main() {
    local command="${1:-help}"

    case "$command" in
        migrate)
            cmd_migrate
            ;;
        cleanup)
            cmd_cleanup "${2:-}"
            ;;
        archive)
            cmd_archive
            ;;
        stats)
            cmd_stats
            ;;
        gdpr-export)
            cmd_gdpr_export "${2:-}"
            ;;
        gdpr-delete)
            cmd_gdpr_delete "${2:-}"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            error "Unknown command: $command"
            echo ""
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main with all arguments
main "$@"
