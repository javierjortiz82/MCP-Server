#!/bin/bash

# ============================================================================
# LAB01-MCP DATABASE VERIFICATION SCRIPT
# ============================================================================
# Quick health checks and detailed diagnostics for Lab01-MCP database
#
# Usage:
#   ./verify.sh                # Full verification
#   ./verify.sh --quick        # Quick health check only
#   ./verify.sh --detailed     # Detailed diagnostics
#   ./verify.sh --help         # Show help
#
# Features:
#   - Container status check
#   - Database connectivity
#   - Schema and table verification
#   - Data integrity checks
#   - Search capabilities (fuzzy, vector)
#   - Performance diagnostics
#
# Exit codes:
#   0 - All checks passed
#   1 - Some checks failed
#
# Author: Lab01-MCP Team
# Created: 2025-10-18
# ============================================================================

set -u

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$SQL_ROOT_DIR/.env"

# Load environment variables from .env
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️  Warning: .env file not found at $ENV_FILE, using default SCHEMA_NAME=test"
    SCHEMA_NAME="test"
fi

# Set default schema if not in .env
SCHEMA_NAME="${SCHEMA_NAME:-test}"

# Mode
QUICK_MODE=false
DETAILED_MODE=false

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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
    echo ""
}

check() {
    echo -ne "${BLUE}🔍 Checking $1...${NC}"
}

# ============================================================================
# VERIFICATION FUNCTIONS
# ============================================================================

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
        error "Start container: cd ../DockerConfig && docker-compose up -d"
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

verify_schema() {
    check "Schema "${SCHEMA_NAME}""
    
    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    
    if [ "$count" == "1" ]; then
        echo -e "\r${GREEN}✅ Schema exists${NC}                        "
        return 0
    else
        echo -e "\r${RED}❌ Schema not found${NC}                   "
        return 1
    fi
}

verify_tables() {
    check "Database tables"
    
    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    
    if [ "$count" -ge "14" ]; then
        echo -e "\r${GREEN}✅ Found $count tables (expected 14+)${NC}    "
        return 0
    else
        echo -e "\r${YELLOW}⚠️  Found $count/14 tables${NC}             "
        return 1
    fi
}

verify_products() {
    check "Products data"
    
    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM "${SCHEMA_NAME}".products;" 2>/dev/null | xargs)
    
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
        "SELECT COUNT(*) FROM "${SCHEMA_NAME}".products WHERE embedding IS NOT NULL;" 2>/dev/null | xargs)
    
    if [ "$count" == "90" ]; then
        echo -e "\r${GREEN}✅ All 90 embeddings ready${NC}             "
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
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    
    if [ "$count" -ge "50" ]; then
        echo -e "\r${GREEN}✅ Found $count indexes${NC}               "
        return 0
    else
        echo -e "\r${YELLOW}⚠️  Found $count indexes${NC}              "
        return 1
    fi
}

verify_functions() {
    check "Database functions"
    
    local count=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    
    if [ "$count" -ge "20" ]; then
        echo -e "\r${GREEN}✅ Found $count functions${NC}             "
        return 0
    else
        echo -e "\r${YELLOW}⚠️  Found $count functions${NC}            "
        return 1
    fi
}

test_search() {
    check "Search capabilities"
    
    local fuzzy=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM "${SCHEMA_NAME}".products WHERE similarity(normalize_text(name), normalize_text('laptop')) > 0.3;" 2>/dev/null | xargs)
    
    if [ "$fuzzy" -gt "0" ]; then
        echo -e "\r${GREEN}✅ Fuzzy search working ($fuzzy results)${NC} "
        return 0
    else
        echo -e "\r${RED}❌ Search not available${NC}               "
        return 1
    fi
}

# ============================================================================
# DETAILED REPORT
# ============================================================================

print_detailed_report() {
    header "DETAILED DATABASE DIAGNOSTICS"
    
    echo -e "${CYAN}📊 Container Information${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if docker ps --format '{{.Names}}' | grep -q "mcp-postgres"; then
        info "Container: mcp-postgres"
        info "Status: $(docker inspect -f '{{.State.Status}}' mcp-postgres)"
        info "Port: 5434 → 5432"
    fi
    
    echo ""
    echo -e "${CYAN}📋 Schema Objects${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local tables=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    local indexes=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    local functions=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname='${SCHEMA_NAME}';" 2>/dev/null | xargs)
    
    info "Tables: $tables"
    info "Indexes: $indexes"
    info "Functions: $functions"
    
    echo ""
    echo -e "${CYAN}📦 Data Status${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local products=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM "${SCHEMA_NAME}".products;" 2>/dev/null | xargs)
    local embeddings=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM "${SCHEMA_NAME}".products WHERE embedding IS NOT NULL;" 2>/dev/null | xargs)
    
    info "Products: $products"
    info "Embeddings: $embeddings"
    
    echo ""
    echo -e "${CYAN}🔍 Search Capabilities${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    local fuzzy=$(docker exec mcp-postgres psql -U mcp_user -d mcpdb -t -c \
        "SELECT COUNT(*) FROM "${SCHEMA_NAME}".products WHERE similarity(normalize_text(name), normalize_text('laptop')) > 0.3;" 2>/dev/null | xargs)
    info "Fuzzy search results for 'laptop': $fuzzy"
    info "Vector search: $([ "$embeddings" -gt "0" ] && echo 'Available' || echo 'Not available')"
    
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

print_help() {
    cat << EOF
Lab01-MCP Database Verification Script

USAGE:
    ./verify.sh [OPTIONS]

OPTIONS:
    --help              Show this help message
    --quick             Quick checks only (5 checks)
    --detailed          Detailed diagnostics (11 checks + report)

EXAMPLES:
    ./verify.sh                # Full verification
    ./verify.sh --quick        # Quick health check
    ./verify.sh --detailed     # Detailed diagnostics

DATABASE INFO:
    Container: mcp-postgres
    Port: 5434 (external) / 5432 (internal)
    Database: mcpdb
    User: mcp_user
    Schema: test

EXIT CODES:
    0 - All checks passed
    1 - Some checks failed

EOF
}

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
            --detailed)
                DETAILED_MODE=true
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
    
    local errors=0
    
    # Quick checks
    echo -e "${CYAN}Running health checks...${NC}"
    echo ""
    
    verify_container || ((errors++))
    verify_connection || ((errors++))
    verify_schema || ((errors++))
    verify_tables || ((errors++))
    verify_products || ((errors++))
    
    if [ "$QUICK_MODE" = false ]; then
        echo ""
        echo -e "${CYAN}Running detailed checks...${NC}"
        echo ""
        
        verify_embeddings || ((errors++))
        verify_indexes || ((errors++))
        verify_functions || ((errors++))
        test_search || ((errors++))
    fi
    
    # Detailed report
    if [ "$DETAILED_MODE" = true ]; then
        print_detailed_report
    fi
    
    # Summary
    echo ""
    header "VERIFICATION SUMMARY"
    
    if [ $errors -eq 0 ]; then
        success "All checks passed! Database is healthy. 🎉"
        info "Port: 5434"
        info "Database: mcpdb (Schema: test)"
        echo ""
        exit 0
    else
        error "Found $errors issue(s)"
        warning "Run './deploy.sh' to fix issues"
        echo ""
        exit 1
    fi
}

main "$@"

