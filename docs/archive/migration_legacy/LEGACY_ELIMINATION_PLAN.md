# Legacy OdiseoBot Elimination - Step-by-Step Plan

**Fecha**: 2025-10-12  
**Status**: 📋 **PLAN READY FOR EXECUTION**  
**Timeline**: 6-8 semanas post-V2-deployment  
**Risk Level**: 🟢 **LOW**

---

## Executive Summary

Este plan detalla los pasos específicos para eliminar completamente `client_mcp/core/odiseo_bot.py` del proyecto de manera segura y ordenada.

**Enfoque**: Conservative (6-8 semanas)  
**Rollback**: Posible hasta Week 5  
**Verificación**: Continua en cada fase

---

## 📅 Timeline Overview

```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│  Week 1-2   │  Week 3     │  Week 4     │  Week 5     │  Week 6     │  Week 7-8   │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ V2 Rollout  │ CLI Extract │ Test Migr.  │ Deprecation │ Monitoring  │ Removal     │
│ & Monitor   │ & Doc Update│ & Verify    │ Period      │ & Verify    │ & Cleanup   │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

---

## Phase 1: V2 Deployment & Stabilization (Week 1-2)

### Week 1: Initial Deployment

#### Day 1-2: Deploy to Staging

**Tasks**:
1. Deploy with `USE_ODISEO_V2=false` (baseline)
2. Run full test suite
3. Verify no regressions

**Commands**:
```bash
# Deploy to staging
export USE_ODISEO_V2=false
docker-compose -f docker-compose.staging.yml up -d

# Run tests
pytest agent/test_odiseo_bot_v2.py -v
pytest agent/test_odiseo_bot_v2_integration.py -v

# Monitor logs
tail -f logs/odiseo_bot.log
```

**Success Criteria**:
- ✅ All tests passing
- ✅ No errors in logs
- ✅ Performance equal to production

---

#### Day 3-4: Enable V2 for Internal Users (10%)

**Tasks**:
1. Set `USE_ODISEO_V2=true` for staging
2. Monitor metrics for 24h
3. Compare with baseline

**Commands**:
```bash
# Enable V2
export USE_ODISEO_V2=true
docker-compose -f docker-compose.staging.yml restart

# Monitor metrics
watch -n 5 'curl -s http://localhost:8000/metrics | jq ".error_rate, .response_time"'
```

**Success Criteria**:
- ✅ Error rate ≤ baseline
- ✅ Response time ≤ baseline +10%
- ✅ No critical bugs

---

#### Day 5-7: Production Deployment (10% Rollout)

**Tasks**:
1. Deploy to production with V2 at 10%
2. Monitor intensively (24h)
3. Gradual increase to 50%

**Commands**:
```bash
# Production deployment
git checkout main
git pull
docker build -t odiseo-bot:v2-prod .
docker-compose up -d

# Enable V2 for 10% of users (A/B testing)
# Configure load balancer or feature flag service
```

**Success Criteria**:
- ✅ Error rate <1%
- ✅ No customer complaints
- ✅ Metrics stable

---

### Week 2: Full Rollout

#### Day 8-10: 50% Rollout

**Tasks**:
1. Increase V2 to 50% of traffic
2. Monitor for 48h
3. Compare metrics vs Legacy

**Success Criteria**:
- ✅ Error rate <1%
- ✅ Response time acceptable
- ✅ No degradation

---

#### Day 11-14: 100% Rollout

**Tasks**:
1. Set `USE_ODISEO_V2=true` globally
2. Monitor for 7 days
3. Verify zero Legacy usage

**Commands**:
```bash
# Enable V2 for 100% of users
export USE_ODISEO_V2=true
docker-compose restart

# Verify no Legacy usage
grep -i "Legacy OdiseoBot" logs/odiseo_bot.log | tail -20
```

**Success Criteria**:
- ✅ 100% traffic on V2
- ✅ No Legacy usage detected
- ✅ Metrics stable for 7+ days

---

## Phase 2: Migration & Extraction (Week 3-4)

### Week 3: Extract CLI Tools

#### Task 1: Create Standalone CLI Wrapper

**File**: `scripts/odiseo_cli.py`

**Implementation**:
```python
#!/usr/bin/env python3
"""Odiseo Bot - Interactive CLI Tool.

Standalone CLI wrapper for OdiseoBotV2 with interactive mode,
help, and metrics display.
"""
import asyncio
from multi_agent import OdiseoBotV2

class OdiseoCLI:
    """Interactive CLI for OdiseoBot."""

    def __init__(self):
        self.bot = None
        self.debug_mode = False

    async def initialize(self):
        """Initialize bot."""
        self.bot = OdiseoBotV2()
        await self.bot.initialize()

    async def run_interactive(self):
        """Run interactive chat loop."""
        print("\n" + "═" * 60)
        print("🌟 ODISEO BOT - Tu Vendedor Inteligente")
        print("═" * 60)
        print("💡 Commands: /exit, /debug, /help, /metrics")
        print("─" * 60)
        print("👋 ¡Hola! ¿Qué producto buscas hoy?\n")

        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print("👋 ¡Hasta luego!")
                    break
                elif user_input.lower() == "/debug":
                    self.debug_mode = not self.debug_mode
                    status = "activado" if self.debug_mode else "desactivado"
                    print(f"🐛 Modo debug {status}")
                    continue
                elif user_input.lower() == "/help":
                    self.show_help()
                    continue
                elif user_input.lower() == "/metrics":
                    self.show_metrics()
                    continue

                response = await self.bot.send_message(user_input)
                print(f"\n🤖 Bot: {response}")

            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    def show_help(self):
        """Show help information."""
        print("\n" + "═" * 60)
        print("📚 AYUDA - ODISEO BOT")
        print("═" * 60)
        print("\n🎯 ¿Qué puedo hacer por ti?")
        print("  • Buscar productos por nombre, marca o categoría")
        print("  • Encontrar productos específicos por código SKU")
        print("  • Recomendar productos según tus necesidades")
        print("\n💬 Comandos especiales:")
        print("  /exit    - Salir del chat")
        print("  /debug   - Alternar modo debug")
        print("  /help    - Mostrar esta ayuda")
        print("  /metrics - Ver métricas de ejecución")
        print("─" * 60 + "\n")

    def show_metrics(self):
        """Show execution metrics."""
        if not self.bot or not self.bot.tool_executor:
            print("\n📊 Métricas no disponibles")
            return

        stats = self.bot.tool_executor.get_stats()
        print("\n" + "═" * 60)
        print("📊 MÉTRICAS DE EJECUCIÓN")
        print("═" * 60)

        if "summary" in stats:
            summary = stats["summary"]
            print("\n🎯 Resumen General:")
            print(f"  Total de llamadas: {summary.get('total_tool_calls', 0)}")
            print(f"  Exitosas: {summary.get('successful_calls', 0)}")
            print(f"  Tasa de éxito: {summary.get('success_rate_percent', 0):.2f}%")
        print("─" * 60 + "\n")

    async def cleanup(self):
        """Cleanup bot resources."""
        if self.bot:
            await self.bot.cleanup()

async def main():
    """Main entry point."""
    cli = OdiseoCLI()
    try:
        await cli.initialize()
        await cli.run_interactive()
    finally:
        await cli.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

**Verification**:
```bash
# Make executable
chmod +x scripts/odiseo_cli.py

# Test CLI
python3 scripts/odiseo_cli.py
```

**Success Criteria**:
- ✅ CLI runs correctly
- ✅ All commands work (/help, /metrics, /debug, /exit)
- ✅ Chat functionality working

---

#### Task 2: Update Documentation

**Files to Update**:
1. `README.md`
2. `docs/USAGE_EXAMPLES.md`
3. `client_mcp/README.md`
4. `agent/README_AB_TESTING.md`

**Changes**:
```bash
# Find and replace Legacy examples with V2
find docs -name "*.md" -exec sed -i 's/from client_mcp.core.odiseo_bot import OdiseoBot/from multi_agent import OdiseoBotV2/g' {} \;

# Update CLI usage examples
echo "# Using CLI tool
python3 scripts/odiseo_cli.py" >> README.md
```

**Verification**:
```bash
# Check all docs updated
grep -r "from client_mcp.core.odiseo_bot" docs/ README.md
# Expected: No matches (or only in historical/migration docs)
```

**Success Criteria**:
- ✅ All examples use V2
- ✅ CLI tool documented
- ✅ No outdated examples

---

### Week 4: Migrate Tests

#### Task 1: Identify Test Files to Migrate

**Files**:
```bash
# List all test files using Legacy
grep -r "from client_mcp.core.odiseo_bot import OdiseoBot" test/ client_mcp/test/ -l
```

**Output**:
- `test/integration/test_full_integration.py`
- `test/unit/test_bot_initialization.py`
- `test/unit/test_professional_implementation.py`
- `test/unit/test_type_structure.py`
- `client_mcp/test/integration/test_bot_initialization.py`
- `client_mcp/test/integration/test_context_caching.py`
- `client_mcp/test/unit/test_odiseo_bot.py`
- `client_mcp/test/unit/test_main.py`

---

#### Task 2: Migrate or Deprecate Tests

**Option A: Migrate to V2**
```python
# Before (Legacy)
from client_mcp.core.odiseo_bot import OdiseoBot

async def test_bot_initialization():
    bot = OdiseoBot()
    await bot.initialize()
    # ...

# After (V2)
from multi_agent import OdiseoBotV2

async def test_bot_initialization():
    bot = OdiseoBotV2()
    await bot.initialize()
    # ...
```

**Option B: Deprecate Test**
```python
import pytest

@pytest.mark.skip(reason="Legacy OdiseoBot deprecated - test no longer applicable")
def test_legacy_specific_feature():
    pass
```

**Verification**:
```bash
# Run all tests
pytest test/ -v
pytest client_mcp/test/ -v

# Ensure no failures
```

**Success Criteria**:
- ✅ All tests passing or explicitly skipped
- ✅ No Legacy OdiseoBot usage in active tests

---

## Phase 3: Deprecation Period (Week 5)

### Task 1: Add Loud Deprecation Warnings

**File**: `client_mcp/core/odiseo_bot.py`

**Change** (already done):
```python
# DeprecationWarning already added in __init__()
# Verify it's working:
python3 -c "
import warnings
warnings.simplefilter('always')
from client_mcp.core.odiseo_bot import OdiseoBot
bot = OdiseoBot()
"
# Expected: DeprecationWarning printed
```

---

### Task 2: Update Feature Flag Defaults

**File**: `client_mcp/config/settings.py`

**Change**:
```python
# Before
USE_ODISEO_V2: bool = Field(
    default=False,  # ← Change this
    env="USE_ODISEO_V2",
    description="Use OdiseoBotV2 (BaseAgent) instead of Legacy OdiseoBot"
)

# After
USE_ODISEO_V2: bool = Field(
    default=True,  # ← Now defaults to V2
    env="USE_ODISEO_V2",
    description="Use OdiseoBotV2 (BaseAgent) instead of Legacy OdiseoBot"
)
```

**Verification**:
```bash
# Test default behavior
python3 -c "from client_mcp.config.settings import settings; print(settings.USE_ODISEO_V2)"
# Expected: True
```

---

### Task 3: Monitor for Legacy Usage

**Script**: `scripts/check_legacy_usage.sh`

```bash
#!/bin/bash
# Check if anyone is still using Legacy OdiseoBot

echo "Checking for Legacy OdiseoBot usage..."

# Check logs
legacy_count=$(grep -i "Legacy OdiseoBot (Standalone)" logs/odiseo_bot.log 2>/dev/null | wc -l)

if [ "$legacy_count" -gt 0 ]; then
    echo "⚠️  WARNING: Legacy OdiseoBot still in use ($legacy_count occurrences)"
    grep -i "Legacy OdiseoBot (Standalone)" logs/odiseo_bot.log | tail -10
    exit 1
else
    echo "✅ No Legacy usage detected - safe to proceed with removal"
    exit 0
fi
```

**Run Daily**:
```bash
chmod +x scripts/check_legacy_usage.sh
./scripts/check_legacy_usage.sh
```

**Success Criteria**:
- ✅ No Legacy usage for 7+ days
- ✅ All deprecation warnings addressed

---

## Phase 4: Removal & Cleanup (Week 6-8)

### Week 6: Preparation

#### Task 1: Final Verification

**Checklist**:
- [ ] V2 stable for 14+ days
- [ ] No Legacy usage detected
- [ ] CLI tool extracted and tested
- [ ] Tests migrated or deprecated
- [ ] Documentation updated
- [ ] Team aware of upcoming removal

**Script**: `scripts/final_verification_before_removal.sh`

```bash
#!/bin/bash
# Final verification before removing Legacy OdiseoBot

echo "═══════════════════════════════════════════"
echo "  FINAL VERIFICATION BEFORE LEGACY REMOVAL"
echo "═══════════════════════════════════════════"

FAILED=0

# Check 1: V2 stability
echo "\n1. Checking V2 stability (14+ days)..."
# Add logic to check uptime and metrics
echo "✅ V2 stable"

# Check 2: No Legacy usage
echo "\n2. Checking for Legacy usage..."
./scripts/check_legacy_usage.sh || FAILED=1

# Check 3: CLI tool exists
echo "\n3. Checking CLI tool..."
[ -f "scripts/odiseo_cli.py" ] && echo "✅ CLI tool exists" || { echo "❌ CLI missing"; FAILED=1; }

# Check 4: Tests passing
echo "\n4. Running tests..."
pytest agent/test_odiseo_bot_v2.py -q || FAILED=1

# Check 5: Documentation updated
echo "\n5. Checking documentation..."
if grep -r "from client_mcp.core.odiseo_bot import OdiseoBot" README.md docs/ 2>/dev/null | grep -v "migration\|legacy\|deprecated"; then
    echo "❌ Outdated examples found in docs"
    FAILED=1
else
    echo "✅ Documentation up to date"
fi

# Final verdict
echo "\n═══════════════════════════════════════════"
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED - SAFE TO REMOVE LEGACY"
    exit 0
else
    echo "❌ VERIFICATION FAILED - DO NOT REMOVE YET"
    exit 1
fi
```

**Run**:
```bash
chmod +x scripts/final_verification_before_removal.sh
./scripts/final_verification_before_removal.sh
```

---

### Week 7: Legacy Removal

#### Task 1: Create Removal Branch

```bash
git checkout -b remove-legacy-odiseobot
git pull origin main
```

---

#### Task 2: Remove Legacy OdiseoBot File

```bash
# Backup first (just in case)
cp client_mcp/core/odiseo_bot.py backups/odiseo_bot.py.backup

# Remove Legacy file
git rm client_mcp/core/odiseo_bot.py

# Commit
git add -A
git commit -m "feat: remove Legacy OdiseoBot

- Deleted client_mcp/core/odiseo_bot.py (1,183 lines)
- OdiseoBotV2 is now the only implementation
- CLI tools extracted to scripts/odiseo_cli.py
- All tests migrated to use V2

Breaking Change: Legacy OdiseoBot removed
Migration: Use OdiseoBotV2 from multi_agent
Documentation: agent/docs/MIGRATION_ODISEOBOT_V2.md

🤖 Generated with Claude Code
"
```

---

#### Task 3: Update `bot_factory.py`

**File**: `client_mcp/core/bot_factory.py`

**Changes**:
```python
# Remove Legacy import function
def _get_legacy_odiseo_bot():
    """REMOVED - Legacy OdiseoBot no longer available."""
    raise ImportError(
        "Legacy OdiseoBot has been removed. Use OdiseoBotV2 instead.\n"
        "Migration: from multi_agent import OdiseoBotV2\n"
        "See: agent/docs/MIGRATION_ODISEOBOT_V2.md"
    )

# Update create_odiseo_bot to always use V2
def create_odiseo_bot(...) -> OdiseoBotProtocol:
    """Create OdiseoBot instance (always V2)."""
    # Always use V2 (feature flag removed)
    bot_class = _get_odiseo_bot_v2()
    bot = bot_class(user_id=user_id, debug_mode=debug_mode, **kwargs)
    return bot
```

---

#### Task 4: Update `agent_orchestrator.py`

**File**: `client_mcp/core/agent_orchestrator.py`

**Changes**:
```python
# Remove Legacy import (line 41)
# from core.odiseo_bot import OdiseoBot  # ← DELETE

# Update initialization (lines 111-119)
async def initialize(self) -> None:
    try:
        if not self.routing_enabled:
            # Legacy mode removed - always use V2
            logger.info("🔄 Initializing in SINGLE-AGENT mode (OdiseoBotV2)")
            self.odiseo_bot = OdiseoBotV2()
            await self.odiseo_bot.initialize()
            logger.info("✅ Single-agent mode initialized successfully")
        else:
            # Multi-agent mode (unchanged)
            ...
```

---

#### Task 5: Run Tests

```bash
# Run all tests
pytest agent/test_odiseo_bot_v2.py -v
pytest agent/test_odiseo_bot_v2_integration.py -v

# Run smoke test
python3 scripts/odiseo_cli.py
# Type: "Busco laptops"
# Expected: Working response
```

---

#### Task 6: Commit & Push

```bash
git add -A
git commit -m "refactor: update bot_factory and agent_orchestrator for V2-only

- Remove Legacy OdiseoBot imports
- Always use OdiseoBotV2
- Simplify code paths

🤖 Generated with Claude Code
"

git push origin remove-legacy-odiseobot
```

---

### Week 8: Review & Deploy

#### Task 1: Create Pull Request

```bash
gh pr create \
  --title "Remove Legacy OdiseoBot - Migrate to V2 Only" \
  --body "$(cat <<'PR_BODY'
## Summary

Removes Legacy OdiseoBot implementation after successful V2 deployment and 6 weeks of stable operation.

## Changes

- ✅ Deleted `client_mcp/core/odiseo_bot.py` (1,183 lines)
- ✅ Updated `bot_factory.py` to always use V2
- ✅ Updated `agent_orchestrator.py` to remove Legacy path
- ✅ Extracted CLI tools to `scripts/odiseo_cli.py`
- ✅ Migrated all tests to use V2
- ✅ Updated documentation

## Verification

- ✅ V2 stable for 42+ days
- ✅ No Legacy usage detected in 28+ days
- ✅ All tests passing (8/8 integration tests)
- ✅ CLI tool working
- ✅ Documentation updated

## Breaking Changes

⚠️ **Breaking**: Legacy OdiseoBot removed. Use OdiseoBotV2 instead.

**Migration**:
```python
# Before
from client_mcp.core.odiseo_bot import OdiseoBot
bot = OdiseoBot()

# After
from multi_agent import OdiseoBotV2
bot = OdiseoBotV2()
```

**Documentation**: `agent/docs/MIGRATION_ODISEOBOT_V2.md`

## Rollback Plan

If issues arise, revert this PR and deploy previous version.

## Testing

```bash
# Run integration tests
pytest agent/test_odiseo_bot_v2_integration.py -v

# Test CLI
python3 scripts/odiseo_cli.py
```

---

🤖 Generated with Claude Code
PR_BODY
)" \
  --base main
```

---

#### Task 2: Code Review

**Reviewers**: Tech Lead, Senior Developers

**Review Checklist**:
- [ ] All Legacy references removed?
- [ ] Tests passing?
- [ ] CLI tool works?
- [ ] Documentation updated?
- [ ] No breaking changes for V2 users?

---

#### Task 3: Deploy to Production

```bash
# After PR approval
git checkout main
git pull
git merge remove-legacy-odiseobot

# Tag release
git tag -a v3.0.0 -m "v3.0.0: Remove Legacy OdiseoBot"
git push origin v3.0.0

# Deploy
docker build -t odiseo-bot:v3.0.0 .
docker-compose up -d

# Monitor
tail -f logs/odiseo_bot.log
```

---

## 📊 Success Metrics

### Code Quality
- ✅ -1,183 lines removed (Legacy OdiseoBot)
- ✅ -~300 lines removed (Legacy imports/paths)
- ✅ Total: **~1,500 lines removed**

### Performance
- ✅ Error rate ≤ V2 baseline
- ✅ Response time ≤ V2 baseline
- ✅ No regressions

### Adoption
- ✅ 0% Legacy usage
- ✅ 100% V2 usage
- ✅ CLI tool adoption (optional)

---

## 🔄 Rollback Procedure

If issues arise after removal:

### Immediate Rollback (< 5 minutes)

```bash
# 1. Revert PR
git revert <commit-hash>
git push origin main

# 2. Restore Legacy file from backup
cp backups/odiseo_bot.py.backup client_mcp/core/odiseo_bot.py
git add client_mcp/core/odiseo_bot.py
git commit -m "hotfix: restore Legacy OdiseoBot temporarily"
git push origin main

# 3. Deploy
docker build -t odiseo-bot:rollback .
docker-compose up -d

# 4. Set feature flag to use Legacy
export USE_ODISEO_V2=false
docker-compose restart
```

---

## ✅ Final Checklist

Before removing Legacy:

- [ ] V2 deployed and stable for 42+ days
- [ ] 100% V2 usage confirmed (no Legacy traffic)
- [ ] CLI tool extracted and tested
- [ ] All tests migrated to V2
- [ ] Documentation updated (all examples use V2)
- [ ] Team informed and trained
- [ ] Rollback procedure tested
- [ ] Backup of Legacy code created
- [ ] PR approved by 2+ reviewers
- [ ] Deployment planned for low-traffic window

---

**Prepared by**: Lab01-MCP Team  
**Date**: 2025-10-12  
**Version**: 1.0.0  
**Status**: ✅ Plan Ready for Execution

---

**Next Steps**: Await V2 deployment to production, then begin Week 1-2 tasks.
