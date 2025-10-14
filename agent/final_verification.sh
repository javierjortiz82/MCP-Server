#!/bin/bash
# Final Verification Script - OdiseoBotV2 Migration
# Run this script before production deployment
# Version: 1.0.0
# Date: 2025-10-12

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                        ║"
echo "║  🔍 FINAL VERIFICATION - OdiseoBotV2 Migration                         ║"
echo "║                                                                        ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Function to run test
run_test() {
    local test_name=$1
    local test_command=$2

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 Test: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if eval "$test_command"; then
        print_result 0 "$test_name"
    else
        print_result 1 "$test_name"
    fi
}

# ============================================================================
# 1. DOCUMENTATION VERIFICATION
# ============================================================================

echo ""
echo "📚 PHASE 1: Documentation Verification"
echo "════════════════════════════════════════════════════════════════════════"

run_test "Feature comparison exists" "[ -f 'docs/LEGACY_VS_V2_FEATURE_COMPARISON.md' ]"
run_test "Migration guide exists" "[ -f 'docs/MIGRATION_ODISEOBOT_V2.md' ]"
run_test "Production checklist exists" "[ -f 'docs/ODISEOBOT_V2_PRODUCTION_CHECKLIST.md' ]"
run_test "Rollback strategy exists" "[ -f 'docs/ROLLBACK_STRATEGY.md' ]"
run_test "Executive summary exists" "[ -f 'docs/MIGRATION_EXECUTIVE_SUMMARY.md' ]"

# ============================================================================
# 2. CODE FILES VERIFICATION
# ============================================================================

echo ""
echo "💻 PHASE 2: Code Files Verification"
echo "════════════════════════════════════════════════════════════════════════"

run_test "OdiseoBotV2 source exists" "[ -f 'src/multi_agent/odiseo_bot_v2.py' ]"
run_test "Integration tests exist" "[ -f 'test_odiseo_bot_v2_integration.py' ]"
run_test "Bot factory exists" "[ -f '../client_mcp/core/bot_factory.py' ]"
run_test "Legacy OdiseoBot exists" "[ -f '../client_mcp/core/odiseo_bot.py' ]"

# ============================================================================
# 3. UNIT TESTS
# ============================================================================

echo ""
echo "🧪 PHASE 3: Unit Tests"
echo "════════════════════════════════════════════════════════════════════════"

run_test "Unit tests pass" "pytest test_odiseo_bot_v2.py -v --tb=short -q"

# ============================================================================
# 4. INTEGRATION TESTS
# ============================================================================

echo ""
echo "🔗 PHASE 4: Integration Tests"
echo "════════════════════════════════════════════════════════════════════════"

run_test "Integration tests pass" "pytest test_odiseo_bot_v2_integration.py -v --tb=short -q"

# ============================================================================
# 5. FEATURE FLAG VERIFICATION (DEPRECATED - bot_factory.py removed)
# ============================================================================

echo ""
echo "🚦 PHASE 5: Feature Flag Verification"
echo "════════════════════════════════════════════════════════════════════════"
echo "⚠️  DEPRECATED: bot_factory.py was removed (v3.0.0)"
echo "    Use AgentOrchestrator with ENABLE_AGENT_ROUTING flag instead"
echo "    Skipping legacy bot_factory tests..."

# DEPRECATED: bot_factory.py removed in v3.0.0
# Test V2 enabled
# run_test "Feature flag V2 works" "USE_ODISEO_V2=true PYTHONPATH=/home/javort/Lab01-MCP:/home/javort/Lab01-MCP/agent/src:\$PYTHONPATH python3 -c \"from client_mcp.core.bot_factory import get_active_bot_version; assert 'V2' in get_active_bot_version()\""

# Test Legacy enabled
# run_test "Feature flag Legacy works" "USE_ODISEO_V2=false PYTHONPATH=/home/javort/Lab01-MCP:/home/javort/Lab01-MCP/agent/src:/home/javort/Lab01-MCP/client_mcp:\$PYTHONPATH python3 -c \"from client_mcp.core.bot_factory import get_active_bot_version; assert 'Legacy' in get_active_bot_version()\""

# ============================================================================
# 6. SMOKE TEST (DEPRECATED - bot_factory.py removed)
# ============================================================================

echo ""
echo "🔥 PHASE 6: Smoke Test (End-to-End)"
echo "════════════════════════════════════════════════════════════════════════"
echo "⚠️  DEPRECATED: bot_factory.py was removed (v3.0.0)"
echo "    Use AgentOrchestrator for end-to-end testing"
echo "    Skipping legacy bot_factory smoke test..."

# DEPRECATED: bot_factory.py removed in v3.0.0
# SMOKE_TEST='
# import asyncio
# from client_mcp.core.bot_factory import create_odiseo_bot
#
# async def test():
#     bot = create_odiseo_bot(user_id="final_verification")
#     await bot.initialize()
#     response = await bot.send_message("test query")
#     assert len(response) > 0
#     await bot.cleanup()
#
# asyncio.run(test())
# '
#
# run_test "Smoke test passes" "USE_ODISEO_V2=true PYTHONPATH=/home/javort/Lab01-MCP:/home/javort/Lab01-MCP/agent/src:\$PYTHONPATH python3 -c '$SMOKE_TEST'"

# ============================================================================
# 7. ROLLBACK TEST (DEPRECATED - bot_factory.py removed)
# ============================================================================

echo ""
echo "🔄 PHASE 7: Rollback Test"
echo "════════════════════════════════════════════════════════════════════════"
echo "⚠️  DEPRECATED: bot_factory.py was removed (v3.0.0)"
echo "    Feature flag USE_ODISEO_V2 no longer exists"
echo "    Use ENABLE_AGENT_ROUTING for multi-agent routing"
echo "    Skipping legacy rollback test..."

# DEPRECATED: bot_factory.py removed in v3.0.0
# Test V2 → Legacy → V2 rollback
# ROLLBACK_TEST='
# from client_mcp.core.bot_factory import get_active_bot_version, set_bot_version
# import warnings
# warnings.simplefilter("ignore", DeprecationWarning)
#
# # Start with V2
# set_bot_version(True)
# assert "V2" in get_active_bot_version(), "V2 not active"
#
# # Rollback to Legacy
# set_bot_version(False)
# assert "Legacy" in get_active_bot_version(), "Legacy not active after rollback"
#
# # Restore to V2
# set_bot_version(True)
# assert "V2" in get_active_bot_version(), "V2 not active after restore"
#
# print("Rollback cycle: V2 → Legacy → V2 ✅")
# '
#
# run_test "Rollback cycle works" "PYTHONPATH=/home/javort/Lab01-MCP:/home/javort/Lab01-MCP/agent/src:/home/javort/Lab01-MCP/client_mcp:\$PYTHONPATH python3 -c '$ROLLBACK_TEST'"

# ============================================================================
# FINAL SUMMARY
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                        ║"
echo "║  📊 VERIFICATION SUMMARY                                               ║"
echo "║                                                                        ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

# Exit code
if [ $TESTS_FAILED -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                        ║"
    echo "║  ✅ ALL CHECKS PASSED - READY FOR PRODUCTION                          ║"
    echo "║                                                                        ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Next Steps:"
    echo "1. Deploy to staging with ENABLE_AGENT_ROUTING=false (single-agent)"
    echo "2. Monitor for 24 hours"
    echo "3. Enable multi-agent gradually: ENABLE_AGENT_ROUTING=true"
    echo "4. Monitor metrics continuously"
    echo "5. Execute rollback if issues detected"
    echo ""
    echo "Documentation:"
    echo "- Multi-Agent Guide: docs/USE_ODISEO_V2_ELIMINATION_PLAN.md"
    echo "- Memory Activation: docs/MEMORY_ACTIVATION_GUIDE.md"
    echo "- Booking System: docs/NOTAS_CLAUDE.md"
    echo ""
    echo "⚠️  Note: Legacy migration docs archived in docs/archive/migration_legacy/"
    echo ""
    exit 0
else
    echo "╔════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                        ║"
    echo "║  ❌ VERIFICATION FAILED - NOT READY FOR PRODUCTION                    ║"
    echo "║                                                                        ║"
    echo "╚════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Please fix the failed tests before proceeding to production."
    echo ""
    exit 1
fi
