# Makefile for Gemini Agent (AI Service Provider)
# Python version: 3.11+

.PHONY: help clean test lint format install install-dev run run-dev run-prod health docs check

# Default target
help:
	@echo "═══════════════════════════════════════════════════════════════════"
	@echo "  Gemini Agent - AI Service Provider (v1.0.0)"
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
	@echo "  test-cov     - Run tests with coverage report"
	@echo "  check        - Run all quality checks (lint + test)"
	@echo "  run          - Run the agent service (development mode)"
	@echo "  run-dev      - Run with auto-reload (development)"
	@echo "  run-prod     - Run in production mode (4 workers)"
	@echo "  health       - Check service health endpoints"
	@echo "  docs         - Open API documentation in browser"
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
	@ruff check src tests
	@echo "  → Mypy (type checker)..."
	@mypy src tests --ignore-missing-imports
	@echo "✅ Lint checks passed!"

# Format code with ruff
format:
	@echo "✨ Formatting code with ruff..."
	@ruff format src tests
	@ruff check --fix src tests
	@echo "✅ Code formatted!"

# Run all tests
test:
	@echo "🧪 Running all tests..."
	@pytest -v
	@echo "✅ All tests passed!"

# Run tests with coverage
test-cov:
	@echo "📊 Running tests with coverage..."
	@pytest --cov=src --cov-report=term-missing --cov-report=html -q
	@echo "✅ Coverage report generated in htmlcov/"

# Run all quality checks
check: lint test
	@echo "✅ All quality checks passed!"

# Run the agent service (development mode)
run:
	@echo "🚀 Starting Gemini Agent (development mode)..."
	@uvicorn gemini_agent.server:app --host 0.0.0.0 --port 8000

# Run with auto-reload (development)
run-dev:
	@echo "🚀 Starting Gemini Agent with auto-reload..."
	@uvicorn gemini_agent.server:app --reload --host 0.0.0.0 --port 8000

# Run in production mode (multiple workers)
run-prod:
	@echo "🚀 Starting Gemini Agent (production mode - 4 workers)..."
	@uvicorn gemini_agent.server:app --host 0.0.0.0 --port 8000 --workers 4

# Check service health
health:
	@echo "🏥 Checking Gemini Agent health..."
	@echo ""
	@echo "=== Comprehensive Health Check ==="
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Service unreachable"
	@echo ""
	@echo "=== Liveness Probe ==="
	@curl -s http://localhost:8000/health/live | python -m json.tool || echo "❌ Service not alive"
	@echo ""
	@echo "=== Readiness Probe ==="
	@curl -s http://localhost:8000/health/ready | python -m json.tool || echo "❌ Service not ready"

# Open API documentation
docs:
	@echo "📚 Opening API documentation..."
	@echo "  → Swagger UI: http://localhost:8000/docs"
	@echo "  → ReDoc: http://localhost:8000/redoc"
	@python -c "import webbrowser; webbrowser.open('http://localhost:8000/docs')" 2>/dev/null || echo "Please open http://localhost:8000/docs in your browser"
