# Port Configuration Guide

## Overview

This document details the port configuration for Lab01-MCP services, especially the PostgreSQL port change to avoid conflicts with existing installations.

## Port Mappings

| Service | External Port | Internal Port | Environment Variable | Notes |
|---------|--------------|---------------|---------------------|--------|
| PostgreSQL | **5434** | 5432 | `POSTGRES_PORT` | Changed from 5432 to avoid conflicts |
| MCP Server | 3000 | 3000 | `MCP_PORT` | REST API endpoint |
| Client MCP | - | - | - | Interactive CLI (no port) |
| Agent Service | 8000 | 8000 | `AGENT_PORT` | Gemini Agent API |
| PgAdmin | 5050 | 80 | `PGADMIN_PORT` | Web interface (dev only) |
| Redis | 6379 | 6379 | `REDIS_PORT` | Cache service (optional) |
| Nginx | 80, 443 | 80, 443 | - | Production only |

## PostgreSQL Port Configuration

### Why Port 5434?

The PostgreSQL service is configured to use **port 5434** externally to avoid conflicts with existing PostgreSQL installations that typically use port 5432.

### Configuration Details

```yaml
# docker-compose.yml
postgres:
  ports:
    - "${POSTGRES_PORT:-5434}:5432"
    #   ^external:internal^
```

- **External Port (5434)**: Port accessible from your host machine
- **Internal Port (5432)**: Port used within Docker network

### Connection Strings

#### From Host Machine
```bash
# Connect to PostgreSQL from host
psql -h localhost -p 5434 -U mcp_user -d mcp_db

# Connection URL from host
postgresql://mcp_user:password@localhost:5434/mcp_db
```

#### From Docker Containers
```bash
# Containers use internal port 5432
postgresql://mcp_user:password@postgres:5432/mcp_db
```

### Important Notes

1. **Internal Communication**: Services within Docker use the standard port 5432
2. **External Access**: Use port 5434 when connecting from your host machine
3. **No Changes Required**: The application code doesn't need changes - it uses internal ports

## Configuration Files

### .env File
```env
# PostgreSQL external port
POSTGRES_PORT=5434
```

### Database URL Examples

#### Development (from host)
```env
DATABASE_URL=postgresql://mcp_user:password@localhost:5434/mcp_db
```

#### Docker Services (internal)
```env
DATABASE_URL=postgresql://mcp_user:password@postgres:5432/mcp_db
```

## Common Issues and Solutions

### Issue: "Port 5432 already in use"

**Cause**: You have PostgreSQL already running on port 5432

**Solution**: We've configured port 5434 to avoid this conflict

### Issue: "Cannot connect to database"

**Check these:**

1. **From Host Machine**:
   ```bash
   # Use port 5434
   psql -h localhost -p 5434 -U mcp_user
   ```

2. **From Docker Container**:
   ```bash
   # Use port 5432 and hostname 'postgres'
   docker exec -it lab01_client psql -h postgres -p 5432 -U mcp_user
   ```

### Issue: "Connection refused on port 5434"

**Solutions**:

1. Check if container is running:
   ```bash
   docker ps | grep postgres
   ```

2. Check port binding:
   ```bash
   docker port lab01_postgres
   ```

3. Verify environment variable:
   ```bash
   grep POSTGRES_PORT .env
   ```

## Testing Connections

### Test from Host
```bash
# Using psql
psql -h localhost -p 5434 -U mcp_user -d mcp_db -c "SELECT 1"

# Using pg_isready
pg_isready -h localhost -p 5434 -U mcp_user

# Using curl (if pg endpoint exists)
curl -v telnet://localhost:5434
```

### Test from Container
```bash
# From MCP server container
docker exec -it lab01_mcp_server psql -h postgres -p 5432 -U mcp_user -c "SELECT 1"

# Using docker-compose
docker-compose exec mcp-server psql -h postgres -p 5432 -U mcp_user -c "SELECT 1"
```

## Migration from Port 5432

If migrating from an existing setup using port 5432:

1. **Stop existing PostgreSQL** (if running on host):
   ```bash
   sudo systemctl stop postgresql  # Linux
   brew services stop postgresql   # macOS
   ```

2. **Update connection strings** in your application:
   ```python
   # Old
   DATABASE_URL = "postgresql://user:pass@localhost:5432/db"

   # New (from host)
   DATABASE_URL = "postgresql://user:pass@localhost:5434/db"
   ```

3. **Update database tools**:
   - DBeaver: Change connection port to 5434
   - pgAdmin: Update server configuration
   - TablePlus: Update connection settings

## Docker Network Communication

### How It Works

```
Host Machine
    |
    | Port 5434 (external)
    v
Docker Bridge Network (lab01_network)
    |
    | Port 5432 (internal)
    v
PostgreSQL Container
```

### Service Discovery

Docker services can reach PostgreSQL using:
- **Hostname**: `postgres` (service name)
- **Port**: `5432` (internal port)
- **Network**: `lab01_network` (custom bridge)

Example from MCP Server:
```python
# Correct - uses Docker service name and internal port
DATABASE_URL = "postgresql://mcp_user:password@postgres:5432/mcp_db"

# Wrong - would fail from container
DATABASE_URL = "postgresql://mcp_user:password@localhost:5434/mcp_db"
```

## Quick Reference

### Connect from Different Contexts

| Context | Host | Port | Example |
|---------|------|------|---------|
| Host Machine | `localhost` | `5434` | `psql -h localhost -p 5434` |
| Docker Container | `postgres` | `5432` | `psql -h postgres -p 5432` |
| Docker Compose | `postgres` | `5432` | `postgresql://user@postgres:5432/db` |
| External App | `your-server.com` | `5434` | `postgresql://user@server.com:5434/db` |

### Environment Variables

```bash
# Required in .env
POSTGRES_PORT=5434        # External port for host access
POSTGRES_USER=mcp_user    # Database user
POSTGRES_PASSWORD=secret  # Database password
POSTGRES_DB=mcp_db       # Database name
```

## Troubleshooting Checklist

- [ ] Is PostgreSQL container running? `docker ps`
- [ ] Is port 5434 free? `lsof -i :5434` or `netstat -an | grep 5434`
- [ ] Is .env file configured? `cat .env | grep POSTGRES_PORT`
- [ ] Can you connect from host? `psql -h localhost -p 5434 -U mcp_user`
- [ ] Can containers connect? `docker exec -it lab01_mcp_server pg_isready -h postgres`
- [ ] Are credentials correct? Check POSTGRES_USER and POSTGRES_PASSWORD in .env
- [ ] Is the database created? `docker logs lab01_postgres | grep "database system is ready"`

## Summary

- **PostgreSQL runs on port 5434** (external) to avoid conflicts
- **Internal services use port 5432** (standard PostgreSQL port)
- **No code changes required** - Docker handles port mapping
- **Connection strings differ** based on where you're connecting from