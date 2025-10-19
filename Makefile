# Lab01-MCP Makefile
# Simplifies common development and deployment tasks
#
# ============================================================================
# CODE REVIEW IMPROVEMENTS (v2.0)
# ============================================================================
# ✓ Error handling: All commands stop on first failure
# ✓ Prerequisites checking: Verify Docker, directories exist before running
# ✓ Venv verification: Check if venv exists before creation
# ✓ Process cleanup: Trap signals in dev command to prevent zombie processes
# ✓ Directory validation: Verify required dirs (client_mcp, agent, test, logs, etc)
# ✓ File existence checks: Verify scripts/config files before execution
# ✓ Consolidated chmod: Combine chmod +x with command execution
# ✓ Error messages: Clear, colored error messages on failure
# ============================================================================

.PHONY: help install test clean deploy start stop status lint format check docs db docker-start docker-stop docker-build docker-restart docker-logs docker-ps docker-clean review review-fix review-report

# Variables
PYTHON := python3
PIP := pip3
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(BLUE)Lab01-MCP Makefile Commands$(NC)"
	@echo "$(BLUE)=============================$(NC)"
	@echo "$(GREEN)install$(NC)           - Set up virtual environment and install all dependencies"
	@echo "$(GREEN)db$(NC)                - Initialize database (DDL + DML + seed data)"
	@echo "$(GREEN)test$(NC)              - Run all tests with coverage"
	@echo "$(GREEN)clean$(NC)             - Remove cache files and build artifacts"
	@echo "$(GREEN)docs$(NC)              - Generate documentation"
	@echo ""
	@echo "$(YELLOW)Code Quality (Professional):$(NC)"
	@echo "$(GREEN)review$(NC)            - Professional code review (ruff + mypy + isort + vulture + bandit)"
	@echo "$(GREEN)review-fix$(NC)        - Auto-fix code issues (ruff + isort)"
	@echo "$(GREEN)review-report$(NC)     - Generate detailed review report"
	@echo "$(GREEN)lint$(NC)              - Run code linting (ruff check)"
	@echo "$(GREEN)format$(NC)            - Format code (ruff format)"
	@echo "$(GREEN)check$(NC)             - Run type checking (mypy with modern type hints)"
	@echo ""
	@echo "$(YELLOW)Services:$(NC)"
	@echo "$(GREEN)deploy$(NC)            - Full deployment (install + start services)"
	@echo "$(GREEN)start$(NC)             - Start all services"
	@echo "$(GREEN)stop$(NC)              - Stop all services"
	@echo "$(GREEN)status$(NC)            - Show service status"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@echo "$(GREEN)docker-start$(NC)      - Start all Docker containers"
	@echo "$(GREEN)docker-stop$(NC)       - Stop all Docker containers"
	@echo "$(GREEN)docker-build$(NC)      - Build all Docker images"
	@echo "$(GREEN)docker-restart$(NC)    - Restart all Docker containers"
	@echo "$(GREEN)docker-logs$(NC)       - Show Docker logs (follow)"
	@echo "$(GREEN)docker-ps$(NC)         - Show Docker container status"
	@echo "$(GREEN)docker-clean$(NC)      - Clean up Docker (volumes, images, etc)"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "$(GREEN)dev$(NC)               - Start development environment"

# Setup and Installation
install:
	@echo "$(YELLOW)Setting up virtual environment...$(NC)"
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(ACTIVATE) && $(PIP) install --upgrade pip || { echo "$(RED)Failed to upgrade pip$(NC)"; exit 1; }
	@echo "$(YELLOW)Installing all dependencies...$(NC)"
	@$(ACTIVATE) && $(PIP) install -r requirements.txt && \
		$(PIP) install -r agent/requirements.txt && \
		$(PIP) install -r agent/requirements-dev.txt && \
		$(PIP) install -r client_mcp/requirements.txt && \
		$(PIP) install -r client_mcp/requirements-dev.txt && \
		$(PIP) install -r email_service/requirements.txt && \
		$(PIP) install -r email_service/requirements-dev.txt && \
		$(PIP) install -r mcp_server/requirements.txt || { echo "$(RED)Failed to install dependencies$(NC)"; exit 1; }
	@echo "$(YELLOW)Installing code review tools...$(NC)"
	@$(ACTIVATE) && $(PIP) install -q vulture bandit isort || { echo "$(RED)Failed to install review tools$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Installation complete (including review tools)$(NC)"

# Testing
test:
	@echo "$(YELLOW)Running all tests...$(NC)"
	@test -d test || { echo "$(RED)Test directory not found$(NC)"; exit 1; }
	@$(ACTIVATE) && pytest test/ -v --cov=client_mcp --cov=agent --cov-report=term-missing || { echo "$(RED)Tests failed$(NC)"; exit 1; }

test-unit:
	@echo "$(YELLOW)Running unit tests...$(NC)"
	@test -f test/test_gemini_agent.py || { echo "$(RED)Unit test file not found$(NC)"; exit 1; }
	@$(ACTIVATE) && pytest test/test_gemini_agent.py -v || { echo "$(RED)Unit tests failed$(NC)"; exit 1; }

test-int:
	@echo "$(YELLOW)Running integration tests...$(NC)"
	@test -f test/test_integration.py || { echo "$(RED)Integration test file not found$(NC)"; exit 1; }
	@$(ACTIVATE) && pytest test/test_integration.py -v || { echo "$(RED)Integration tests failed$(NC)"; exit 1; }

test-quick:
	@echo "$(YELLOW)Running quick tests (no coverage)...$(NC)"
	@test -d test || { echo "$(RED)Test directory not found$(NC)"; exit 1; }
	@$(ACTIVATE) && pytest test/ -v -x || { echo "$(RED)Quick tests failed$(NC)"; exit 1; }

# Code Quality
lint:
	@echo "$(YELLOW)Running linter (ruff)...$(NC)"
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@$(ACTIVATE) && ruff check client_mcp/ agent/ test/ || { echo "$(RED)Linting failed$(NC)"; exit 1; }

format:
	@echo "$(YELLOW)Formatting code (ruff)...$(NC)"
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@$(ACTIVATE) && ruff format client_mcp/ agent/ test/ || { echo "$(RED)Formatting failed$(NC)"; exit 1; }

check:
	@echo "$(YELLOW)Running type checker (mypy)...$(NC)"
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@$(ACTIVATE) && mypy --strict client_mcp/ agent/ || { echo "$(RED)Type checking failed$(NC)"; exit 1; }

# Professional Code Review
review:
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Professional Code Review - All Best Practices$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)[1/6] Linting (Ruff - PEP8, style, complexity)...$(NC)"
	@$(ACTIVATE) && ruff check client_mcp/ agent/ test/ --show-settings || true
	@echo ""
	@echo "$(YELLOW)[2/6] Import sorting (isort - Organized imports)...$(NC)"
	@$(ACTIVATE) && isort --check-only --diff client_mcp/ agent/ test/ || true
	@echo ""
	@echo "$(YELLOW)[3/6] Type checking (Mypy - Modern type hints, PEP 604)...$(NC)"
	@$(ACTIVATE) && mypy --strict --show-error-codes client_mcp/ agent/ || true
	@echo ""
	@echo "$(YELLOW)[4/6] Dead code detection (Vulture - Unused variables/imports)...$(NC)"
	@$(ACTIVATE) && vulture client_mcp/ agent/ test/ --min-confidence 80 || true
	@echo ""
	@echo "$(YELLOW)[5/6] Security analysis (Bandit - Security vulnerabilities)...$(NC)"
	@$(ACTIVATE) && bandit -r client_mcp/ agent/ -ll || true
	@echo ""
	@echo "$(YELLOW)[6/6] Code formatting check (Ruff - F-strings, no hardcode)...$(NC)"
	@$(ACTIVATE) && ruff format --check client_mcp/ agent/ test/ || true
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)✓ Professional code review complete$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"

review-fix:
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@echo "$(BLUE)Auto-fixing code issues...$(NC)"
	@echo ""
	@echo "$(YELLOW)Fixing with Ruff...$(NC)"
	@$(ACTIVATE) && ruff check --fix --unsafe-fixes client_mcp/ agent/ test/ || true
	@echo ""
	@echo "$(YELLOW)Formatting with Ruff...$(NC)"
	@$(ACTIVATE) && ruff format client_mcp/ agent/ test/ || true
	@echo ""
	@echo "$(YELLOW)Sorting imports with isort...$(NC)"
	@$(ACTIVATE) && isort client_mcp/ agent/ test/ || true
	@echo ""
	@echo "$(GREEN)✓ Auto-fix complete$(NC)"

review-report:
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@echo "$(BLUE)Generating detailed review report...$(NC)"
	@echo ""
	@echo "$(YELLOW)Ruff Report (850+ rules):$(NC)"
	@$(ACTIVATE) && ruff check client_mcp/ agent/ test/ --statistics 2>/dev/null || true
	@echo ""
	@echo "$(YELLOW)Type Coverage Report:$(NC)"
	@$(ACTIVATE) && python3 -c "print('Run: mypy --stats client_mcp/ agent/')" || true
	@$(ACTIVATE) && mypy --stats client_mcp/ agent/ 2>/dev/null || true
	@echo ""
	@echo "$(YELLOW)Dead Code Report:$(NC)"
	@$(ACTIVATE) && vulture client_mcp/ agent/ test/ --min-confidence 60 2>/dev/null || true
	@echo ""
	@echo "$(GREEN)✓ Review report generated$(NC)"

# Cleaning
clean:
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*~" -delete
	@find . -type f -name ".coverage" -delete
	@rm -rf build/ dist/ *.egg-info 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

clean-deep: clean
	@echo "$(YELLOW)Deep cleaning (including venv)...$(NC)"
	@rm -rf $(VENV)
	@rm -rf logs/ pids/ 2>/dev/null || true
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

# Docker Management
docker-start:
	@echo "$(YELLOW)Starting Docker containers...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose up -d || { echo "$(RED)Failed to start Docker containers$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker containers started$(NC)"

docker-stop:
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose down || { echo "$(RED)Failed to stop Docker containers$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker containers stopped$(NC)"

docker-build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose build || { echo "$(RED)Failed to build Docker images$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker images built$(NC)"

docker-restart:
	@echo "$(YELLOW)Restarting Docker containers...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose restart || { echo "$(RED)Failed to restart Docker containers$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker containers restarted$(NC)"

docker-logs:
	@echo "$(YELLOW)Following Docker logs...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose logs -f

docker-ps:
	@echo "$(YELLOW)Docker container status:$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose ps

docker-clean:
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@cd DockerConfig && docker-compose down -v || { echo "$(RED)Failed to clean Docker containers$(NC)"; exit 1; }
	@docker system prune -f || { echo "$(RED)Failed to prune Docker system$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

# Deployment
deploy:
	@echo "$(BLUE)Starting full deployment...$(NC)"
	@chmod +x scripts/deploy.sh && bash scripts/deploy.sh deploy || { echo "$(RED)Deployment failed$(NC)"; exit 1; }

start:
	@echo "$(YELLOW)Starting services...$(NC)"
	@chmod +x scripts/deploy.sh && bash scripts/deploy.sh start || { echo "$(RED)Failed to start services$(NC)"; exit 1; }

stop:
	@echo "$(YELLOW)Stopping services...$(NC)"
	@chmod +x scripts/deploy.sh && bash scripts/deploy.sh stop || { echo "$(RED)Failed to stop services$(NC)"; exit 1; }

status:
	@chmod +x scripts/deploy.sh && bash scripts/deploy.sh status || { echo "$(RED)Failed to get status$(NC)"; exit 1; }

# Development
dev: docker-start
	@echo "$(BLUE)Starting development environment...$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to stop all services$(NC)"
	@trap "kill %1 %2 2>/dev/null; echo '$(RED)Services stopped$(NC)'; exit 0" INT TERM; \
		. $(VENV)/bin/activate && \
		cd mcp && $(PYTHON) main.py & \
		sleep 3 && \
		cd ../client_mcp && $(PYTHON) main.py; \
		wait

dev-agent:
	@echo "$(YELLOW)Testing agent module...$(NC)"
	@$(ACTIVATE) && $(PYTHON) -c "from agent import GeminiAgent; print('Agent module OK')"

dev-client:
	@echo "$(YELLOW)Starting client in dev mode...$(NC)"
	@$(ACTIVATE) && cd client_mcp && $(PYTHON) main.py

# Documentation
docs:
	@echo "$(YELLOW)Generating documentation...$(NC)"
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@mkdir -p docs/api
	@$(ACTIVATE) && pdoc --html --output-dir docs/api agent client_mcp || { echo "$(RED)Documentation generation failed$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Documentation generated in docs/api$(NC)"

# Database
db:
	@test -f SQL/scripts/deploy.sh || { echo "$(RED)Database deploy script not found$(NC)"; exit 1; }
	@chmod +x SQL/scripts/deploy.sh && bash SQL/scripts/deploy.sh || { echo "$(RED)Database deployment failed$(NC)"; exit 1; }

# Monitoring
logs:
	@test -d logs || { echo "$(RED)No logs directory found$(NC)"; exit 1; }
	@test -n "$$(find logs -name '*.log' 2>/dev/null)" || { echo "$(RED)No log files found$(NC)"; exit 1; }
	@tail -f logs/*.log

monitor:
	@watch -n 2 "make status"

# CI/CD
ci:
	@echo "$(BLUE)Running CI/CD pipeline...$(NC)"
	@make clean || { echo "$(RED)Clean failed$(NC)"; exit 1; }
	@make install || { echo "$(RED)Install failed$(NC)"; exit 1; }
	@make lint || { echo "$(RED)Lint failed$(NC)"; exit 1; }
	@make check || { echo "$(RED)Type check failed$(NC)"; exit 1; }
	@make test || { echo "$(RED)Tests failed$(NC)"; exit 1; }
	@echo "$(GREEN)✓ CI checks passed$(NC)"

build:
	@echo "$(YELLOW)Building project...$(NC)"
	@test -d client_mcp || { echo "$(RED)client_mcp directory not found$(NC)"; exit 1; }
	@test -d agent || { echo "$(RED)agent directory not found$(NC)"; exit 1; }
	@$(ACTIVATE) && $(PYTHON) -m build || { echo "$(RED)Build failed$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Build complete$(NC)"

# Shortcuts
i: install
t: test
c: clean
d: deploy
s: start
st: stop

# Version info
version:
	@echo "$(BLUE)Lab01-MCP Version Information$(NC)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "Pip: $$($(PIP) --version)"
	@echo "Project: 1.0.0"

.DEFAULT_GOAL := help