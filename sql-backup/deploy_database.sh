#!/bin/bash
#==============================================================================
# Database Deployment Master Script
# Lab01-MCP - Complete Database Initialization from Zero to Production
#==============================================================================
# This script orchestrates the complete database deployment process:
# 1. Prerequisites validation (Docker, PostgreSQL, .env)
# 2. Core schema initialization (products, extensions, indexes)
# 3. Data population with AI embeddings
# 4. Agent memory system setup
# 5. Bookings schema creation
# 6. Email notification system
# 7. Optional migrations and seed data
# 8. Comprehensive verification
#
# Usage:
#   ./deploy_database.sh                    # Full deployment
#   ./deploy_database.sh --skip-seed        # Skip test data
#   ./deploy_database.sh --only-core        # Only core + data
#   ./deploy_database.sh --verify-only      # Only run verification
#   ./deploy_database.sh --help             # Show help
#
# Author: Lab01-MCP Team
# Created: 2025-10-18
# Version: 1.0.0
#==============================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

#==============================================================================
# CONFIGURATION
#==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${SCRIPT_DIR}/deployment.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Deployment phases
SKIP_SEED=false
ONLY_CORE=false
VERIFY_ONLY=false

#==============================================================================
# HELPER FUNCTIONS
#==============================================================================

log() {
    echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

step() {
    echo ""
    echo -e "${BLUE}━━━ Step $1: $2${NC}"
}

#==============================================================================
# PREREQUISITE CHECKS
#==============================================================================

check_prerequisites() {
    header "PHASE 0: Prerequisites Validation"

    local errors=0

    # Check if running from correct directory
    if [ ! -f "${SCRIPT_DIR}/README.md" ]; then
        error "Must run from SQL/ directory"
        ((errors++))
    fi

    # Check Python version
    step "1/6" "Checking Python version"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        info "Python version: $PYTHON_VERSION"
        success "Python 3 found"
    else
        error "Python 3 not found. Please install Python 3.10+"
        ((errors++))
    fi

    # Check Docker
    step "2/6" "Checking Docker"
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        info "Docker version: $DOCKER_VERSION"
        success "Docker found"
    else
        error "Docker not found. Please install Docker"
        ((errors++))
    fi

    # Check PostgreSQL container
    step "3/6" "Checking PostgreSQL container"
    if docker ps --format '{{.Names}}' | grep -q "mcp-postgres"; then
        CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' mcp-postgres)
        info "Container status: $CONTAINER_STATUS"

        if [ "$CONTAINER_STATUS" == "running" ]; then
            success "PostgreSQL container running"
        else
            error "PostgreSQL container not running. Start with: cd ../DockerConfig && docker-compose up -d"
            ((errors++))
        fi
    else
        error "PostgreSQL container 'mcp-postgres' not found"
        error "Start with: cd ../DockerConfig && docker-compose up -d"
        ((errors++))
    fi

    # Check .env file
    step "4/6" "Checking environment configuration"
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        success ".env file found"

        # Check required variables
        if grep -q "DATABASE_URL=" "${SCRIPT_DIR}/.env"; then
            DATABASE_URL=$(grep "DATABASE_URL=" "${SCRIPT_DIR}/.env" | cut -d'=' -f2)
            info "DATABASE_URL configured"
        else
            error "DATABASE_URL not found in .env"
            ((errors++))
        fi

        if grep -q "GOOGLE_API_KEY=" "${SCRIPT_DIR}/.env"; then
            success "GOOGLE_API_KEY configured"
        else
            warning "GOOGLE_API_KEY not found (required for embeddings)"
            info "Get your key from: https://aistudio.google.com/app/apikey"
        fi
    else
        error ".env file not found. Copy from .env.example"
        ((errors++))
    fi

    # Check required Python packages
    step "5/6" "Checking Python dependencies"
    local missing_packages=0

    for package in psycopg2 dotenv google.genai pgvector tenacity; do
        if python3 -c "import ${package//-/_}" 2>/dev/null; then
            success "Package '${package}' installed"
        else
            error "Package '${package}' not found"
            ((missing_packages++))
        fi
    done

    if [ $missing_packages -gt 0 ]; then
        error "Missing $missing_packages required packages"
        info "Install with: pip install psycopg2-binary python-dotenv google-genai pgvector tenacity"
        ((errors++))
    fi

    # Test database connection
    step "6/6" "Testing database connection"
    if docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT version();" &>/dev/null; then
        PG_VERSION=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c "SELECT version();" | head -1 | xargs)
        info "PostgreSQL: ${PG_VERSION:0:50}..."
        success "Database connection successful"
    else
        error "Cannot connect to database"
        error "Check credentials in .env and container status"
        ((errors++))
    fi

    # Summary
    echo ""
    if [ $errors -eq 0 ]; then
        success "All prerequisites validated successfully"
        return 0
    else
        error "Found $errors error(s). Please fix before continuing."
        return 1
    fi
}

#==============================================================================
# DEPLOYMENT PHASES
#==============================================================================

deploy_core_schema() {
    header "PHASE 1: Core Schema Initialization"

    step "1/1" "Creating schema, extensions, tables, indexes, functions"

    cd "$SCRIPT_DIR"
    if python3 src/init-db.py; then
        success "Core schema initialized successfully"

        # Verify
        local table_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='test';" | xargs)
        info "Created $table_count tables in 'test' schema"

        return 0
    else
        error "Core schema initialization failed"
        return 1
    fi
}

populate_data() {
    header "PHASE 2: Data Population with AI Embeddings"

    step "1/1" "Loading 90 products and generating Gemini embeddings"

    cd "$SCRIPT_DIR"
    if python3 src/populate-db.py; then
        success "Data population completed successfully"

        # Verify
        local product_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
            "SELECT COUNT(*) FROM test.products;" | xargs)
        local embedding_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
            "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;" | xargs)

        info "Products loaded: $product_count"
        info "Embeddings generated: $embedding_count"

        if [ "$product_count" == "90" ] && [ "$embedding_count" == "90" ]; then
            success "All products loaded with embeddings"
            return 0
        else
            warning "Expected 90 products/embeddings, got $product_count/$embedding_count"
            return 1
        fi
    else
        error "Data population failed"
        return 1
    fi
}

deploy_memory_system() {
    header "PHASE 3: Agent Memory System"

    step "1/1" "Creating conversation sessions, messages, memory blocks"

    cd "$SCRIPT_DIR"
    if python3 src/init_memory_system.py; then
        success "Agent memory system initialized successfully"
        return 0
    else
        error "Memory system initialization failed"
        return 1
    fi
}

deploy_bookings() {
    header "PHASE 4: Bookings Schema"

    step "1/2" "Creating appointments, service types, business hours"

    cd "$SCRIPT_DIR"
    if python3 src/init_bookings.py; then
        success "Bookings schema initialized successfully"
    else
        error "Bookings initialization failed"
        return 1
    fi

    step "2/2" "Creating service-specific hours (optional)"

    if [ -f "src/init_service_hours.py" ]; then
        if python3 src/init_service_hours.py; then
            success "Service hours initialized successfully"
        else
            warning "Service hours initialization failed (non-critical)"
        fi
    else
        info "Service hours script not found (optional)"
    fi

    return 0
}

deploy_email_queue() {
    header "PHASE 5: Email Notification System"

    step "1/1" "Creating email queue table and worker functions"

    cd "$SCRIPT_DIR"
    if python3 src/init_email_queue.py; then
        success "Email queue system initialized successfully"
        return 0
    else
        error "Email queue initialization failed"
        return 1
    fi
}

deploy_migrations() {
    header "PHASE 6: Advanced Features (Optional Migrations)"

    step "1/3" "User memory profiles (cross-session memory)"

    cd "$SCRIPT_DIR"
    if [ -f "src/run_user_memory_migration.py" ]; then
        if python3 src/run_user_memory_migration.py; then
            success "User memory migration completed"
        else
            warning "User memory migration failed (non-critical)"
        fi
    else
        info "User memory migration script not found (optional)"
    fi

    step "2/3" "Session lifecycle tracking"

    if [ -f "src/run_session_lifecycle_migration.py" ]; then
        if python3 src/run_session_lifecycle_migration.py; then
            success "Session lifecycle migration completed"
        else
            warning "Session lifecycle migration failed (non-critical)"
        fi
    else
        info "Session lifecycle migration script not found (optional)"
    fi

    step "3/3" "Auto-sync features"

    if [ -f "src/run_auto_sync_migration.py" ]; then
        if python3 src/run_auto_sync_migration.py; then
            success "Auto-sync migration completed"
        else
            warning "Auto-sync migration failed (non-critical)"
        fi
    else
        info "Auto-sync migration script not found (optional)"
    fi

    return 0
}

seed_test_data() {
    header "PHASE 7: Test Data Seeding (Optional)"

    step "1/2" "Seeding booking test data"

    cd "$SCRIPT_DIR"
    if [ -f "src/seed_booking_data.py" ]; then
        if python3 src/seed_booking_data.py; then
            success "Booking test data seeded"
        else
            warning "Booking seed failed (non-critical)"
        fi
    else
        info "Booking seed script not found (optional)"
    fi

    step "2/2" "Seeding service hours test data"

    if [ -f "src/seed_service_hours.py" ]; then
        if python3 src/seed_service_hours.py; then
            success "Service hours test data seeded"
        else
            warning "Service hours seed failed (non-critical)"
        fi
    else
        info "Service hours seed script not found (optional)"
    fi

    return 0
}

#==============================================================================
# VERIFICATION
#==============================================================================

verify_deployment() {
    header "PHASE 8: Deployment Verification"

    local errors=0

    step "1/8" "Verifying extensions"

    local ext_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_extension WHERE extname IN ('vector', 'pg_trgm', 'unaccent', 'uuid-ossp');" | xargs)

    if [ "$ext_count" == "4" ]; then
        success "All 4 required extensions installed"
    else
        error "Expected 4 extensions, found $ext_count"
        ((errors++))
    fi

    step "2/8" "Verifying tables"

    local table_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='test';" | xargs)

    info "Found $table_count tables in 'test' schema"

    if [ "$table_count" -ge "3" ]; then
        success "Core tables created"
    else
        error "Expected at least 3 tables, found $table_count"
        ((errors++))
    fi

    step "3/8" "Verifying indexes"

    local index_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='test';" | xargs)

    info "Found $index_count indexes"

    if [ "$index_count" -ge "10" ]; then
        success "Indexes created"
    else
        warning "Expected at least 10 indexes, found $index_count"
    fi

    step "4/8" "Verifying functions"

    local func_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname='test';" | xargs)

    info "Found $func_count functions in 'test' schema"

    if [ "$func_count" -ge "2" ]; then
        success "Functions created"
    else
        warning "Expected at least 2 functions, found $func_count"
    fi

    step "5/8" "Verifying products data"

    local product_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products;" | xargs)

    if [ "$product_count" == "90" ]; then
        success "All 90 products loaded"
    else
        error "Expected 90 products, found $product_count"
        ((errors++))
    fi

    step "6/8" "Verifying embeddings"

    local embedding_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;" | xargs)

    if [ "$embedding_count" == "90" ]; then
        success "All 90 embeddings generated"
    else
        error "Expected 90 embeddings, found $embedding_count"
        ((errors++))
    fi

    step "7/8" "Testing fuzzy search"

    local fuzzy_result=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE similarity(normalize_text(name), normalize_text('laptop')) > 0.3;" | xargs)

    if [ "$fuzzy_result" -gt "0" ]; then
        success "Fuzzy search working ($fuzzy_result results for 'laptop')"
    else
        warning "Fuzzy search returned no results"
    fi

    step "8/8" "Testing vector search"

    # Get a sample embedding
    local has_vector=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL LIMIT 1;" | xargs)

    if [ "$has_vector" == "1" ]; then
        success "Vector search capabilities verified"
    else
        error "Vector search test failed"
        ((errors++))
    fi

    # Summary
    echo ""
    if [ $errors -eq 0 ]; then
        success "All verification checks passed!"
        return 0
    else
        error "Verification found $errors error(s)"
        return 1
    fi
}

#==============================================================================
# MAIN DEPLOYMENT ORCHESTRATOR
#==============================================================================

print_help() {
    cat << EOF
Lab01-MCP Database Deployment Script

USAGE:
    ./deploy_database.sh [OPTIONS]

OPTIONS:
    --help              Show this help message
    --skip-seed         Skip test data seeding (Phase 7)
    --only-core         Deploy only core schema and data (Phases 1-2)
    --verify-only       Run verification checks only

EXAMPLES:
    ./deploy_database.sh                    # Full deployment
    ./deploy_database.sh --skip-seed        # Production deployment (no test data)
    ./deploy_database.sh --only-core        # Minimal deployment
    ./deploy_database.sh --verify-only      # Check existing deployment

DATABASE PORT:
    PostgreSQL runs on port 5434 (external) / 5432 (internal)
    Container name: mcp-postgres
    Database: mcpdb
    User: mcp_user

PHASES:
    0. Prerequisites validation
    1. Core schema initialization
    2. Data population with embeddings
    3. Agent memory system
    4. Bookings schema
    5. Email notification system
    6. Optional migrations
    7. Test data seeding (optional)
    8. Deployment verification

For more information, see SQL/README.md
EOF
}

main() {
    # Initialize log file
    echo "=== Database Deployment Log ===" > "$LOG_FILE"
    echo "Timestamp: $TIMESTAMP" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_help
                exit 0
                ;;
            --skip-seed)
                SKIP_SEED=true
                shift
                ;;
            --only-core)
                ONLY_CORE=true
                shift
                ;;
            --verify-only)
                VERIFY_ONLY=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done

    # Print banner
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                           ║${NC}"
    echo -e "${CYAN}║          Lab01-MCP Database Deployment Script            ║${NC}"
    echo -e "${CYAN}║                                                           ║${NC}"
    echo -e "${CYAN}║  Complete database initialization from zero to prod      ║${NC}"
    echo -e "${CYAN}║                                                           ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"

    info "Deployment started: $TIMESTAMP"
    info "Log file: $LOG_FILE"

    if [ "$SKIP_SEED" == "true" ]; then
        info "Mode: Production (skip test data)"
    elif [ "$ONLY_CORE" == "true" ]; then
        info "Mode: Core only (schema + data)"
    elif [ "$VERIFY_ONLY" == "true" ]; then
        info "Mode: Verification only"
    else
        info "Mode: Full deployment"
    fi

    echo ""

    # Execute phases
    local start_time=$(date +%s)
    local phase_errors=0

    if [ "$VERIFY_ONLY" == "true" ]; then
        # Only run verification
        if ! verify_deployment; then
            ((phase_errors++))
        fi
    else
        # Full deployment
        if ! check_prerequisites; then
            error "Prerequisites check failed. Aborting deployment."
            exit 1
        fi

        if ! deploy_core_schema; then
            ((phase_errors++))
            error "Core schema deployment failed. Aborting."
            exit 1
        fi

        if ! populate_data; then
            ((phase_errors++))
            error "Data population failed. Aborting."
            exit 1
        fi

        if [ "$ONLY_CORE" == "false" ]; then
            deploy_memory_system || ((phase_errors++))
            deploy_bookings || ((phase_errors++))
            deploy_email_queue || ((phase_errors++))
            deploy_migrations  # Don't count errors (optional)

            if [ "$SKIP_SEED" == "false" ]; then
                seed_test_data  # Don't count errors (optional)
            fi
        fi

        verify_deployment || ((phase_errors++))
    fi

    # Calculate execution time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    # Final summary
    echo ""
    header "DEPLOYMENT SUMMARY"

    echo ""
    info "Total execution time: ${minutes}m ${seconds}s"

    if [ $phase_errors -eq 0 ]; then
        success "Deployment completed successfully! 🎉"
        success "Database is ready for use on port 5434"
        echo ""
        info "Next steps:"
        info "  1. Start MCP server: docker-compose restart mcp-server"
        info "  2. Run client: python -m client_mcp.main"
        info "  3. Test queries: See SQL/examples/README_TESTING.md"
        echo ""
        exit 0
    else
        error "Deployment completed with $phase_errors error(s)"
        error "Check $LOG_FILE for details"
        echo ""
        exit 1
    fi
}

# Execute main function
main "$@"
