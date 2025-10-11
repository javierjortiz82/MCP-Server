# Client MCP Test Suite

Comprehensive test suite for the Odiseo Bot (Client MCP) project.

## Structure

```
test/
├── conftest.py                        # Shared pytest fixtures
├── unit/                              # Unit tests
│   ├── test_error_handler.py         # Error handling utilities
│   ├── test_rate_limiter.py          # Rate limiting (requires aiolimiter)
│   ├── test_thinking_manager.py      # Gemini 2.5 Thinking Mode
│   ├── test_settings.py              # Configuration management
│   ├── test_tool_validator.py        # Tool parameter validation
│   └── test_tool_executor.py         # Tool execution orchestrator
└── integration/                       # Integration tests
    └── test_bot_initialization.py    # Bot initialization flow
```

## Running Tests

### Run All Tests

```bash
cd /home/javort/Lab01-MCP/client_mcp
python -m pytest test/ -v
```

### Run Specific Test File

```bash
python -m pytest test/unit/test_thinking_manager.py -v
```

### Run with Coverage

```bash
python -m pytest test/ --cov=. --cov-report=html --cov-report=term
```

### Run Only Unit Tests

```bash
python -m pytest test/unit/ -v
```

### Run Only Integration Tests

```bash
python -m pytest test/integration/ -v
```

## Test Coverage

Current test coverage by module:

| Module | Tests | Coverage | Notes |
|--------|-------|----------|-------|
| `core/thinking_manager.py` | 15 | ~95% | Complete |
| `core/rate_limiter.py` | 13 | ~90% | Requires aiolimiter |
| `utils/error_handler.py` | 22 | ~100% | Complete |
| `config/settings.py` | 18 | ~85% | Complete |
| `core/tool_validator.py` | 34 | ~95% | Complete |
| `core/tool_executor.py` | 25 | ~80% | Core functionality |
| `core/odiseo_bot.py` | 12 | ~40% | Integration tests |

**Total**: ~120 test cases

## Test Requirements

### Required Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov
```

### Optional Dependencies

- `aiolimiter>=1.1.0` - Required for rate limiter tests
- `pydantic>=2.0` - Required for validator tests

## Fixtures

The `conftest.py` file provides shared fixtures:

- **mock_settings**: Mock Settings instance with test values
- **mock_gemini_client**: Mock Google Gemini API client
- **mock_mcp_connector**: Mock MCP connector
- **sample_mcp_tools**: Sample tool definitions (search_products, fetch_by_sku)
- **sample_gemini_response**: Mock Gemini API response
- **sample_product**: Single product data
- **sample_products**: List of products

## Writing New Tests

### Unit Test Template

```python
"""Unit tests for MyModule."""

import pytest

from my.module import MyClass


class TestMyClass:
    """Test suite for MyClass."""

    def test_initialization(self):
        """Test MyClass initialization."""
        instance = MyClass()
        assert instance is not None

    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method."""
        instance = MyClass()
        result = await instance.async_method()
        assert result == expected
```

### Integration Test Template

```python
"""Integration tests for MyFeature."""

import pytest
from unittest.mock import AsyncMock, patch


class TestMyFeatureIntegration:
    """Integration tests for MyFeature flow."""

    @pytest.mark.asyncio
    async def test_complete_flow(self, mock_settings):
        """Test complete feature flow."""
        # Setup
        # Execute
        # Verify
```

## Test Markers

Tests use the following pytest markers:

- `@pytest.mark.asyncio` - Async tests requiring event loop
- `@pytest.mark.slow` - Slow tests (>1s)
- `@pytest.mark.integration` - Integration tests

## Skipping Tests

Tests can be skipped conditionally:

```python
pytest.importorskip("aiolimiter", reason="aiolimiter not installed")
```

## CI/CD Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    pip install pytest pytest-asyncio pytest-cov
    pytest test/ --cov=. --cov-report=xml
```

## Troubleshooting

### Issue: aiolimiter not found

**Solution**: Install aiolimiter or skip those tests:

```bash
pip install aiolimiter>=1.1.0
# OR
pytest test/ -k "not rate_limiter"
```

### Issue: Import errors

**Solution**: Ensure you're running from project root:

```bash
cd /home/javort/Lab01-MCP/client_mcp
python -m pytest test/
```

### Issue: Fixtures not found

**Solution**: Check `conftest.py` is present and pytest can find it:

```bash
pytest --fixtures test/
```

## Best Practices

1. **One test per behavior** - Each test should verify one specific behavior
2. **Descriptive names** - Use clear, descriptive test names
3. **AAA pattern** - Arrange, Act, Assert structure
4. **Mock external dependencies** - Isolate units under test
5. **Use fixtures** - Leverage conftest.py for shared setup
6. **Test edge cases** - Include error conditions and boundary cases
7. **Keep tests fast** - Unit tests should run in milliseconds

## Future Improvements

- [ ] Add performance/benchmark tests
- [ ] Add mutation testing
- [ ] Increase integration test coverage
- [ ] Add property-based tests (hypothesis)
- [ ] Add API contract tests
- [ ] Add load/stress tests for rate limiter

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure >80% coverage for new code
3. Run full test suite before committing
4. Update this README if adding new test categories
