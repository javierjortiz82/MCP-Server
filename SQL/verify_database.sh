#!/bin/bash
#==============================================================================
# Database Verification Script
# Quick health check for Lab01-MCP PostgreSQL database
#==============================================================================
# This script performs a quick verification of the database state:
# - Container status
# - Database connectivity
# - Schema objects count
# - Data integrity
# - Search capabilities
#
# Usage:
#   ./verify_database.sh           # Full verification
#   ./verify_database.sh --quick   # Quick check only
#
# Exit codes:
#   0 - All checks passed
#   1 - Some checks failed
#
# Author: Lab01-MCP Team
# Created: 2025-10-18
# Version: 1.0.0
#==============================================================================

set -u  # Exit on undefined variable

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Mode
QUICK_MODE=false

#==============================================================================
# HELPER FUNCTIONS
#==============================================================================

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

header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

check() {
    echo -ne "${BLUE}🔍 Checking $1...${NC}"
}

#==============================================================================
# VERIFICATION FUNCTIONS
#==============================================================================

verify_container() {
    check "PostgreSQL container"

    if docker ps --format '{{.Names}}' | grep -q "mcp-postgres"; then
        local status=$(docker inspect -f '{{.State.Status}}' mcp-postgres)

        if [ "$status" == "running" ]; then
            echo -e "\r${GREEN}✅ Container running${NC}                    "
            return 0
        else
            echo -e "\r${RED}❌ Container status: $status${NC}           "
            return 1
        fi
    else
        echo -e "\r${RED}❌ Container not found${NC}                "
        error "Start with: cd ../DockerConfig && docker-compose up -d"
        return 1
    fi
}

verify_connection() {
    check "Database connection"

    if docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT 1;" &>/dev/null; then
        echo -e "\r${GREEN}✅ Connection successful${NC}              "
        return 0
    else
        echo -e "\r${RED}❌ Connection failed${NC}                  "
        return 1
    fi
}

verify_extensions() {
    check "PostgreSQL extensions"

    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_extension WHERE extname IN ('vector', 'pg_trgm', 'unaccent', 'uuid-ossp');" 2>/dev/null | xargs)

    if [ "$count" == "4" ]; then
        echo -e "\r${GREEN}✅ All 4 extensions installed${NC}         "
        return 0
    else
        echo -e "\r${RED}❌ Only $count/4 extensions found${NC}     "
        return 1
    fi
}

verify_schema() {
    check "Database schema"

    local exists=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='test';" 2>/dev/null | xargs)

    if [ "$exists" == "1" ]; then
        echo -e "\r${GREEN}✅ Schema 'test' exists${NC}               "
        return 0
    else
        echo -e "\r${RED}❌ Schema 'test' not found${NC}            "
        return 1
    fi
}

verify_tables() {
    check "Database tables"

    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='test';" 2>/dev/null | xargs)

    if [ "$count" -ge "3" ]; then
        echo -e "\r${GREEN}✅ Found $count tables${NC}                "
        return 0
    else
        echo -e "\r${YELLOW}⚠️  Only $count tables found${NC}         "
        return 1
    fi
}

verify_products() {
    check "Products data"

    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products;" 2>/dev/null | xargs)

    if [ "$count" == "90" ]; then
        echo -e "\r${GREEN}✅ All 90 products loaded${NC}             "
        return 0
    elif [ "$count" -gt "0" ]; then
        echo -e "\r${YELLOW}⚠️  Found $count/90 products${NC}          "
        return 1
    else
        echo -e "\r${RED}❌ No products found${NC}                   "
        return 1
    fi
}

verify_embeddings() {
    check "AI embeddings"

    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;" 2>/dev/null | xargs)

    if [ "$count" == "90" ]; then
        echo -e "\r${GREEN}✅ All 90 embeddings generated${NC}        "
        return 0
    elif [ "$count" -gt "0" ]; then
        echo -e "\r${YELLOW}⚠️  Found $count/90 embeddings${NC}        "
        return 1
    else
        echo -e "\r${RED}❌ No embeddings found${NC}                 "
        return 1
    fi
}

verify_indexes() {
    check "Database indexes"

    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='test';" 2>/dev/null | xargs)

    if [ "$count" -ge "10" ]; then
        echo -e "\r${GREEN}✅ Found $count indexes${NC}               "
        return 0
    else
        echo -e "\r${YELLOW}⚠️  Only $count indexes found${NC}         "
        return 1
    fi
}

verify_functions() {
    check "PostgreSQL functions"

    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname='test';" 2>/dev/null | xargs)

    if [ "$count" -ge "2" ]; then
        echo -e "\r${GREEN}✅ Found $count functions${NC}             "
        return 0
    else
        echo -e "\r${YELLOW}⚠️  Only $count functions found${NC}       "
        return 1
    fi
}

test_fuzzy_search() {
    check "Fuzzy search capability"

    local result=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE similarity(normalize_text(name), normalize_text('laptop')) > 0.3;" 2>/dev/null | xargs)

    if [ "$result" -gt "0" ]; then
        echo -e "\r${GREEN}✅ Fuzzy search working ($result results)${NC} "
        return 0
    else
        echo -e "\r${RED}❌ Fuzzy search failed${NC}                "
        return 1
    fi
}

test_vector_search() {
    check "Vector search capability"

    local result=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL LIMIT 1;" 2>/dev/null | xargs)

    if [ "$result" == "1" ]; then
        echo -e "\r${GREEN}✅ Vector search available${NC}            "
        return 0
    else
        echo -e "\r${RED}❌ Vector search not available${NC}        "
        return 1
    fi
}

#==============================================================================
# DETAILED REPORT
#==============================================================================

print_detailed_report() {
    header "DATABASE STATUS REPORT"

    echo ""
    echo -e "${CYAN}📊 Container Information${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if docker ps --format '{{.Names}}' | grep -q "mcp-postgres"; then
        local uptime=$(docker inspect -f '{{.State.StartedAt}}' mcp-postgres | cut -d'.' -f1 | sed 's/T/ /')
        local health=$(docker inspect -f '{{.State.Health.Status}}' mcp-postgres 2>/dev/null || echo "N/A")

        info "Container: mcp-postgres"
        info "Status: Running"
        info "Started: $uptime"
        info "Health: $health"
    fi

    echo ""
    echo -e "${CYAN}📋 Schema Objects${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local tables=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='test';" 2>/dev/null | xargs)
    local indexes=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='test';" 2>/dev/null | xargs)
    local functions=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname='test';" 2>/dev/null | xargs)
    local extensions=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_extension;" 2>/dev/null | xargs)

    info "Tables: $tables"
    info "Indexes: $indexes"
    info "Functions: $functions"
    info "Extensions: $extensions"

    echo ""
    echo -e "${CYAN}📦 Data Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local products=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products;" 2>/dev/null | xargs)
    local embeddings=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;" 2>/dev/null | xargs)

    info "Products: $products"
    info "Embeddings: $embeddings"

    # Check optional tables
    local bookings=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='test' AND table_name='appointments';" 2>/dev/null | xargs)

    if [ "$bookings" == "1" ]; then
        local appts=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
            "SELECT COUNT(*) FROM test.appointments;" 2>/dev/null | xargs)
        info "Appointments: $appts"
    fi

    echo ""
    echo -e "${CYAN}🔍 Search Capabilities${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Test fuzzy search
    local fuzzy=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE similarity(normalize_text(name), normalize_text('laptop')) > 0.3;" 2>/dev/null | xargs)
    info "Fuzzy search results for 'laptop': $fuzzy"

    # Test vector capabilities
    local vector=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;" 2>/dev/null | xargs)
    info "Vector search enabled: $([ "$vector" -gt "0" ] && echo 'Yes' || echo 'No')"

    echo ""
}

#==============================================================================
# MAIN
#==============================================================================

print_help() {
    cat << EOF
Lab01-MCP Database Verification Script

USAGE:
    ./verify_database.sh [OPTIONS]

OPTIONS:
    --help      Show this help message
    --quick     Quick check only (skip detailed tests)
    --report    Show detailed status report

EXAMPLES:
    ./verify_database.sh            # Full verification
    ./verify_database.sh --quick    # Quick health check
    ./verify_database.sh --report   # Detailed report only

DATABASE INFO:
    Container: mcp-postgres
    Port: 5434 (external) / 5432 (internal)
    Database: mcpdb
    User: mcp_user
    Schema: test

EOF
}

main() {
    # Parse arguments
    local show_report=false

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
            --report)
                show_report=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done

    # Banner
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       Lab01-MCP Database Verification                    ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$show_report" == "true" ]; then
        print_detailed_report
        exit 0
    fi

    local errors=0

    # Quick checks
    echo -e "${CYAN}Running quick health checks...${NC}"
    echo ""

    verify_container || ((errors++))
    verify_connection || ((errors++))
    verify_schema || ((errors++))
    verify_tables || ((errors++))
    verify_products || ((errors++))
    verify_embeddings || ((errors++))

    if [ "$QUICK_MODE" == "false" ]; then
        echo ""
        echo -e "${CYAN}Running detailed checks...${NC}"
        echo ""

        verify_extensions || ((errors++))
        verify_indexes || ((errors++))
        verify_functions || ((errors++))
        test_fuzzy_search || ((errors++))
        test_vector_search || ((errors++))
    fi

    # Summary
    echo ""
    header "VERIFICATION SUMMARY"
    echo ""

    if [ $errors -eq 0 ]; then
        success "All checks passed! Database is healthy. 🎉"
        info "Port: 5434"
        info "Database: mcpdb"
        info "Schema: test"
        echo ""
        info "Run './verify_database.sh --report' for detailed status"
        echo ""
        exit 0
    else
        error "Found $errors issue(s)"
        warning "Run './deploy_database.sh' to fix issues"
        echo ""
        exit 1
    fi
}

main "$@"
