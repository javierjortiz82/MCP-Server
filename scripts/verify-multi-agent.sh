#!/bin/bash

# Lab01-MCP Multi-Agent System - Verification Script
# Version: 2.2.0-dev
# Date: 2025-10-11

set -e

echo "=============================================="
echo "🔍 Lab01-MCP Multi-Agent System Verification"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counter
CHECKS_PASSED=0
CHECKS_FAILED=0

check_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $description - File not found: $file"
        ((CHECKS_FAILED++))
        return 1
    fi
}

check_directory() {
    local dir=$1
    local description=$2

    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}❌${NC} $description - Directory not found: $dir"
        ((CHECKS_FAILED++))
        return 1
    fi
}

echo "📦 Checking Multi-Agent System Files..."
echo ""

# Multi-Agent System
check_directory "agent/src/multi_agent" "Multi-agent directory exists"
check_file "agent/src/multi_agent/__init__.py" "Multi-agent __init__.py"
check_file "agent/src/multi_agent/agent_router.py" "AgentRouter (Intent Classification)"
check_file "agent/src/multi_agent/booking_agent.py" "BookingAgent"
check_file "agent/src/multi_agent/general_agent.py" "GeneralAgent"

echo ""
echo "🎯 Checking Orchestrator..."
echo ""

check_file "client_mcp/core/agent_orchestrator.py" "AgentOrchestrator"

echo ""
echo "📅 Checking Booking System Files..."
echo ""

# Booking Tools
check_file "mcp_server/tools/bookings.py" "Booking business logic"
check_file "mcp_server/mcp_handlers/booking_handlers.py" "Booking MCP handlers"
check_file "mcp_server/utils/google_calendar.py" "Google Calendar client"

echo ""
echo "🗄️ Checking Database Files..."
echo ""

# Database Schema
check_file "SQL/scripts/create_bookings_schema.sql" "Booking schema SQL"
check_file "SQL/scripts/init-bookings.sh" "Booking initialization script"
check_file "SQL/src/init_bookings.py" "Python booking initializer"
check_file "SQL/src/seed_booking_data.py" "Booking data seeder"

echo ""
echo "⚙️ Checking Configuration Files..."
echo ""

check_file ".env.example" ".env.example updated"
check_file "client_mcp/config/settings.py" "Client configuration"
check_file "mcp_server/config/settings.py" "Server configuration"

echo ""
echo "📚 Checking Documentation..."
echo ""

check_file "README.md" "README.md updated"
check_file "docs/NOTAS_CLAUDE.md" "Technical notes"

echo ""
echo "🧪 Running Quality Checks..."
echo ""

# Check if files are properly formatted
if command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⏳${NC} Running Python syntax checks..."

    SYNTAX_ERRORS=0
    for file in agent/src/multi_agent/*.py client_mcp/core/agent_orchestrator.py mcp_server/tools/bookings.py mcp_server/mcp_handlers/booking_handlers.py mcp_server/utils/google_calendar.py; do
        if [ -f "$file" ]; then
            if python3 -m py_compile "$file" 2>/dev/null; then
                echo -e "${GREEN}✅${NC} Syntax OK: $file"
                ((CHECKS_PASSED++))
            else
                echo -e "${RED}❌${NC} Syntax Error: $file"
                ((CHECKS_FAILED++))
                SYNTAX_ERRORS=1
            fi
        fi
    done
else
    echo -e "${YELLOW}⚠️${NC}  Python3 not found - skipping syntax checks"
fi

echo ""
echo "=============================================="
echo "📊 Verification Summary"
echo "=============================================="
echo ""
echo -e "${GREEN}✅ Checks Passed: $CHECKS_PASSED${NC}"
echo -e "${RED}❌ Checks Failed: $CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! Ready for testing.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run: bash SQL/scripts/init-bookings.sh"
    echo "2. Configure .env file"
    echo "3. Test legacy mode: ENABLE_AGENT_ROUTING=false python -m client_mcp"
    echo "4. Test multi-agent: ENABLE_AGENT_ROUTING=true python -m client_mcp"
    exit 0
else
    echo -e "${RED}⚠️  Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
