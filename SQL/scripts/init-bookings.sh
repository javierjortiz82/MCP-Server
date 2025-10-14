#!/usr/bin/env bash
# ============================================================================
# Bookings Schema Initialization Script
# ============================================================================
# Initializes bookings tables and seeds initial data.
#
# Prerequisites:
#   - PostgreSQL running
#   - .env file configured with DATABASE_URL and SCHEMA_NAME
#   - Python 3.11+ with psycopg2 installed
#
# Usage:
#   ./SQL/scripts/init-bookings.sh
#   # or
#   bash SQL/scripts/init-bookings.sh
#
# Author: Lab01-MCP Team
# Created: 2025-10-11
# Version: 1.0.0
# ============================================================================

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SQL_SRC_DIR="$ROOT_DIR/SQL/src"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo ""
    echo "========================================================================"
    echo "  BOOKINGS SCHEMA INITIALIZATION"
    echo "========================================================================"
    echo ""
}

print_summary() {
    echo ""
    echo "========================================================================"
    echo "  INITIALIZATION COMPLETE"
    echo "========================================================================"
    echo ""
}

# ============================================================================
# VALIDATION
# ============================================================================

validate_environment() {
    log_info "Validating environment..."

    # Check if .env exists
    if [ ! -f "$ROOT_DIR/.env" ]; then
        log_error ".env file not found in project root"
        log_info "Please create .env from .env.example:"
        log_info "  cp .env.example .env"
        exit 1
    fi

    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_info "Python version: $PYTHON_VERSION"

    # Check if psycopg2 is installed
    if ! python3 -c "import psycopg2" &> /dev/null; then
        log_error "psycopg2 not installed. Please install it:"
        log_info "  pip install psycopg2-binary"
        exit 1
    fi

    # Check if dotenv is installed
    if ! python3 -c "import dotenv" &> /dev/null; then
        log_error "python-dotenv not installed. Please install it:"
        log_info "  pip install python-dotenv"
        exit 1
    fi

    log_success "Environment validation passed"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_banner

    # Step 1: Validate environment
    validate_environment

    # Step 2: Initialize bookings schema
    log_info "Step 1/2: Creating bookings schema and tables..."
    if python3 "$SQL_SRC_DIR/init_bookings.py"; then
        log_success "Bookings schema created successfully"
    else
        log_error "Failed to create bookings schema"
        exit 1
    fi

    echo ""

    # Step 3: Seed initial data
    log_info "Step 2/2: Seeding initial data..."
    if python3 "$SQL_SRC_DIR/seed_booking_data.py"; then
        log_success "Initial data seeded successfully"
    else
        log_warning "Failed to seed initial data (non-critical)"
        log_info "You can run it manually later:"
        log_info "  python3 SQL/src/seed_booking_data.py"
    fi

    print_summary

    # Next steps
    log_info "Next steps:"
    log_info "  1. Configure Google Calendar credentials"
    log_info "  2. Test booking functionality"
    log_info "  3. Start MCP server with booking tools"
    echo ""
    log_success "Bookings system ready!"
}

# ============================================================================
# ERROR HANDLING
# ============================================================================

trap 'log_error "Script interrupted"; exit 130' INT
trap 'log_error "Script terminated"; exit 143' TERM

# Run main function
main "$@"
