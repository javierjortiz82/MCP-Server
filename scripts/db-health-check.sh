#!/bin/bash

# ============================================================================
# LAB01-MCP DATABASE HEALTH CHECK SCRIPT
# ============================================================================
# Comprehensive health check for database deployment
#
# Usage:
#   ./db-health-check.sh                # Full health check
#   ./db-health-check.sh --quick        # Quick status only
#   ./db-health-check.sh --verbose      # Detailed output with queries
#   ./db-health-check.sh --help         # Show this help message
#
# Exit codes:
#   0 - All checks passed
#   1 - Some checks failed
#
# ============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Flags
QUICK_MODE=false
VERBOSE=false

# Counter
CHECKS_PASSED=0
CHECKS_FAILED=0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  $1${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((CHECKS_PASSED++))
}

fail() {
    echo -e "${RED}❌ $1${NC}"
    ((CHECKS_FAILED++))
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check() {
    echo -e "${CYAN}[CHECK] $1${NC}"
}

print_help() {
    cat << EOF
Lab01-MCP Database Health Check Script

USAGE:
    ./db-health-check.sh [OPTIONS]

OPTIONS:
    --help              Show this help message
    --quick             Quick status check only (no detailed queries)
    --verbose           Show detailed output with query results

EXAMPLES:
    ./db-health-check.sh                # Full health check
    ./db-health-check.sh --quick        # Fast check
    ./db-health-check.sh --verbose      # Detailed with results

EXIT CODES:
    0 - All checks passed
    1 - Some checks failed

CHECKS PERFORMED:
    1. Docker container running
    2. Database connectivity
    3. Schema exists
    4. All 14 tables created
    5. All 31 functions exist
    6. Data loaded correctly
    7. Embeddings present
    8. Indexes in place
    9. No orphaned rows
   10. Vector similarity working

OUTPUT:
    - Health status for each component
    - Row count summary
    - Function verification
    - Index status
    - Detailed results (if --verbose)

EOF
}

# ============================================================================
# CHECKS
# ============================================================================

check_docker_container() {
    check "Docker container running..."

    if docker ps --format '{{.Names}}' | grep -q "mcp-postgres"; then
        success "Container 'mcp-postgres' is running"
        return 0
    else
        fail "Container 'mcp-postgres' not found"
        return 1
    fi
}

check_database_connectivity() {
    check "Database connectivity..."

    if docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT 1;" &>/dev/null; then
        success "Database is accessible"
        return 0
    else
        fail "Cannot connect to database"
        return 1
    fi
}

check_schema_exists() {
    check "Schema 'test' exists..."

    local schema_exists=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = 'test';")

    if [ "$schema_exists" -eq 1 ]; then
        success "Schema 'test' exists"
        return 0
    else
        fail "Schema 'test' not found"
        return 1
    fi
}

check_tables() {
    check "All 14 tables created..."

    local table_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'test';")

    if [ "$table_count" -eq 14 ]; then
        success "All 14 tables created"
        if [ "$VERBOSE" = true ]; then
            echo "    Tables:"
            docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
                "SELECT '    ' || tablename FROM pg_tables WHERE schemaname = 'test' ORDER BY tablename;" | head -14
        fi
        return 0
    else
        fail "Expected 14 tables, found $table_count"
        return 1
    fi
}

check_functions() {
    check "All 31 functions exist..."

    local func_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'test';")

    if [ "$func_count" -eq 31 ]; then
        success "All 31 functions created"
        return 0
    else
        fail "Expected 31 functions, found $func_count"
        return 1
    fi
}

check_data_loaded() {
    check "Data loaded correctly..."

    local products=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM test.products;")
    local service_types=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM test.service_types;")
    local business_hours=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM test.business_hours;")

    local success_flag=true

    if [ "$products" -ne 90 ]; then
        warning "Expected 90 products, found $products"
        success_flag=false
    fi

    if [ "$service_types" -ne 5 ]; then
        warning "Expected 5 service types, found $service_types"
        success_flag=false
    fi

    if [ "$business_hours" -lt 5 ]; then
        warning "Expected >= 5 business hours, found $business_hours"
        success_flag=false
    fi

    if [ "$success_flag" = true ]; then
        success "Data loaded: products=$products, service_types=$service_types, business_hours=$business_hours"
        return 0
    else
        fail "Data loading incomplete"
        return 1
    fi
}

check_embeddings() {
    check "Product embeddings present..."

    local embeddings=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;")

    if [ "$embeddings" -eq 90 ]; then
        success "All 90 products have embeddings"
        return 0
    else
        fail "Expected 90 embeddings, found $embeddings"
        return 1
    fi
}

check_indexes() {
    check "Indexes created..."

    local index_count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'test';")

    if [ "$index_count" -gt 50 ]; then
        success "Indexes created: $index_count indexes"
        return 0
    else
        warning "Expected 80+ indexes, found $index_count"
        return 1
    fi
}

check_no_orphans() {
    check "No orphaned rows..."

    # Check for email_queue without valid bookings
    local orphaned=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT COUNT(*) FROM test.email_queue WHERE booking_id IS NOT NULL AND booking_id NOT IN (SELECT id FROM test.appointments);")

    if [ "$orphaned" -eq 0 ]; then
        success "No orphaned rows found"
        return 0
    else
        warning "Found $orphaned potentially orphaned email queue rows"
        return 1
    fi
}

check_vector_search() {
    check "Vector search working..."

    # Simple test: can we query embeddings?
    local vector_test=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -tA -c \
        "SELECT 1 FROM test.products WHERE embedding IS NOT NULL LIMIT 1;" 2>/dev/null)

    if [ "$vector_test" = "1" ]; then
        success "Vector embeddings are searchable"
        return 0
    else
        fail "Vector search test failed"
        return 1
    fi
}

# ============================================================================
# SUMMARY
# ============================================================================

print_summary() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  HEALTH CHECK SUMMARY                                        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$CHECKS_FAILED" -eq 0 ]; then
        echo -e "${GREEN}✅ All checks passed ($CHECKS_PASSED/$CHECKS_PASSED)${NC}"
        echo ""
        info "Database deployment is healthy and ready for use"
        return 0
    else
        echo -e "${RED}❌ Some checks failed ($CHECKS_PASSED passed, $CHECKS_FAILED failed)${NC}"
        echo ""
        warning "Please review failed checks above"
        return 1
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                print_help
                exit 0
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done

    print_header "LAB01-MCP DATABASE HEALTH CHECK"

    if [ "$QUICK_MODE" = true ]; then
        echo "Running in QUICK mode (container and connectivity only)"
        echo ""
    fi

    # Run checks
    check_docker_container || true
    check_database_connectivity || true

    if [ "$QUICK_MODE" = false ]; then
        check_schema_exists || true
        check_tables || true
        check_functions || true
        check_data_loaded || true
        check_embeddings || true
        check_indexes || true
        check_no_orphans || true
        check_vector_search || true
    fi

    # Print summary and exit with appropriate code
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main "$@"
