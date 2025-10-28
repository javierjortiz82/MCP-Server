#!/bin/bash
################################################################################
# PostgreSQL Database Backup Script for Lab01-MCP
################################################################################
#
# Description:
#   Creates compressed backups of the PostgreSQL database running in Docker
#   Automatically rotates old backups (keeps last 7)
#
# Usage:
#   ./scripts/backup_database.sh
#
# Cron setup (daily at 3 AM):
#   0 3 * * * /home/javort/Lab01-MCP/scripts/backup_database.sh >> /var/log/postgres_backup.log 2>&1
#
# Author: Lab01-MCP Team
# Date: 2025-10-28
################################################################################

set -e  # Exit on error

# Configuration (reads from DockerConfig/.env)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/DockerConfig/.env"

# Default values
POSTGRES_CONTAINER="mcp-postgres"
POSTGRES_USER="mcp_user"
POSTGRES_DB="mcpdb"
BACKUP_DIR="$PROJECT_ROOT/backups"
KEEP_BACKUPS=7

# Load configuration from .env if exists
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    POSTGRES_USER="${POSTGRES_USER:-mcp_user}"
    POSTGRES_DB="${POSTGRES_DB:-mcpdb}"
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/postgres_${TIMESTAMP}.backup"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "PostgreSQL Backup Script - Lab01-MCP"
echo "================================================================================"
echo "Start time: $(date)"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running${NC}"
    exit 1
fi

# Check if container exists and is running
if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
    echo -e "${RED}ERROR: Container '${POSTGRES_CONTAINER}' is not running${NC}"
    echo "Available containers:"
    docker ps --format 'table {{.Names}}\t{{.Status}}'
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker and container are running"
echo ""

# Create backup
echo "Creating backup..."
echo "  Database: $POSTGRES_DB"
echo "  User: $POSTGRES_USER"
echo "  Container: $POSTGRES_CONTAINER"
echo "  Output: $BACKUP_FILE"
echo ""

# Execute pg_dump inside container
if docker exec "$POSTGRES_CONTAINER" pg_dump \
    -U "$POSTGRES_USER" \
    -F c \
    -b \
    -v \
    -f /tmp/backup.dump \
    "$POSTGRES_DB" 2>&1 | grep -E "(dumping|saving)"; then

    echo ""
    echo -e "${GREEN}✓${NC} Database dump created inside container"
else
    echo -e "${RED}ERROR: Failed to create database dump${NC}"
    exit 1
fi

# Copy backup from container to host
if docker cp "${POSTGRES_CONTAINER}:/tmp/backup.dump" "$BACKUP_FILE"; then
    echo -e "${GREEN}✓${NC} Backup copied to host: $BACKUP_FILE"
else
    echo -e "${RED}ERROR: Failed to copy backup from container${NC}"
    exit 1
fi

# Clean up temporary file in container
docker exec "$POSTGRES_CONTAINER" rm /tmp/backup.dump 2>/dev/null || true

# Get backup file size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "Backup size: $BACKUP_SIZE"

# Verify backup integrity
echo ""
echo "Verifying backup integrity..."
if docker cp "$BACKUP_FILE" "${POSTGRES_CONTAINER}:/tmp/verify.dump" && \
   docker exec "$POSTGRES_CONTAINER" pg_restore --list /tmp/verify.dump > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backup integrity verified"
    docker exec "$POSTGRES_CONTAINER" rm /tmp/verify.dump 2>/dev/null || true
else
    echo -e "${YELLOW}WARNING: Could not verify backup integrity${NC}"
fi

# Rotate old backups (keep last N backups)
echo ""
echo "Rotating old backups (keeping last $KEEP_BACKUPS)..."
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/postgres_*.backup 2>/dev/null | wc -l)
echo "Total backups: $BACKUP_COUNT"

if [ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]; then
    OLD_BACKUPS=$(ls -t "$BACKUP_DIR"/postgres_*.backup | tail -n +$((KEEP_BACKUPS + 1)))
    echo "Removing old backups:"
    echo "$OLD_BACKUPS" | while read -r file; do
        echo "  - $(basename "$file")"
        rm "$file"
    done
    echo -e "${GREEN}✓${NC} Removed $((BACKUP_COUNT - KEEP_BACKUPS)) old backup(s)"
else
    echo "No rotation needed"
fi

# Summary
echo ""
echo "================================================================================"
echo -e "${GREEN}BACKUP COMPLETED SUCCESSFULLY${NC}"
echo "================================================================================"
echo "Backup file: $BACKUP_FILE"
echo "Backup size: $BACKUP_SIZE"
echo "End time: $(date)"
echo ""
echo "To restore this backup:"
echo "  docker cp $BACKUP_FILE ${POSTGRES_CONTAINER}:/tmp/restore.dump"
echo "  docker exec ${POSTGRES_CONTAINER} pg_restore -U ${POSTGRES_USER} -d ${POSTGRES_DB} -v /tmp/restore.dump"
echo ""
echo "Available backups:"
ls -lh "$BACKUP_DIR"/postgres_*.backup | awk '{print "  " $9 " (" $5 ")"}'
echo ""
