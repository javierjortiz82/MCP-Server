#!/bin/bash

# Lab01-MCP Unified Deployment Script
# This script orchestrates the deployment of all project components

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"

# Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Lab01-MCP Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    echo -e "${YELLOW}Checking Python version...${NC}"
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        MIN_VERSION="3.9"
        if [ "$(printf '%s\n' "$MIN_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$MIN_VERSION" ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
        else
            echo -e "${RED}✗ Python $PYTHON_VERSION is too old. Minimum required: $MIN_VERSION${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Python3 not found${NC}"
        exit 1
    fi
}

# Function to setup virtual environment
setup_venv() {
    echo -e "${YELLOW}Setting up virtual environment...${NC}"
    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        echo -e "${GREEN}✓ Virtual environment already exists${NC}"
    fi

    # Activate virtual environment
    source "$VENV_PATH/bin/activate"

    # Upgrade pip
    pip install --upgrade pip >/dev/null 2>&1
    echo -e "${GREEN}✓ pip upgraded${NC}"
}

# Function to install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r "$PROJECT_ROOT/requirements.txt" >/dev/null 2>&1
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

# Function to setup environment variables
setup_environment() {
    echo -e "${YELLOW}Setting up environment variables...${NC}"

    # Check if .env exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            echo -e "${YELLOW}⚠ Created .env from .env.example - Please update with your API keys${NC}"
        else
            echo -e "${RED}✗ No .env file found${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Environment file found${NC}"
    fi

    # Load environment variables
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
}

# Function to check database connection
check_database() {
    echo -e "${YELLOW}Checking database connection...${NC}"

    # Check if PostgreSQL is running via Docker
    if docker ps | grep -q postgres; then
        echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
    else
        echo -e "${YELLOW}⚠ PostgreSQL not running. Starting Docker services...${NC}"
        cd "$PROJECT_ROOT/DockerConfig"
        docker-compose up -d postgres
        sleep 5
        echo -e "${GREEN}✓ PostgreSQL started${NC}"
    fi
}

# Function to start MCP server
start_mcp_server() {
    echo -e "${YELLOW}Starting MCP server...${NC}"

    cd "$PROJECT_ROOT/mcp"

    # Check if already running
    if [ -f "$PID_DIR/mcp_server.pid" ]; then
        PID=$(cat "$PID_DIR/mcp_server.pid")
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓ MCP server already running (PID: $PID)${NC}"
            return
        fi
    fi

    # Start MCP server in background
    nohup python main.py > "$LOG_DIR/mcp_server.log" 2>&1 &
    echo $! > "$PID_DIR/mcp_server.pid"

    sleep 3

    # Check if started successfully
    if ps -p $(cat "$PID_DIR/mcp_server.pid") > /dev/null; then
        echo -e "${GREEN}✓ MCP server started (PID: $(cat "$PID_DIR/mcp_server.pid"))${NC}"
    else
        echo -e "${RED}✗ Failed to start MCP server${NC}"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}Running tests...${NC}"

    cd "$PROJECT_ROOT"

    # Run pytest with coverage
    if pytest test/ --cov=client_mcp --cov=agent --cov-report=term-missing > "$LOG_DIR/test_results.log" 2>&1; then
        echo -e "${GREEN}✓ All tests passed${NC}"
    else
        echo -e "${YELLOW}⚠ Some tests failed. Check $LOG_DIR/test_results.log${NC}"
    fi
}

# Function to start Odiseo Bot
start_odiseo_bot() {
    echo -e "${YELLOW}Starting Odiseo Bot...${NC}"

    cd "$PROJECT_ROOT/client_mcp"

    # Check if already running
    if [ -f "$PID_DIR/odiseo_bot.pid" ]; then
        PID=$(cat "$PID_DIR/odiseo_bot.pid")
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓ Odiseo Bot already running (PID: $PID)${NC}"
            return
        fi
    fi

    # Start in interactive mode or background based on argument
    if [ "$1" = "--interactive" ]; then
        echo -e "${BLUE}Starting Odiseo Bot in interactive mode...${NC}"
        python main.py
    else
        nohup python main.py > "$LOG_DIR/odiseo_bot.log" 2>&1 &
        echo $! > "$PID_DIR/odiseo_bot.pid"
        echo -e "${GREEN}✓ Odiseo Bot started (PID: $(cat "$PID_DIR/odiseo_bot.pid"))${NC}"
    fi
}

# Function to show status
show_status() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}         Deployment Status${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Check MCP server
    if [ -f "$PID_DIR/mcp_server.pid" ] && ps -p $(cat "$PID_DIR/mcp_server.pid") > /dev/null 2>&1; then
        echo -e "${GREEN}✓ MCP Server: Running (PID: $(cat "$PID_DIR/mcp_server.pid"))${NC}"
    else
        echo -e "${RED}✗ MCP Server: Not running${NC}"
    fi

    # Check Odiseo Bot
    if [ -f "$PID_DIR/odiseo_bot.pid" ] && ps -p $(cat "$PID_DIR/odiseo_bot.pid") > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Odiseo Bot: Running (PID: $(cat "$PID_DIR/odiseo_bot.pid"))${NC}"
    else
        echo -e "${RED}✗ Odiseo Bot: Not running${NC}"
    fi

    # Check PostgreSQL
    if docker ps | grep -q postgres; then
        echo -e "${GREEN}✓ PostgreSQL: Running${NC}"
    else
        echo -e "${RED}✗ PostgreSQL: Not running${NC}"
    fi

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Logs available at: $LOG_DIR${NC}"
}

# Function to stop all services
stop_all() {
    echo -e "${YELLOW}Stopping all services...${NC}"

    # Stop Odiseo Bot
    if [ -f "$PID_DIR/odiseo_bot.pid" ]; then
        kill $(cat "$PID_DIR/odiseo_bot.pid") 2>/dev/null || true
        rm "$PID_DIR/odiseo_bot.pid"
        echo -e "${GREEN}✓ Odiseo Bot stopped${NC}"
    fi

    # Stop MCP server
    if [ -f "$PID_DIR/mcp_server.pid" ]; then
        kill $(cat "$PID_DIR/mcp_server.pid") 2>/dev/null || true
        rm "$PID_DIR/mcp_server.pid"
        echo -e "${GREEN}✓ MCP Server stopped${NC}"
    fi

    # Stop Docker services
    cd "$PROJECT_ROOT/DockerConfig"
    docker-compose down >/dev/null 2>&1
    echo -e "${GREEN}✓ Docker services stopped${NC}"
}

# Main deployment flow
main() {
    case "${1:-deploy}" in
        deploy)
            check_python_version
            setup_venv
            install_dependencies
            setup_environment
            check_database
            start_mcp_server
            run_tests
            start_odiseo_bot "${2:-}"
            show_status
            ;;
        start)
            setup_environment
            check_database
            start_mcp_server
            start_odiseo_bot "${2:-}"
            show_status
            ;;
        stop)
            stop_all
            ;;
        status)
            show_status
            ;;
        test)
            setup_venv
            run_tests
            ;;
        *)
            echo "Usage: $0 {deploy|start|stop|status|test} [--interactive]"
            echo "  deploy: Full deployment (install deps, run tests, start services)"
            echo "  start: Start services only"
            echo "  stop: Stop all services"
            echo "  status: Show service status"
            echo "  test: Run tests only"
            echo ""
            echo "Options:"
            echo "  --interactive: Start Odiseo Bot in interactive mode"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"