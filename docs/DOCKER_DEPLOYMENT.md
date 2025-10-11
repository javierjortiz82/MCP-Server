# Docker Deployment Guide - Lab01-MCP

## Overview

This guide covers the Docker deployment configuration for Lab01-MCP, including development, staging, and production environments.

## Architecture

```
┌─────────────────┐
│     Nginx       │ (Reverse Proxy - Production)
│   Port 80/443   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬───────────┐
    │         │          │           │
┌───▼───┐ ┌──▼────┐ ┌───▼───┐ ┌────▼────┐
│  MCP   │ │Client │ │Agent  │ │ PgAdmin │
│Server  │ │  MCP  │ │Service│ │  (Dev)  │
│Port 3000│ │       │ │Port 8000│ │Port 5050│
└───┬────┘ └───┬───┘ └───┬───┘ └────┬────┘
    │          │         │           │
    └──────────┴─────────┴───────────┘
                    │
           ┌────────▼────────┐
           │   PostgreSQL    │
           │  with pgvector  │
           │    Port 5432    │
           └─────────────────┘
```

## Features

### Security
- ✅ **Non-root users** in all containers
- ✅ **Environment-based secrets** management
- ✅ **Network isolation** with custom bridge network
- ✅ **SSL/TLS support** with Nginx
- ✅ **Rate limiting** configured
- ✅ **Security headers** implemented

### Performance
- ✅ **Resource limits** defined for all services
- ✅ **Health checks** for auto-recovery
- ✅ **Connection pooling** for database
- ✅ **Gzip compression** in Nginx
- ✅ **Optimized logging** with rotation

### Scalability
- ✅ **Load balancing** ready with Nginx
- ✅ **Horizontal scaling** support
- ✅ **Redis caching** (optional)
- ✅ **Separated services** architecture

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose 1.29+
- 4GB RAM minimum
- 10GB disk space

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Required variables:
# - GOOGLE_API_KEY
# - POSTGRES_PASSWORD
# - PGADMIN_PASSWORD (for development)
```

### 3. Start Services

```bash
# Development environment (with PgAdmin)
./scripts/docker-manage.sh start-dev

# Production environment (with Nginx)
./scripts/docker-manage.sh start-prod

# Basic start (no extras)
./scripts/docker-manage.sh start
```

## Environment Configurations

### Development

```yaml
# Includes:
- Hot reload for code changes
- PgAdmin for database management
- Debug logging enabled
- Ports exposed for direct access
- Source code mounted as volumes
```

**Access Points:**
- MCP Server: http://localhost:3000
- PgAdmin: http://localhost:5050
- PostgreSQL: localhost:5434 (external) → 5432 (internal)
- Agent Service: http://localhost:8000

### Production

```yaml
# Includes:
- Nginx reverse proxy with SSL
- Optimized builds
- Resource limits enforced
- Health checks active
- Log rotation configured
```

**Access Points:**
- HTTPS: https://yourdomain.com
- HTTP→HTTPS redirect
- API: https://yourdomain.com/api/
- Metrics: Internal only

## Service Configuration

### PostgreSQL Database

```yaml
Features:
- pgvector extension for embeddings
- Connection pooling (1-5 connections)
- Health checks every 10s
- Automatic initialization scripts
- Volume persistence

Resource Limits:
- CPU: 2.0 cores max, 0.5 reserved
- Memory: 2GB max, 512MB reserved
```

### MCP Server

```yaml
Features:
- FastMCP framework
- Stateless HTTP mode
- Tool discovery
- Health endpoint
- Metrics collection

Resource Limits:
- CPU: 1.0 core max, 0.25 reserved
- Memory: 1GB max, 256MB reserved
```

### Client MCP (Odiseo Bot)

```yaml
Features:
- Google Gemini integration
- Interactive CLI
- Conversation memory
- Error recovery

Resource Limits:
- CPU: 1.0 core max, 0.25 reserved
- Memory: 1GB max, 256MB reserved
```

### Gemini Agent Service

```yaml
Features:
- Separated AI logic
- REST API interface
- Health monitoring
- Async processing

Resource Limits:
- CPU: 0.5 cores max, 0.1 reserved
- Memory: 512MB max, 128MB reserved
```

## Management Commands

### Using docker-manage.sh

```bash
# Start services
./scripts/docker-manage.sh start

# Stop services
./scripts/docker-manage.sh stop

# View logs
./scripts/docker-manage.sh logs mcp-server

# Check health
./scripts/docker-manage.sh health

# Create backup
./scripts/docker-manage.sh backup

# Restore backup
./scripts/docker-manage.sh restore backup_20250106_120000.sql

# Open shell
./scripts/docker-manage.sh shell postgres

# Run tests
./scripts/docker-manage.sh test

# Clean everything
./scripts/docker-manage.sh clean
```

### Direct Docker Commands

```bash
# Start with specific profile
docker-compose --profile dev up -d

# Scale services
docker-compose up -d --scale mcp-server=3

# View resource usage
docker stats

# Inspect network
docker network inspect lab01-mcp_lab01_network

# Execute command
docker-compose exec postgres psql -U mcp_user -d mcp_db
```

## Health Monitoring

### Health Check Endpoints

| Service | Endpoint | Expected Response |
|---------|----------|-------------------|
| MCP Server | http://localhost:3000/health | 200 OK |
| Agent Service | http://localhost:8000/health | 200 OK |
| Nginx | http://localhost/health | "healthy\n" |
| PostgreSQL | `pg_isready` command | 0 exit code |

### Monitoring Commands

```bash
# Check all health statuses
./scripts/docker-manage.sh health

# View container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check specific service
docker-compose exec postgres pg_isready -U mcp_user
```

## Troubleshooting

### Common Issues

#### 1. API Key Error
```bash
Error: GOOGLE_API_KEY not set in .env
Solution: Add your Google API key to .env file
```

#### 2. Port Already in Use
```bash
Error: bind: address already in use
Solution: Change port in .env or stop conflicting service
```

#### 3. Database Connection Failed
```bash
Error: connection to server at "postgres" failed
Solution: Wait for postgres to be healthy or check credentials
```

#### 4. Out of Memory
```bash
Error: Container killed due to OOM
Solution: Increase memory limits in docker-compose.yml
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up

# View detailed logs
docker-compose logs -f --tail=100 mcp-server

# Inspect container
docker inspect lab01_mcp_server
```

## Backup and Recovery

### Automated Backup

```bash
# Create backup
./scripts/docker-manage.sh backup

# Backups stored in ./backups/
ls -la ./backups/
```

### Manual Backup

```bash
# Backup database
docker-compose exec postgres pg_dump -U mcp_user mcp_db > backup.sql

# Backup volumes
docker run --rm -v lab01-mcp_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_data.tar.gz /data
```

### Restore

```bash
# Restore database
./scripts/docker-manage.sh restore ./backups/backup_20250106_120000.sql

# Restore volumes
docker run --rm -v lab01-mcp_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_data.tar.gz -C /
```

## SSL/TLS Configuration

### Self-Signed Certificates (Development)

```bash
# Generate certificates
mkdir -p DockerConfig/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout DockerConfig/ssl/key.pem \
  -out DockerConfig/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=lab01.local"
```

### Let's Encrypt (Production)

```bash
# Use Certbot with Nginx
docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot \
  -d yourdomain.com
```

## Performance Tuning

### Database Optimization

```sql
-- Check slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Analyze tables
ANALYZE products;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

### Container Resources

```bash
# Monitor resource usage
docker stats --no-stream

# Adjust limits in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'  # Increase as needed
      memory: 4G    # Increase as needed
```

## Security Best Practices

### 1. Environment Variables
- ✅ Never commit `.env` files
- ✅ Use strong passwords
- ✅ Rotate API keys regularly
- ✅ Use secrets management in production

### 2. Network Security
- ✅ Use internal networks for service communication
- ✅ Expose only necessary ports
- ✅ Enable firewall rules
- ✅ Use SSL/TLS for all external traffic

### 3. Container Security
- ✅ Run as non-root user
- ✅ Use official base images
- ✅ Keep images updated
- ✅ Scan for vulnerabilities

### 4. Data Security
- ✅ Encrypt data at rest
- ✅ Regular backups
- ✅ Secure backup storage
- ✅ Test restore procedures

## Scaling Guidelines

### Horizontal Scaling

```bash
# Scale MCP Server
docker-compose up -d --scale mcp-server=3

# Configure load balancing in Nginx
upstream mcp_backend {
    least_conn;
    server mcp-server_1:3000;
    server mcp-server_2:3000;
    server mcp-server_3:3000;
}
```

### Vertical Scaling

```yaml
# Increase resources in docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '4.0'  # Increased
          memory: 8G   # Increased
```

## Maintenance

### Regular Tasks

```bash
# Weekly: Update images
docker-compose pull

# Weekly: Clean unused resources
docker system prune -f

# Daily: Check logs for errors
./scripts/docker-manage.sh logs | grep ERROR

# Daily: Verify backups
ls -la ./backups/

# Monthly: Update dependencies
docker-compose build --no-cache
```

### Updates

```bash
# Update services
git pull origin main
docker-compose build
docker-compose up -d

# Zero-downtime update
docker-compose up -d --no-deps --build mcp-server
```

## Monitoring Integration

### Prometheus Metrics

```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./DockerConfig/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
```

### Grafana Dashboard

```yaml
# Add to docker-compose.yml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Disaster Recovery

### Recovery Plan

1. **Database Failure**
   - Restore from latest backup
   - Verify data integrity
   - Resume operations

2. **Service Failure**
   - Health checks trigger auto-restart
   - Manual intervention if needed
   - Check logs for root cause

3. **Complete System Failure**
   - Restore from infrastructure as code
   - Restore data from backups
   - Verify all services operational

## Support

For issues or questions:
- Check logs: `./scripts/docker-manage.sh logs`
- Health status: `./scripts/docker-manage.sh health`
- Documentation: `/docs` directory
- GitHub Issues: Report bugs or request features