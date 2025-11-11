# Testing Quick Reference Guide

## 30-Second Summary

| Service | Status | Command | Coverage |
|---------|--------|---------|----------|
| agent | ✅ Ready | `pytest agent/tests/ -v` | ~70-80% |
| client_mcp | ✅ Ready | `pytest client_mcp/tests/ -v` | 64% |
| demo_agent | ✅ Ready | `pytest demo_agent/tests/ -v` | ~85% |
| email_service | ⚠️ Needs tests | N/A | 0% |
| mcp_server | ⚠️ Minimal | `pytest mcp_server/tests/ -v` | ~15% |

## Run All Tests

```bash
make test
```

## Run Per-Service Tests

```bash
# Agent (13 files, 74 tests)
pytest agent/tests/ -v --cov=agent

# Client MCP (17 files, 557 tests) - Most comprehensive
pytest client_mcp/tests/ -v --cov=. --cov-report=html

# Demo Agent (11 files, 131 tests)
pytest demo_agent/tests/ -v --cov=demo_agent

# MCP Server (2 files, 8 tests)
pytest mcp_server/tests/ -v

# Email Service - No tests yet
# (create tests in email_service/tests/)
```

## Key Test Files

### Agent
- `agent/tests/test_agent.py` - Core agent functionality
- `agent/tests/test_booking_modular_prompts.py` - Booking logic
- `agent/tests/test_metrics.py` - Metrics tracking

### Client MCP (Most Complete)
- `client_mcp/tests/unit/test_thinking_manager.py` - Gemini 2.5 thinking
- `client_mcp/tests/unit/test_tool_validator.py` - Parameter validation
- `client_mcp/tests/unit/test_rate_limiter.py` - Rate limiting
- `client_mcp/tests/unit/test_tool_executor.py` - Tool execution

### Demo Agent
- `demo_agent/tests/test_recaptcha_unit.py` - reCAPTCHA unit tests
- `demo_agent/tests/test_recaptcha_e2e.py` - reCAPTCHA E2E
- `demo_agent/tests/test_fingerprint.py` - Client fingerprinting
- `demo_agent/tests/test_http_recaptcha_e2e.sh` - HTTP E2E tests

### MCP Server
- `mcp_server/tests/test_product_handler_i18n.py` - i18n validation

## Test Coverage

### Highest Coverage
- **client_mcp**: 64% (1,846/2,869 lines)
  - error_handler: 100%
  - tool_validator: 95%
  - thinking_manager: 95%
  - rate_limiter: 90%

### Medium Coverage
- **agent**: ~70-80%
- **demo_agent**: ~85%

### Needs Improvement
- **mcp_server**: ~15%
- **email_service**: 0%

## Full CI Pipeline

```bash
make ci                    # Runs: clean → install → lint → check → test
```

## Code Quality Tools

```bash
make lint                  # Run ruff linter
make check                 # Run mypy type checker
make format                # Auto-format code
make review                # Full review (ruff + mypy + vulture + bandit)
make review-fix            # Auto-fix issues
```

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Test Files | 43 |
| Total Test Functions | 770+ |
| Most Comprehensive | client_mcp (557 tests) |
| Execution Time | ~8-15 seconds |
| Pass Rate | 100% (all passing) |
| Framework | pytest 7.0+ |

## Testing Dependencies

```bash
# Already in requirements.txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
pytest-mock>=3.12.0

# Optional review tools
ruff mypy vulture bandit isort black
```

## Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Markers

```bash
pytest agent/tests/ -m "not slow"      # Skip slow tests
pytest demo_agent/tests/ -m "integration"  # Run integration tests
```

## Docker-Based Testing

```bash
# Start services
make docker-start
make db                    # Initialize database

# Run service-based tests
bash demo_agent/tests/test_http_recaptcha_e2e.sh
bash mcp_server/tests/test_mcp_endpoints.sh

# Stop services
make docker-stop
```

## Troubleshooting

### Tests not found
```bash
cd /home/javort/alfredo/MCP-Server
pytest --collect-only  # List all tests
```

### Import errors
```bash
# Ensure in project root
cd /home/javort/alfredo/MCP-Server
python -m pytest agent/tests/
```

### Database connection errors
```bash
# For integration tests, start Docker first
make docker-start
make db
```

### Coverage reports missing
```bash
# Install coverage if needed
pip install pytest-cov coverage[toml]
pytest --cov=. --cov-report=html
```

## Priority Actions

1. **Immediate**: `make test` to verify all tests pass
2. **Soon**: Expand mcp_server tests to 70%+ coverage
3. **Medium-term**: Create email_service test suite
4. **Long-term**: Set up GitHub Actions CI/CD

## Useful Links

- Full Report: `docs/TESTING_INFRASTRUCTURE_REPORT.md`
- Client MCP Details: `client_mcp/tests/README.md`
- Demo Agent Details: `demo_agent/tests/README_TESTS.md`
- Latest Results: `client_mcp/tests/TEST_RESULTS.md`

---

**Generated**: November 3, 2025
**Status**: Ready to use
