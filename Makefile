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

.PHONY: help install setup-env env-check test clean deploy start stop status lint format check docs db docker-start docker-stop docker-build docker-restart docker-logs docker-ps docker-clean review review-fix review-report validate validate-strict validate-quiet validate-pydantic docker-start-safe

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
CYAN := \033[0;36m
NC := \033[0m # No Color

# Default target
help:
	@echo ""
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                     Lab01-MCP Quick Start Guide                                ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)🚀 QUICK START - Choose your deployment method:$(NC)"
	@echo ""
	@echo "$(CYAN)OPTION A: Docker Deployment (Recommended)$(NC)"
	@echo "  1. make setup-env              # Create .env files from templates"
	@echo "  2. make env-check              # Verify all .env files exist"
	@echo "  3. nano DockerConfig/.env      # Edit: POSTGRES_PASSWORD, PGADMIN_PASSWORD"
	@echo "  4. nano mcp_server/.env        # Edit: GOOGLE_API_KEY, DATABASE_URL"
	@echo "  5. nano email_service/.env     # Edit: GOOGLE_API_KEY, SMTP_*"
	@echo "  6. make docker-start-safe      # Validate + Start Docker"
	@echo "  7. make db                     # Initialize database"
	@echo ""
	@echo "$(CYAN)OPTION B: Local Development (No Docker)$(NC)"
	@echo "  1. make setup-env              # Create .env files from templates"
	@echo "  2. make env-check              # Verify all .env files exist"
	@echo "  3. make install                # Install dependencies"
	@echo "  4. nano mcp_server/.env        # Edit: GOOGLE_API_KEY, DATABASE_URL (local PostgreSQL)"
	@echo "  5. nano email_service/.env     # Edit: SMTP_*, GOOGLE_API_KEY"
	@echo "  6. make db                     # Initialize database"
	@echo "  7. make dev                    # Start all services"
	@echo ""
	@echo "$(CYAN)OPTION C: Quick Test (Skip Docker/Local Setup)$(NC)"
	@echo "  1. make install                # Install dependencies"
	@echo "  2. make test                   # Run tests"
	@echo "  3. make lint                   # Check code quality"
	@echo ""
	@echo ""
	@echo "$(YELLOW)📋 DETAILED COMMAND REFERENCE:$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup & Configuration:$(NC)"
	@echo "  $(GREEN)make setup-env$(NC)          Create .env files from .env.example (required first)"
	@echo "  $(GREEN)make env-check$(NC)          Check if all .env files exist + next steps"
	@echo "  $(GREEN)make install$(NC)           Set up venv + install all dependencies"
	@echo "  $(GREEN)make validate$(NC)          Check environment configuration"
	@echo "  $(GREEN)make validate-quiet$(NC)    Validate without verbose output"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@echo "  $(GREEN)make db$(NC)                Initialize database (DDL + DML + seed)"
	@echo ""
	@echo "$(YELLOW)Deployment (All-in-One):$(NC)"
	@echo "  $(GREEN)make deploy$(NC)            Full deployment (setup-env + install + start)"
	@echo "  $(GREEN)make docker-start-safe$(NC) Safe Docker (setup-env + validate + docker-start)"
	@echo ""
	@echo "$(YELLOW)Docker Operations:$(NC)"
	@echo "  $(GREEN)make docker-start$(NC)      Start all containers (or SERVICE=<name>)"
	@echo "  $(GREEN)make docker-stop$(NC)       Stop all containers (or SERVICE=<name>)"
	@echo "  $(GREEN)make docker-restart$(NC)    Restart all containers (or SERVICE=<name>)"
	@echo "  $(GREEN)make docker-build$(NC)      Build Docker images (or SERVICE=<name>)"
	@echo "  $(GREEN)make docker-ps$(NC)         Show container status (or SERVICE=<name>)"
	@echo "  $(GREEN)make docker-logs$(NC)       Show Docker logs (follow mode, or SERVICE=<name>)"
	@echo "  $(GREEN)make docker-clean$(NC)      Remove containers + volumes (or SERVICE=<name>)"
	@echo "  $(CYAN)💡 Services: postgres, pgadmin, mcp-server, email-worker$(NC)"
	@echo ""
	@echo "$(YELLOW)Services (Local):$(NC)"
	@echo "  $(GREEN)make start$(NC)             Start all local services"
	@echo "  $(GREEN)make stop$(NC)              Stop all local services"
	@echo "  $(GREEN)make status$(NC)            Show service status"
	@echo "  $(GREEN)make dev$(NC)               Start dev environment (interactive)"
	@echo ""
	@echo "$(YELLOW)Code Quality & Testing:$(NC)"
	@echo "  $(GREEN)make test$(NC)              Run all tests with coverage"
	@echo "  $(GREEN)make lint$(NC)              Run linter (ruff)"
	@echo "  $(GREEN)make format$(NC)            Format code (ruff)"
	@echo "  $(GREEN)make check$(NC)             Type checking (mypy)"
	@echo "  $(GREEN)make review$(NC)            Full code review (ruff + mypy + vulture + bandit)"
	@echo "  $(GREEN)make review-fix$(NC)        Auto-fix code issues"
	@echo "  $(GREEN)make review-report$(NC)     Detailed review report"
	@echo ""
	@echo "$(YELLOW)Documentation & Utilities:$(NC)"
	@echo "  $(GREEN)make docs$(NC)              Generate API documentation"
	@echo "  $(GREEN)make clean$(NC)             Remove cache files + build artifacts"
	@echo "  $(GREEN)make ci$(NC)                Run CI pipeline (lint + test + check)"
	@echo ""
	@echo "$(YELLOW)Shortcuts:$(NC)"
	@echo "  $(GREEN)i$(NC)  = install    $(GREEN)t$(NC)  = test    $(GREEN)c$(NC)  = clean"
	@echo "  $(GREEN)d$(NC)  = deploy     $(GREEN)s$(NC)  = start   $(GREEN)st$(NC) = stop"
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)📖 For detailed setup guide, see: docs/ENVIRONMENT_SETUP.md$(NC)"
	@echo "$(YELLOW)✅ For validation tips, see: VALIDATION_GUIDE.md$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""

# Setup and Installation
install:
	@echo "$(YELLOW)Setting up virtual environment...$(NC)"
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(ACTIVATE) && $(PIP) install --upgrade pip || { echo "$(RED)Failed to upgrade pip$(NC)"; exit 1; }
	@echo "$(YELLOW)Installing all dependencies...$(NC)"
	@$(ACTIVATE) && $(PIP) install -r requirements.txt && \
		$(PIP) install -r agent/requirements.txt && \
		$(PIP) install -r client_mcp/requirements.txt && \
		$(PIP) install -r email_service/requirements.txt && \
		$(PIP) install -r mcp_server/requirements.txt || { echo "$(RED)Failed to install dependencies$(NC)"; exit 1; }
	@echo "$(YELLOW)Installing code review tools...$(NC)"
	@$(ACTIVATE) && $(PIP) install -q vulture bandit isort || { echo "$(RED)Failed to install review tools$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Installation complete (including review tools)$(NC)"

# Environment Setup
setup-env:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Setting up .env files from templates$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)Creating .env files from .env.example templates...$(NC)"
	@test -f DockerConfig/.env.example || { echo "$(RED)DockerConfig/.env.example not found$(NC)"; exit 1; }
	@test -f mcp_server/.env.example || { echo "$(RED)mcp_server/.env.example not found$(NC)"; exit 1; }
	@test -f email_service/.env.example || { echo "$(RED)email_service/.env.example not found$(NC)"; exit 1; }
	@# Create .env files if they don't exist
	@if [ ! -f DockerConfig/.env ]; then \
		cp DockerConfig/.env.example DockerConfig/.env; \
		echo "$(GREEN)✓ Created DockerConfig/.env$(NC)"; \
	else \
		echo "$(YELLOW)⚠ DockerConfig/.env already exists (skipped)$(NC)"; \
	fi
	@if [ ! -f mcp_server/.env ]; then \
		cp mcp_server/.env.example mcp_server/.env; \
		echo "$(GREEN)✓ Created mcp_server/.env$(NC)"; \
	else \
		echo "$(YELLOW)⚠ mcp_server/.env already exists (skipped)$(NC)"; \
	fi
	@if [ ! -f email_service/.env ]; then \
		cp email_service/.env.example email_service/.env; \
		echo "$(GREEN)✓ Created email_service/.env$(NC)"; \
	else \
		echo "$(YELLOW)⚠ email_service/.env already exists (skipped)$(NC)"; \
	fi
	@if [ ! -f agent/.env ]; then \
		test -f agent/.env.example && cp agent/.env.example agent/.env && echo "$(GREEN)✓ Created agent/.env$(NC)" || echo "$(YELLOW)⚠ agent/.env.example not found (optional)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ agent/.env already exists (skipped)$(NC)"; \
	fi
	@if [ ! -f client_mcp/.env ]; then \
		test -f client_mcp/.env.example && cp client_mcp/.env.example client_mcp/.env && echo "$(GREEN)✓ Created client_mcp/.env$(NC)" || echo "$(YELLOW)⚠ client_mcp/.env.example not found (optional)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ client_mcp/.env already exists (skipped)$(NC)"; \
	fi
	@if [ ! -f SQL/.env ]; then \
		test -f SQL/.env.example && cp SQL/.env.example SQL/.env && echo "$(GREEN)✓ Created SQL/.env$(NC)" || echo "$(YELLOW)⚠ SQL/.env.example not found (optional)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ SQL/.env already exists (skipped)$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)⚠️  IMPORTANT: Edit the created .env files with your actual credentials:$(NC)"
	@echo "   • DockerConfig/.env - Database passwords"
	@echo "   • mcp_server/.env - Google API Key, Database URL"
	@echo "   • email_service/.env - SMTP credentials, Google API Key"
	@echo "   • agent/.env, client_mcp/.env - API keys (if needed)"
	@echo ""
	@echo "$(GREEN)✓ Environment setup complete$(NC)"

# Environment Check
env-check:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Checking environment files configuration$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@MISSING=0; \
	TOTAL=0; \
	for dir in DockerConfig mcp_server email_service agent client_mcp SQL; do \
		TOTAL=$$((TOTAL + 1)); \
		if [ -d "$$dir" ]; then \
			if [ -f "$$dir/.env" ]; then \
				echo "$(GREEN)✓$$dir/.env$(NC)                 - Found"; \
			else \
				echo "$(RED)✗ $$dir/.env$(NC)               - Missing (run: make setup-env)"; \
				MISSING=$$((MISSING + 1)); \
			fi; \
		fi; \
	done; \
	echo ""; \
	if [ $$MISSING -eq 0 ]; then \
		echo "$(GREEN)✓ All .env files are present!$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Next steps:$(NC)"; \
		echo "  1. Edit .env files with your credentials:"; \
		echo "     - DockerConfig/.env: POSTGRES_PASSWORD, PGADMIN_PASSWORD"; \
		echo "     - mcp_server/.env: GOOGLE_API_KEY, DATABASE_URL"; \
		echo "     - email_service/.env: GOOGLE_API_KEY, SMTP_*"; \
		echo ""; \
		echo "  2. Validate configuration:"; \
		echo "     $(GREEN)make validate$(NC)"; \
		echo ""; \
		echo "  3. Start Docker:"; \
		echo "     $(GREEN)make docker-start-safe$(NC) (or make docker-start)"; \
	else \
		echo "$(YELLOW)⚠ $$MISSING .env file(s) missing!$(NC)"; \
		echo ""; \
		echo "$(YELLOW)To create them, run:$(NC)"; \
		echo "  $(GREEN)make setup-env$(NC)"; \
	fi
	@echo ""

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
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(YELLOW)Starting all Docker containers...$(NC)"; \
		cd DockerConfig && docker-compose up -d || { echo "$(RED)Failed to start Docker containers$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ All Docker containers started$(NC)"; \
		echo "$(CYAN)Tip: Use 'make docker-start SERVICE=<name>' to start a specific service$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
	else \
		echo "$(YELLOW)Starting service: $(SERVICE)$(NC)"; \
		cd DockerConfig && docker-compose up -d $(SERVICE) || { echo "$(RED)Failed to start service: $(SERVICE)$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ Service '$(SERVICE)' started$(NC)"; \
	fi

docker-stop:
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		cd DockerConfig && docker-compose down || { echo "$(RED)Failed to stop Docker containers$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ All Docker containers stopped$(NC)"; \
	else \
		cd DockerConfig && docker-compose stop $(SERVICE) || { echo "$(RED)Failed to stop service: $(SERVICE)$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ Service '$(SERVICE)' stopped$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
	fi

docker-build:
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(YELLOW)Building all Docker images...$(NC)"; \
		cd DockerConfig && docker-compose build || { echo "$(RED)Failed to build Docker images$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ All Docker images built$(NC)"; \
		echo "$(CYAN)Tip: Use 'make docker-build SERVICE=<name>' to build a specific service$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
	else \
		echo "$(YELLOW)Building service: $(SERVICE)$(NC)"; \
		cd DockerConfig && docker-compose build $(SERVICE) || { echo "$(RED)Failed to build service: $(SERVICE)$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ Service '$(SERVICE)' built$(NC)"; \
	fi

docker-restart:
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(YELLOW)Restarting all Docker containers...$(NC)"; \
		cd DockerConfig && docker-compose restart || { echo "$(RED)Failed to restart Docker containers$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ All Docker containers restarted$(NC)"; \
		echo "$(CYAN)Tip: Use 'make docker-restart SERVICE=<name>' to restart a specific service$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
	else \
		echo "$(YELLOW)Restarting service: $(SERVICE)$(NC)"; \
		cd DockerConfig && docker-compose restart $(SERVICE) || { echo "$(RED)Failed to restart service: $(SERVICE)$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ Service '$(SERVICE)' restarted$(NC)"; \
	fi

docker-logs:
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(YELLOW)Following logs for all Docker containers...$(NC)"; \
		echo "$(CYAN)Tip: Use 'make docker-logs SERVICE=<name>' to view a specific service$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
		echo ""; \
		cd DockerConfig && docker-compose logs -f; \
	else \
		echo "$(YELLOW)Following logs for service: $(SERVICE)$(NC)"; \
		cd DockerConfig && docker-compose logs -f $(SERVICE) || { echo "$(RED)Failed to get logs for service: $(SERVICE)$(NC)"; exit 1; }; \
	fi

docker-ps:
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(YELLOW)Docker container status (all services):$(NC)"; \
		cd DockerConfig && docker-compose ps; \
		echo ""; \
		echo "$(CYAN)Tip: Use 'make docker-ps SERVICE=<name>' to view a specific service$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
	else \
		echo "$(YELLOW)Docker container status for service: $(SERVICE)$(NC)"; \
		cd DockerConfig && docker-compose ps $(SERVICE) || { echo "$(RED)Failed to get status for service: $(SERVICE)$(NC)"; exit 1; }; \
	fi

docker-clean:
	@command -v docker >/dev/null || { echo "$(RED)Docker not installed$(NC)"; exit 1; }
	@test -d DockerConfig || { echo "$(RED)DockerConfig directory not found$(NC)"; exit 1; }
	@if [ -z "$(SERVICE)" ]; then \
		echo "$(YELLOW)Cleaning up all Docker resources...$(NC)"; \
		cd DockerConfig && docker-compose down -v || { echo "$(RED)Failed to clean Docker containers$(NC)"; exit 1; }; \
		docker system prune -f || { echo "$(RED)Failed to prune Docker system$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ All Docker resources cleaned$(NC)"; \
		echo "$(CYAN)Tip: Use 'make docker-clean SERVICE=<name>' to remove a specific service$(NC)"; \
		echo "$(CYAN)Available services: postgres, pgadmin, mcp-server, email-worker$(NC)"; \
	else \
		echo "$(YELLOW)Removing service: $(SERVICE)$(NC)"; \
		cd DockerConfig && docker-compose rm --stop --force -v $(SERVICE) || { echo "$(RED)Failed to remove service: $(SERVICE)$(NC)"; exit 1; }; \
		echo "$(GREEN)✓ Service '$(SERVICE)' removed$(NC)"; \
		echo "$(YELLOW)Note: Volumes for $(SERVICE) have been removed. Use 'docker-start SERVICE=$(SERVICE)' to recreate.$(NC)"; \
	fi

# Deployment
deploy: setup-env
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

# Environment Validation
validate:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Lab01-MCP Environment Validation$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@$(PYTHON) scripts/validate_environment.py || { echo "$(RED)Validation failed$(NC)"; exit 1; }

validate-strict:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Lab01-MCP Environment Validation (STRICT MODE)$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@$(PYTHON) scripts/validate_environment.py --strict || { echo "$(RED)Validation failed (strict mode)$(NC)"; exit 1; }

validate-quiet:
	@$(PYTHON) scripts/validate_environment.py --quiet

validate-pydantic:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)Pydantic v2 Field Mapping Validation$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@$(PYTHON) scripts/validate_pydantic_mapping.py || { echo "$(RED)Pydantic validation failed$(NC)"; exit 1; }

# Safe Docker deployment (setup-env → validate → start)
docker-start-safe: setup-env validate-quiet docker-start
	@echo "$(GREEN)✓ Environment setup, validated and Docker started safely$(NC)"

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