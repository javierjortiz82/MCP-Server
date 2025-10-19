# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-10-18

### Added
- Complete refactoring with modular architecture
- Custom exception hierarchy (5 exception types)
- Centralized logging system with `get_logger()` factory
- Pydantic v2 compliance with proper model configuration
- Separated models into specialized modules
- Type hints throughout (mypy compliant)
- Google-style docstrings on all classes and methods
- `.env.example` with all configuration options
- `scripts/validate_env.py` for configuration validation
- `pyproject.toml` for modern package distribution
- Comprehensive README.md with Mermaid architecture diagrams
- Support for Django, FastAPI, and direct Python usage

### Changed
- Migrated from flat structure to modular packages
- Updated SMTP client with transient error detection
- Improved queue manager with better error handling
- Enhanced worker with cleaner separation of concerns
- Standardized configuration validation

### Fixed
- Type checking issues resolved (mypy compliant)
- Unused imports removed (ruff compliant)
- Code formatting standardized (black compliant)
- Import ordering organized (isort compliant)
- Long lines shortened (PEP 8 compliant)

### Removed
- Deprecated v1 module structure
- Redundant code duplication

## [1.0.0] - 2025-10-14

### Initial Release
- Basic email queue system with PostgreSQL
- SMTP client wrapper
- Jinja2 template rendering
- Email worker daemon
- Simple configuration system
- Retry logic with backoff
