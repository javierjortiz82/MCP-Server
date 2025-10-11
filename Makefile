# Lab01-MCP Makefile
# Simplifies common development and deployment tasks

.PHONY: help install test clean deploy start stop status lint format check docs

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
	@echo "$(GREEN)install$(NC)    - Set up virtual environment and install dependencies"
	@echo "$(GREEN)test$(NC)       - Run all tests with coverage"
	@echo "$(GREEN)test-unit$(NC)  - Run unit tests only"
	@echo "$(GREEN)test-int$(NC)   - Run integration tests only"
	@echo "$(GREEN)clean$(NC)      - Remove cache files and build artifacts"
	@echo "$(GREEN)deploy$(NC)     - Full deployment (install + start services)"
	@echo "$(GREEN)start$(NC)      - Start all services"
	@echo "$(GREEN)stop$(NC)       - Stop all services"
	@echo "$(GREEN)status$(NC)     - Show service status"
	@echo "$(GREEN)lint$(NC)       - Run code linting"
	@echo "$(GREEN)format$(NC)     - Format code with black"
	@echo "$(GREEN)check$(NC)      - Run type checking with mypy"
	@echo "$(GREEN)docs$(NC)       - Generate documentation"
	@echo "$(GREEN)docker-up$(NC)  - Start Docker services"
	@echo "$(GREEN)docker-down$(NC) - Stop Docker services"
	@echo "$(GREEN)dev$(NC)        - Start development environment"

# Setup and Installation
install:
	@echo "$(YELLOW)Setting up virtual environment...$(NC)"
	@$(PYTHON) -m venv $(VENV)
	@$(ACTIVATE) && $(PIP) install --upgrade pip
	@$(ACTIVATE) && $(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Installation complete$(NC)"

# Testing
test:
	@echo "$(YELLOW)Running all tests...$(NC)"
	@$(ACTIVATE) && pytest test/ -v --cov=client_mcp --cov=agent --cov-report=term-missing

test-unit:
	@echo "$(YELLOW)Running unit tests...$(NC)"
	@$(ACTIVATE) && pytest test/test_gemini_agent.py -v

test-int:
	@echo "$(YELLOW)Running integration tests...$(NC)"
	@$(ACTIVATE) && pytest test/test_integration.py -v

test-quick:
	@echo "$(YELLOW)Running quick tests (no coverage)...$(NC)"
	@$(ACTIVATE) && pytest test/ -v -x

# Code Quality
lint:
	@echo "$(YELLOW)Running linter...$(NC)"
	@$(ACTIVATE) && ruff check client_mcp/ agent/ test/

format:
	@echo "$(YELLOW)Formatting code...$(NC)"
	@$(ACTIVATE) && black client_mcp/ agent/ test/

check:
	@echo "$(YELLOW)Running type checker...$(NC)"
	@$(ACTIVATE) && mypy client_mcp/ agent/

quality: lint format check
	@echo "$(GREEN)✓ Code quality checks complete$(NC)"

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

# Docker
docker-up:
	@echo "$(YELLOW)Starting Docker services...$(NC)"
	@cd DockerConfig && docker-compose up -d
	@echo "$(GREEN)✓ Docker services started$(NC)"

docker-down:
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	@cd DockerConfig && docker-compose down
	@echo "$(GREEN)✓ Docker services stopped$(NC)"

docker-logs:
	@cd DockerConfig && docker-compose logs -f

# Deployment
deploy:
	@echo "$(BLUE)Starting full deployment...$(NC)"
	@chmod +x scripts/deploy.sh
	@scripts/deploy.sh deploy

start:
	@echo "$(YELLOW)Starting services...$(NC)"
	@chmod +x scripts/deploy.sh
	@scripts/deploy.sh start

stop:
	@echo "$(YELLOW)Stopping services...$(NC)"
	@chmod +x scripts/deploy.sh
	@scripts/deploy.sh stop

status:
	@chmod +x scripts/deploy.sh
	@scripts/deploy.sh status

# Development
dev: docker-up
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(ACTIVATE) && cd mcp && $(PYTHON) main.py &
	@sleep 3
	@$(ACTIVATE) && cd client_mcp && $(PYTHON) main.py

dev-agent:
	@echo "$(YELLOW)Testing agent module...$(NC)"
	@$(ACTIVATE) && $(PYTHON) -c "from agent import GeminiAgent; print('Agent module OK')"

dev-client:
	@echo "$(YELLOW)Starting client in dev mode...$(NC)"
	@$(ACTIVATE) && cd client_mcp && $(PYTHON) main.py

# Documentation
docs:
	@echo "$(YELLOW)Generating documentation...$(NC)"
	@$(ACTIVATE) && pdoc --html --output-dir docs/api agent client_mcp
	@echo "$(GREEN)✓ Documentation generated in docs/api$(NC)"

# Database
db-init:
	@echo "$(YELLOW)Initializing database...$(NC)"
	@cd SQL/scripts && bash init-db.sh

db-populate:
	@echo "$(YELLOW)Populating database...$(NC)"
	@cd SQL/scripts && bash populate-db.sh

db-reset: docker-down docker-up
	@sleep 5
	@make db-init
	@make db-populate
	@echo "$(GREEN)✓ Database reset complete$(NC)"

# Monitoring
logs:
	@tail -f logs/*.log

monitor:
	@watch -n 2 "make status"

# CI/CD
ci: clean install lint check test
	@echo "$(GREEN)✓ CI checks passed$(NC)"

build:
	@echo "$(YELLOW)Building project...$(NC)"
	@$(ACTIVATE) && $(PYTHON) -m build
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