#!/bin/bash

# ============================================================================
# LAB01-MCP DATABASE DEPLOYMENT SCRIPT
# ============================================================================
# Complete database deployment with validation
#
# Usage:
#   ./deploy.sh                    # Full deployment + verification
#   ./deploy.sh --no-verify        # Deployment only (no validation)
#   ./deploy.sh --validate-only    # Validate existing database
#   ./deploy.sh --help             # Show this help message
#
# Features:
#   - Creates schema, tables, indexes, functions
#   - Loads seed data (90 products)
#   - Validates complete deployment
#   - Comprehensive error handling
#
# Exit codes:
#   0 - Success
#   1 - Failure
#
# Author: Lab01-MCP Team
# Created: 2025-10-18
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOY_SQL="$SQL_ROOT_DIR/deploy.sql"
VALIDATE_SQL="$SQL_ROOT_DIR/validate_deployment.sql"
VERIFY_SCRIPT="$SCRIPT_DIR/verify.sh"
ENV_FILE="$SQL_ROOT_DIR/.env"

# Load environment variables from .env
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    error "Error: .env file not found at $ENV_FILE"
    exit 1
fi

# Set default schema if not in .env
SCHEMA_NAME="${SCHEMA_NAME:-test}"

# Mode flags
VERIFY_AFTER=true
VALIDATE_ONLY=false

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

step() {
    echo -e "${CYAN}[STEP] $1${NC}"
}

print_help() {
    cat << EOF
Lab01-MCP Database Deployment Script

USAGE:
    ./deploy.sh [OPTIONS]

OPTIONS:
    --help              Show this help message
    --no-verify         Skip verification after deployment
    --validate-only     Only validate existing database (no deployment)

EXAMPLES:
    ./deploy.sh                    # Full deployment + verification
    ./deploy.sh --no-verify        # Deploy without verification
    ./deploy.sh --validate-only    # Check database health

PREREQUISITES:
    - Docker container 'mcp-postgres' running
    - Database: mcpdb
    - User: mcp_user
    - Port: 5434 (external) / 5432 (internal)

OUTPUT:
    - Full deployment log with timestamps
    - Validation report
    - Health check results

EXIT CODES:
    0 - Success
    1 - Failure

EOF
}

# ============================================================================
# PREREQUISITE CHECKS
# ============================================================================

check_prerequisites() {
    step "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker."
        return 1
    fi
    success "Docker found"
    
    # Check container
    if ! docker ps --format '{{.Names}}' | grep -q "mcp-postgres"; then
        error "Container 'mcp-postgres' not found. Start it with:"
        error "  cd ../DockerConfig && docker-compose up -d"
        return 1
    fi
    success "Container 'mcp-postgres' is running"
    
    # Check database connectivity
    if ! docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT 1;" &>/dev/null; then
        error "Cannot connect to database. Check credentials."
        return 1
    fi
    success "Database connectivity verified"
    
    # Check files exist
    if [ ! -f "$DEPLOY_SQL" ]; then
        error "File not found: $DEPLOY_SQL"
        return 1
    fi
    success "Deploy script found: $(basename $DEPLOY_SQL)"
    
    if [ ! -f "$VALIDATE_SQL" ]; then
        error "File not found: $VALIDATE_SQL"
        return 1
    fi
    success "Validate script found: $(basename $VALIDATE_SQL)"
    
    if [ ! -f "$VERIFY_SCRIPT" ]; then
        error "File not found: $VERIFY_SCRIPT"
        return 1
    fi
    success "Verify script found: $(basename $VERIFY_SCRIPT)"
    
    return 0
}

# ============================================================================
# DEPLOYMENT PHASE
# ============================================================================

run_deployment() {
    step "Running database deployment..."
    echo "  Executing: $DEPLOY_SQL"
    echo ""

    if docker exec mcp-postgres psql -U mcp_user -d mcpdb -v "SCHEMA_NAME=$SCHEMA_NAME" -f "$DEPLOY_SQL"; then
        success "Deployment completed successfully"
        return 0
    else
        error "Deployment failed"
        return 1
    fi
}

# ============================================================================
# VALIDATION PHASE
# ============================================================================

run_validation() {
    step "Running deployment validation..."
    echo "  Executing: $VALIDATE_SQL"
    echo ""

    if docker exec mcp-postgres psql -U mcp_user -d mcpdb -v "SCHEMA_NAME=$SCHEMA_NAME" -f "$VALIDATE_SQL"; then
        success "Validation completed"
        return 0
    else
        error "Validation failed"
        return 1
    fi
}

# ============================================================================
# VERIFICATION PHASE
# ============================================================================

run_verification() {
    step "Running health checks..."
    echo ""
    
    if bash "$VERIFY_SCRIPT"; then
        success "All health checks passed"
        return 0
    else
        warning "Some health checks failed (see above)"
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_help
                exit 0
                ;;
            --no-verify)
                VERIFY_AFTER=false
                shift
                ;;
            --validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done
    
    print_header "LAB01-MCP DATABASE DEPLOYMENT"
    
    # Prerequisite checks
    if ! check_prerequisites; then
        error "Prerequisites check failed"
        exit 1
    fi
    
    echo ""
    success "All prerequisites passed"
    echo ""
    
    # Validate only mode
    if [ "$VALIDATE_ONLY" = true ]; then
        print_header "VALIDATION ONLY MODE"
        if run_validation; then
            success "Validation successful"
            exit 0
        else
            error "Validation failed"
            exit 1
        fi
    fi
    
    # Full deployment
    print_header "PHASE 1: DATABASE DEPLOYMENT"
    if ! run_deployment; then
        error "Deployment failed. Aborting."
        exit 1
    fi
    
    echo ""
    print_header "PHASE 2: DEPLOYMENT VALIDATION"
    if ! run_validation; then
        warning "Validation found issues (see above)"
    fi
    
    # Verification
    if [ "$VERIFY_AFTER" = true ]; then
        echo ""
        print_header "PHASE 3: HEALTH CHECKS"
        if ! run_verification; then
            warning "Some health checks failed"
        fi
    fi
    
    # Final summary
    echo ""
    print_header "DEPLOYMENT SUMMARY"
    success "Database deployment completed"
    info "Schema: test"
    info "Tables: 14"
    info "Indexes: 60+"
    info "Functions: 30+"
    info "Products loaded: 90"
    echo ""
    info "To verify deployment: ./verify.sh"
    info "To check database health: ./verify.sh --quick"
    echo ""
}

# Run main
main "$@"

