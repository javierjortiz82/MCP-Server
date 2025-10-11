# Makefile for Odiseo Bot (SmartBot MCP Client)
# Python version: 3.10+

.PHONY: help clean test lint format install install-dev run health metrics

# Default target
help:
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  Odiseo Bot - SmartBot MCP Client (v2.1.0)"
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Available targets:"
	@echo "  help         - Show this help message"
	@echo "  clean        - Remove cache files and build artifacts"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  lint         - Run code quality checks (ruff, mypy)"
	@echo "  format       - Format code with ruff"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-int     - Run integration tests only"
	@echo "  test-cov     - Run tests with coverage report"
	@echo "  run          - Run the bot interactively"
	@echo "  health       - Check MCP server health"
	@echo "  metrics      - Export execution metrics"
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════════"

# Clean cache and build artifacts
clean:
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*~" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ Clean complete!"

# Install production dependencies
install:
	@echo "📦 Installing production dependencies..."
	@pip install -r requirements.txt
	@echo "✅ Installation complete!"

# Install development dependencies
install-dev: install
	@echo "🔧 Installing development dependencies..."
	@pip install -r requirements-dev.txt
	@echo "✅ Development environment ready!"

# Run linting (ruff + mypy)
lint:
	@echo "🔍 Running code quality checks..."
	@echo "  → Ruff (linter)..."
	@ruff check .
	@echo "  → Mypy (type checker)..."
	@mypy core/ utils/ monitoring/ strategies/ observability/ --ignore-missing-imports
	@echo "✅ Lint checks passed!"

# Format code with ruff
format:
	@echo "✨ Formatting code with ruff..."
	@ruff format .
	@ruff check --fix .
	@echo "✅ Code formatted!"

# Run all tests
test:
	@echo "🧪 Running all tests..."
	@pytest test/ -v
	@echo "✅ All tests passed!"

# Run unit tests only
test-unit:
	@echo "🧪 Running unit tests..."
	@pytest test/unit/ -v
	@echo "✅ Unit tests passed!"

# Run integration tests only
test-int:
	@echo "🧪 Running integration tests..."
	@pytest test/integration/ -v
	@echo "✅ Integration tests passed!"

# Run tests with coverage
test-cov:
	@echo "📊 Running tests with coverage..."
	@pytest test/ --cov=. --cov-report=term-missing --cov-report=html -q
	@echo "✅ Coverage report generated in htmlcov/"

# Run the bot interactively
run:
	@echo "🚀 Starting Odiseo Bot..."
	@python cli/main.py

# Check MCP server health
health:
	@echo "🏥 Checking MCP server health..."
	@curl -s http://localhost:8009/health | python -m json.tool || echo "❌ MCP server unreachable"

# Export execution metrics
metrics:
	@echo "📊 Exporting execution metrics..."
	@test -f data/execution_metrics.json && cat data/execution_metrics.json | python -m json.tool || echo "⚠️  No metrics file found"
