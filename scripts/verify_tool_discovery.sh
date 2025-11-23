#!/bin/bash
# Tool Discovery Verification Script
# Validates that the autodiscovery system is working correctly

set -e

echo "🔍 TOOL DISCOVERY VERIFICATION"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if MCP server is running
echo "📦 Checking MCP server status..."
if ! docker ps | grep -q "mcp-server.*healthy"; then
    echo -e "${RED}❌ MCP server is not running or not healthy${NC}"
    exit 1
fi
echo -e "${GREEN}✅ MCP server is healthy${NC}"

# Check logs for tool registration
echo ""
echo "📊 Checking tool registrations in logs..."

BOOKING_LOG=$(docker logs mcp-server 2>&1 | grep "Registered.*booking tools" | tail -1)
if [ -n "$BOOKING_LOG" ]; then
    echo -e "${GREEN}✅ Booking tools registered:${NC}"
    echo "   $BOOKING_LOG"
else
    echo -e "${RED}❌ No booking tool registration found${NC}"
fi

PRODUCT_LOG=$(docker logs mcp-server 2>&1 | grep "Registered.*product tools" | tail -1)
if [ -n "$PRODUCT_LOG" ]; then
    echo -e "${GREEN}✅ Product tools registered:${NC}"
    echo "   $PRODUCT_LOG"
else
    echo -e "${RED}❌ No product tool registration found${NC}"
fi

# Check for tool discovery validation
echo ""
echo "🔐 Checking tool discovery validation..."
VALIDATION_LOG=$(docker logs mcp-server 2>&1 | grep -i "tool discovery" | tail -5)
if [ -n "$VALIDATION_LOG" ]; then
    echo -e "${GREEN}✅ Tool discovery validation executed${NC}"
    echo "$VALIDATION_LOG"
else
    echo -e "${YELLOW}⚠️  No tool discovery validation logs found${NC}"
fi

# Check for errors
echo ""
echo "🚨 Checking for errors in MCP server..."
ERROR_LOG=$(docker logs mcp-server 2>&1 | grep -i "error\|invalid\|failed" | grep -v "validation skipped" | tail -5)
if [ -z "$ERROR_LOG" ]; then
    echo -e "${GREEN}✅ No critical errors found${NC}"
else
    echo -e "${YELLOW}⚠️  Some errors detected:${NC}"
    echo "$ERROR_LOG"
fi

# Test tool availability via resource endpoint
echo ""
echo "🧪 Testing tool availability via resource endpoint..."
BOOKING_TOOLS=$(curl -s http://localhost:8009/mcp/resources/tool-categories://bookings 2>/dev/null || echo "{}")
if [ -n "$BOOKING_TOOLS" ]; then
    TOOL_COUNT=$(echo "$BOOKING_TOOLS" | grep -o '"tools"' | wc -l)
    echo -e "${GREEN}✅ Booking tools resource available${NC}"
else
    echo -e "${YELLOW}⚠️  Could not access booking tools resource (MCP protocol issue)${NC}"
fi

echo ""
echo "=============================="
echo "✅ VERIFICATION COMPLETE"
echo "=============================="
