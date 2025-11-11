# Service Standardization Guidelines

**Date**: 2025-11-03
**Version**: 1.0
**Status**: ACTIVE

This document defines the standardization patterns applied across all MCP-Server services and should be followed for all future development.

---

## 1. File Structure Standards

### Test Directory Organization

```
service_name/
├── tests/                      # All tests in /tests/ (PLURAL)
│   ├── __init__.py            # Package marker
│   ├── conftest.py            # Pytest fixtures and configuration
│   ├── unit/                  # Unit tests
│   │   ├── __init__.py
│   │   ├── test_*.py
│   │   └── ...
│   ├── integration/           # Integration tests
│   │   ├── __init__.py
│   │   ├── test_*.py
│   │   └── ...
│   └── e2e/                   # End-to-end tests (optional)
│       ├── __init__.py
│       ├── test_*.py
│       └── ...
├── src/                       # Source code (if applicable)
├── docs/                      # Documentation
├── logs/                      # Log directory (created at runtime)
├── pyproject.toml
├── README.md
└── requirements.txt
```

### Test File Naming

- Use `test_*.py` or `*_test.py` prefix/suffix
- Examples: `test_auth.py`, `test_rate_limiter.py`, `email_test.py`
- Pytest discovers these automatically

---

## 2. Exception Handling Standards

### Exception Hierarchy Pattern

All services must have a domain-specific exception hierarchy following this pattern:

```python
# In service_name/exceptions.py

from typing import Any, Optional

class ServiceError(Exception):
    """Base exception for service-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.context = context or {}

    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} (context: {context_str})"
        return base

class SpecificError(ServiceError):
    """Error for specific failure mode."""

    def __init__(
        self,
        message: str,
        error_code: str = "SPECIFIC_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code, context)
```

### Domain-Specific Exceptions

Define exceptions for each domain area:

**agent/** - Framework and agent operations
- AgentError (base)
  - ConfigurationError
  - PromptError
  - ConnectionError
  - InitializationError
  - GenerationError
  - ValidationError

**client_mcp/** - Client operations
- ClientError (base)
  - ConnectionError
  - TimeoutError
  - ConfigError
  - StrategyError
  - ValidationError
  - ToolError
  - ServerError

**demo_agent/** - Demo service
- DemoAgentError (base)
  - AuthenticationError
  - RateLimitError
  - QuotaExceededError
  - CaptchaError
  - ValidationError

### Export in __init__.py

```python
# In service_name/__init__.py

from service_name.exceptions import (
    ServiceError,
    SpecificError,
    # ... other exceptions
)

__all__ = [
    "ServiceError",
    "SpecificError",
    # ... other exports
]
```

---

## 3. Logging Standards

### Factory-Based Logging Pattern

All services use the email_service factory pattern:

```python
# In service_name/logging_config.py

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

_ROOT_LOGGER: Optional[logging.Logger] = None
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_FORMAT_DETAILED = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_LOG_FORMAT_SIMPLE = "%(asctime)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    file_level: str = "DEBUG",
    console_level: str = "INFO",
    enable_file: bool = True,
) -> None:
    """Configure root logger with file and console handlers."""
    global _ROOT_LOGGER, _LOG_DIR

    # Implementation follows email_service pattern...
    # Creates service_name.log and service_name.error.log

def get_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance for a module."""
    logger = logging.getLogger(name)

    if log_level:
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if name.startswith("service_name"):
        logger.propagate = True

    return logger

def get_logs_directory() -> Path:
    """Get the logs directory path."""
    return _LOG_DIR
```

### Logger Usage in Modules

```python
# In service_name/module.py

from service_name.logging_config import get_logger

logger = get_logger(__name__)

def my_function():
    logger.info("Starting operation")
    logger.debug("Debug information")
    logger.error("Error occurred", exc_info=True)
```

### Dual Log Files

Each service creates two log files in `service_name/logs/`:
1. `service_name.log` - All logs (DEBUG+)
2. `service_name.error.log` - Errors only (ERROR+)

Both use rotation: 10MB main file, 5MB error file, 5 backups each.

---

## 4. Configuration Standards

### Pydantic v2 Settings

All services use Pydantic v2 with BaseSettings:

```python
# In service_name/config/settings.py

from pydantic_settings import BaseSettings
from pydantic import Field

class ServiceSettings(BaseSettings):
    """Service configuration from environment variables."""

    # Database
    DATABASE_URL: str = Field(default="postgresql://...")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_TO_FILE: bool = Field(default=True)
    LOG_DIR: str = Field(default="logs")

    class Config:
        env_file = None  # Let Docker/dotenv handle loading
        case_sensitive = True
        extra = "ignore"

settings = ServiceSettings()
```

### Environment Variable Loading

- **Docker**: Use `docker-compose.yml` with `env_file:` directive
- **Local Dev**: Use `python-dotenv` to load `.env` file
- **Pydantic**: Always uses `os.environ` (not file-based in BaseSettings)

---

## 5. Code Organization Standards

### Module Naming Conventions

```
service_name/
├── config/              # Configuration modules
│   ├── __init__.py
│   ├── settings.py      # Main settings class
│   └── ...
├── core/                # Core functionality
│   ├── __init__.py
│   ├── handler.py
│   └── ...
├── utils/               # Utility functions
│   ├── __init__.py
│   ├── helpers.py
│   ├── logger.py        # For backward compatibility
│   └── ...
├── exceptions.py        # Exception hierarchy (service root)
├── logging_config.py    # Logging factory (service root)
└── ...
```

### Import Organization

```python
# Standard library imports
import logging
from pathlib import Path
from typing import Optional

# Third-party imports
from pydantic import Field

# Local imports
from service_name.config import settings
from service_name.logging_config import get_logger
from service_name.exceptions import ServiceError
```

---

## 6. Development Best Practices

### Before Creating New Module

1. Check if exception class exists in `exceptions.py`
2. Use factory `get_logger(__name__)` in each module
3. Follow existing code style and patterns
4. Add comprehensive docstrings to public functions
5. Use type hints throughout

### Adding New Exceptions

1. Add to `service_name/exceptions.py` following the pattern
2. Update service `__init__.py` to export it
3. Document the error_code and context fields
4. Add usage examples in docstring

### Adding New Logging

1. Import: `from service_name.logging_config import get_logger`
2. Create logger: `logger = get_logger(__name__)`
3. Use structured logging with context when appropriate
4. Never hardcode log levels in modules

### Adding Tests

1. Create in `service_name/tests/unit/` or `.../integration/`
2. Use `test_*.py` naming convention
3. Use conftest.py for shared fixtures
4. Mock external dependencies
5. Test both success and failure paths

---

## 7. Quality Checklist for New Services

Before deploying a new service, ensure:

- [ ] Exception hierarchy in `exceptions.py` (not other modules)
- [ ] Exceptions exported in `__init__.py`
- [ ] Logging config in `logging_config.py` (factory pattern)
- [ ] All modules use `get_logger(__name__)`
- [ ] Tests directory is `/tests/` (plural)
- [ ] Test files follow `test_*.py` pattern
- [ ] conftest.py exists with fixtures
- [ ] No hardcoded log levels in code
- [ ] Pydantic v2 for all configurations
- [ ] No malware or suspicious imports
- [ ] Type hints on all public functions
- [ ] Docstrings on all classes and public functions
- [ ] .env file is not committed (in .gitignore)
- [ ] environment.yml or requirements.txt is up to date
- [ ] README.md documents setup and usage

---

## 8. Troubleshooting Guide

### Issue: Tests not found in tests/ directory

```bash
# Check pytest configuration
cat pyproject.toml | grep testpaths
# or
cat pytest.ini

# Should point to tests/ directory
# If using relative paths, they must be relative to project root
```

### Issue: Exceptions not importing

```python
# Verify __init__.py has exports
cat service_name/__init__.py | grep -A 10 "from.*exceptions"

# Verify exceptions.py exists
ls -la service_name/exceptions.py
```

### Issue: Logging to wrong location

```python
# Check where logs are created
from service_name.logging_config import get_logs_directory
print(get_logs_directory())

# Should show service_name/logs/
```

### Issue: Old logger still being used

```python
# Replace
from service_name.utils.logger import setup_logging

# With
from service_name.logging_config import setup_logging, get_logger
```

---

## 9. Migration Path from Old Patterns

### Old Pattern
```python
# Old: Direct logging.getLogger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
```

### New Pattern
```python
# New: Factory-based
from service_name.logging_config import get_logger
logger = get_logger(__name__)
```

### Old Pattern
```python
# Old: Generic exceptions
raise Exception("Something failed")
```

### New Pattern
```python
# New: Domain-specific
from service_name.exceptions import SpecificError
raise SpecificError(
    message="Something failed",
    error_code="SPECIFIC_001",
    context={"operation": "my_operation", "retry_count": 3}
)
```

---

## References

- **Factory-based Logging**: `email_service/core/logger.py` (reference implementation)
- **Domain Exceptions**: `agent/src/gemini_agent/exceptions.py` (reference implementation)
- **Complete Guide**: `docs/SERVICE_STANDARDIZATION_COMPLETED.md`

---

**Last Updated**: 2025-11-03
**Author**: Claude Code (MCP-Server Standardization)
**Status**: ACTIVE - Follow these guidelines for all new services
