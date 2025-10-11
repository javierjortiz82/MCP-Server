#!/bin/bash

# Docker Management Script for Lab01-MCP
# Provides easy commands for managing Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="lab01-mcp"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Functions
print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}    Lab01-MCP Docker Management${NC}"
    echo -e "${BLUE}======================================${NC}"
}

check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}Warning: .env file not found!${NC}"
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
        echo -e "${RED}Please edit .env file with your configuration!${NC}"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed!${NC}"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed!${NC}"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${RED}Docker daemon is not running!${NC}"
        exit 1
    fi
}

# Commands
cmd_start() {
    echo -e "${GREEN}Starting all services...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Services started successfully!${NC}"
    cmd_status
}

cmd_start_dev() {
    echo -e "${GREEN}Starting development environment...${NC}"
    docker-compose --profile dev up -d
    echo -e "${GREEN}Development environment started!${NC}"
    echo -e "${YELLOW}PgAdmin available at: http://localhost:5050${NC}"
    cmd_status
}

cmd_start_prod() {
    echo -e "${GREEN}Starting production environment...${NC}"
    docker-compose --profile production up -d
    echo -e "${GREEN}Production environment started!${NC}"
    cmd_status
}

cmd_stop() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    docker-compose down
    echo -e "${GREEN}Services stopped successfully!${NC}"
}

cmd_restart() {
    echo -e "${YELLOW}Restarting all services...${NC}"
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    echo -e "${BLUE}Service Status:${NC}"
    docker-compose ps
}

cmd_logs() {
    service=${1:-""}
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

cmd_build() {
    echo -e "${GREEN}Building all services...${NC}"
    docker-compose build --no-cache
    echo -e "${GREEN}Build completed successfully!${NC}"
}

cmd_clean() {
    echo -e "${YELLOW}Cleaning up Docker resources...${NC}"
    docker-compose down -v
    docker system prune -f
    echo -e "${GREEN}Cleanup completed!${NC}"
}

cmd_backup() {
    echo -e "${GREEN}Creating database backup...${NC}"
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="backup_${timestamp}.sql"

    docker-compose exec -T postgres pg_dump -U mcp_user mcp_db > "./backups/$backup_file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Backup created: ./backups/$backup_file${NC}"
    else
        echo -e "${RED}Backup failed!${NC}"
        exit 1
    fi
}

cmd_restore() {
    backup_file=${1:-""}
    if [ -z "$backup_file" ]; then
        echo -e "${RED}Usage: $0 restore <backup_file>${NC}"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Backup file not found: $backup_file${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Restoring database from: $backup_file${NC}"
    docker-compose exec -T postgres psql -U mcp_user mcp_db < "$backup_file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Database restored successfully!${NC}"
    else
        echo -e "${RED}Restore failed!${NC}"
        exit 1
    fi
}

cmd_exec() {
    service=${1:-""}
    shift
    if [ -z "$service" ]; then
        echo -e "${RED}Usage: $0 exec <service> <command>${NC}"
        exit 1
    fi
    docker-compose exec "$service" "$@"
}

cmd_shell() {
    service=${1:-"client-mcp"}
    echo -e "${BLUE}Opening shell in $service...${NC}"
    docker-compose exec "$service" /bin/bash
}

cmd_test() {
    echo -e "${GREEN}Running tests...${NC}"
    docker-compose exec client-mcp pytest /app/test/
}

cmd_health() {
    echo -e "${BLUE}Checking service health...${NC}"

    # Check PostgreSQL
    if docker-compose exec postgres pg_isready -U mcp_user &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is healthy${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is not healthy${NC}"
    fi

    # Check MCP Server
    if curl -f http://localhost:3000/health &> /dev/null; then
        echo -e "${GREEN}✓ MCP Server is healthy${NC}"
    else
        echo -e "${RED}✗ MCP Server is not healthy${NC}"
    fi

    # Check Client
    if docker-compose exec client-mcp python -c "import sys; sys.exit(0)" &> /dev/null; then
        echo -e "${GREEN}✓ Client MCP is healthy${NC}"
    else
        echo -e "${RED}✗ Client MCP is not healthy${NC}"
    fi
}

cmd_help() {
    print_header
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start         - Start all services"
    echo "  start-dev     - Start development environment (with PgAdmin)"
    echo "  start-prod    - Start production environment (with Nginx)"
    echo "  stop          - Stop all services"
    echo "  restart       - Restart all services"
    echo "  status        - Show service status"
    echo "  logs [svc]    - Show logs (optionally for specific service)"
    echo "  build         - Build all Docker images"
    echo "  clean         - Clean up Docker resources"
    echo "  backup        - Create database backup"
    echo "  restore <file> - Restore database from backup"
    echo "  exec <svc> <cmd> - Execute command in service"
    echo "  shell [svc]   - Open shell in service (default: client-mcp)"
    echo "  test          - Run tests"
    echo "  health        - Check service health"
    echo "  help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Start all services"
    echo "  $0 logs mcp-server # View MCP server logs"
    echo "  $0 shell postgres  # Open shell in PostgreSQL container"
    echo "  $0 backup          # Create database backup"
    echo ""
}

# Main script
print_header
check_docker
check_env_file

# Create necessary directories
mkdir -p backups logs

# Parse command
command=${1:-"help"}
shift || true

case "$command" in
    start)
        cmd_start
        ;;
    start-dev)
        cmd_start_dev
        ;;
    start-prod)
        cmd_start_prod
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$@"
        ;;
    build)
        cmd_build
        ;;
    clean)
        cmd_clean
        ;;
    backup)
        cmd_backup
        ;;
    restore)
        cmd_restore "$@"
        ;;
    exec)
        cmd_exec "$@"
        ;;
    shell)
        cmd_shell "$@"
        ;;
    test)
        cmd_test
        ;;
    health)
        cmd_health
        ;;
    help)
        cmd_help
        ;;
    *)
        echo -e "${RED}Unknown command: $command${NC}"
        cmd_help
        exit 1
        ;;
esac