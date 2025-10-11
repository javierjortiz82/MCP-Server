# Health Monitoring Guide - Lab01-MCP

## Overview

Lab01-MCP includes comprehensive health monitoring for all services, providing real-time insights into system health, performance, and availability.

## Architecture

```
┌─────────────────────────────────────────┐
│           Health Monitoring              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │MCP Server│  │  Client  │  │ Agent  ││
│  │ /health  │  │  Health  │  │/health ││
│  └────┬─────┘  └────┬─────┘  └───┬────┘│
│       │             │             │     │
│  ┌────▼─────────────▼─────────────▼────┐│
│  │     Component Health Checks          ││
│  ├──────────────────────────────────────┤│
│  │ • Database Connectivity              ││
│  │ • Redis Cache Status                 ││
│  │ • External API Availability          ││
│  │ • System Resources (CPU/Memory)      ││
│  │ • Service Metrics                    ││
│  └──────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

## Health Check Components

### 1. MCP Server Health (`/health`)

The MCP server provides comprehensive health monitoring through multiple endpoints:

#### Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/health` | Full health status | Detailed component status |
| `/health/live` | Kubernetes liveness probe | Simple alive check |
| `/health/ready` | Kubernetes readiness probe | Service ready status |
| `/health/startup` | Kubernetes startup probe | Initial startup check |

#### Components Monitored

1. **PostgreSQL Database**
   - Connection availability
   - Query execution time
   - Table existence verification
   - Database size monitoring

2. **Redis Cache** (if enabled)
   - Connection status
   - Memory usage
   - Response time

3. **MCP Tools**
   - Tool registration status
   - Tool availability count

4. **System Resources**
   - CPU utilization
   - Memory usage
   - Disk space

5. **External APIs**
   - Google Gemini API reachability
   - Network connectivity

#### Health Status Levels

- **HEALTHY** ✅: All components functioning normally
- **DEGRADED** ⚠️: Some non-critical issues detected
- **UNHEALTHY** ❌: Critical components failing

#### Example Response

```json
{
  "status": "healthy",
  "timestamp": "2025-01-06T12:00:00Z",
  "uptime_seconds": 3600,
  "components": [
    {
      "name": "postgresql",
      "status": "healthy",
      "response_time_ms": 12.5,
      "message": "Connected successfully, 15 tables found",
      "details": {
        "tables_count": 15,
        "database_size_mb": 45.2,
        "host": "postgres",
        "port": 5432
      }
    },
    {
      "name": "redis",
      "status": "healthy",
      "response_time_ms": 2.1,
      "message": "Redis connected and responsive",
      "details": {
        "memory_used_mb": 12.3
      }
    },
    {
      "name": "system_resources",
      "status": "healthy",
      "response_time_ms": 0.5,
      "message": "System resources normal",
      "details": {
        "cpu_percent": 35.2,
        "memory_percent": 62.1,
        "disk_percent": 45.0
      }
    }
  ],
  "metrics": {
    "total_checks": 5,
    "healthy_components": 5,
    "degraded_components": 0,
    "unhealthy_components": 0,
    "average_response_time_ms": 8.3
  }
}
```

### 2. Client Health Monitoring

The Odiseo Bot client includes integrated health monitoring:

#### Health Commands

During an interactive session, use these commands:

| Command | Description |
|---------|-------------|
| `/health` | Show full health status |
| `/health-json` | Health status as JSON |
| `/health-bot` | Bot status only |
| `/health-mcp` | MCP connectivity only |
| `/health-help` | Show help for health commands |

#### CLI Health Check

```bash
# Run health check from command line
python client_mcp/health_check.py

# Output as JSON
python client_mcp/health_check.py --format json

# Check specific component
python client_mcp/health_check.py --component mcp

# Exit with error code if unhealthy
python client_mcp/health_check.py --exit-code
```

#### Components Monitored

1. **Bot Status**
   - Initialization state
   - Activity monitoring
   - Message/error counts
   - Uptime tracking

2. **MCP Connectivity**
   - Connection status
   - Available tools count
   - Host/port configuration

3. **Gemini API**
   - API key configuration
   - Client initialization

4. **System Resources**
   - Process CPU usage
   - Process memory consumption
   - Python version

### 3. Agent Service Health (`/health`)

The Gemini Agent service provides health endpoints:

#### Components Monitored

1. **API Key Status**
   - Configuration check
   - Placeholder detection

2. **Service Metrics**
   - Request count
   - Error rate
   - Uptime

3. **System Resources**
   - CPU usage
   - Memory consumption

## Docker Health Checks

### Container Health Configuration

Each service in `docker-compose.yml` includes health checks:

```yaml
services:
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mcp_user -d mcp_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  mcp-server:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      postgres:
        condition: service_healthy

  client-mcp:
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Health Status in Docker

```bash
# Check container health status
docker ps --format "table {{.Names}}\t{{.Status}}"

# View health check logs
docker inspect lab01_mcp_server | jq '.[0].State.Health'

# Monitor health in real-time
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

## Integration with Monitoring Tools

### Prometheus Metrics

Configure Prometheus to scrape health endpoints:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-server'
    static_configs:
      - targets: ['mcp-server:3000']
    metrics_path: '/health'
    scrape_interval: 30s
```

### Grafana Dashboard

Create dashboards to visualize:
- Component health status over time
- Response times
- Resource utilization
- Error rates

### AlertManager Rules

```yaml
# alert-rules.yml
groups:
  - name: health
    rules:
      - alert: ServiceUnhealthy
        expr: health_status != 1
        for: 5m
        annotations:
          summary: "Service {{ $labels.service }} is unhealthy"

      - alert: HighErrorRate
        expr: error_rate > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: database_health != 1
        for: 2m
        annotations:
          summary: "Database connection lost"
```

## Usage Patterns

### 1. Development Monitoring

```bash
# Start with health monitoring
./scripts/docker-manage.sh start-dev

# Monitor health
./scripts/docker-manage.sh health

# Check specific service
docker exec lab01_mcp_server curl localhost:3000/health
```

### 2. Production Monitoring

```bash
# Kubernetes deployment
kubectl apply -f k8s/deployment.yaml

# Check pod health
kubectl get pods -o wide
kubectl describe pod mcp-server-xxx

# View health logs
kubectl logs mcp-server-xxx | grep health
```

### 3. Automated Testing

```python
# test_health_integration.py
import requests
import time

def test_service_health():
    """Test that service becomes healthy within timeout."""
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:3000/health")
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "healthy"
                return
        except:
            pass
        time.sleep(2)

    raise TimeoutError("Service did not become healthy")
```

## Troubleshooting

### Common Issues

#### 1. Database Health Check Failing

**Symptoms:**
```json
{
  "name": "postgresql",
  "status": "unhealthy",
  "message": "Database error: connection refused"
}
```

**Solutions:**
- Check database container is running: `docker ps`
- Verify credentials in `.env`
- Check network connectivity: `docker exec mcp-server ping postgres`
- Review database logs: `docker logs lab01_postgres`

#### 2. High Resource Usage

**Symptoms:**
```json
{
  "name": "system_resources",
  "status": "degraded",
  "message": "High resource usage",
  "details": {
    "cpu_percent": 85.0,
    "memory_percent": 92.0
  }
}
```

**Solutions:**
- Increase resource limits in `docker-compose.yml`
- Scale horizontally: `docker-compose up -d --scale mcp-server=3`
- Optimize queries and caching
- Check for memory leaks

#### 3. MCP Tools Unavailable

**Symptoms:**
```json
{
  "name": "mcp_tools",
  "status": "degraded",
  "message": "No tools registered"
}
```

**Solutions:**
- Check tool registration on startup
- Verify database migrations completed
- Review MCP server logs for errors
- Manually register tools if needed

### Health Check Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up

# Test individual components
# Database
docker exec lab01_postgres pg_isready

# Redis
docker exec lab01_redis redis-cli ping

# MCP Server
curl -v http://localhost:3000/health

# Check from inside container
docker exec -it lab01_mcp_server /bin/bash
curl localhost:3000/health/ready
```

## Best Practices

### 1. Health Check Design

- **Fast Response**: Health checks should complete within 1-2 seconds
- **Cached Results**: Cache expensive checks for 30-60 seconds
- **Graceful Degradation**: Don't fail on non-critical components
- **Detailed Logging**: Log all health check failures
- **Metrics Collection**: Track health check performance

### 2. Alert Configuration

- **Avoid Flapping**: Use appropriate thresholds and delays
- **Severity Levels**: Different alerts for degraded vs unhealthy
- **Actionable Alerts**: Include remediation steps
- **Alert Routing**: Send to appropriate teams/channels

### 3. Monitoring Strategy

```yaml
# Monitoring matrix
Components:
  Critical (Page immediately):
    - Database down
    - All API endpoints failing
    - Out of memory

  Important (Alert team):
    - High error rate (>5%)
    - Degraded performance
    - Cache unavailable

  Informational (Log only):
    - Individual tool failures
    - Temporary network issues
    - Non-critical API timeouts
```

## Performance Impact

Health checks are designed to have minimal performance impact:

| Check Type | Frequency | Avg. Duration | CPU Impact | Memory Impact |
|------------|-----------|---------------|------------|---------------|
| Liveness | 30s | <100ms | <0.1% | <1MB |
| Readiness | 30s | <500ms | <0.5% | <2MB |
| Full Health | 60s | <1000ms | <1% | <5MB |

## Security Considerations

### 1. Information Disclosure

Health endpoints may reveal sensitive information:

- **Public Endpoints**: Only show basic status
- **Authenticated Endpoints**: Include detailed diagnostics
- **Internal Only**: Full system information

### 2. Rate Limiting

Protect health endpoints from abuse:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/health")
@limiter.limit("10/minute")
async def health():
    return await get_health_status()
```

### 3. Access Control

```nginx
# nginx.conf
location /health {
    # Basic health - public
    proxy_pass http://mcp_backend/health/live;
}

location /health/detailed {
    # Detailed health - internal only
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://mcp_backend/health;
}
```

## Summary

The health monitoring system provides:

- ✅ **Comprehensive Coverage**: All components monitored
- ✅ **Multiple Granularities**: From simple liveness to detailed diagnostics
- ✅ **Kubernetes Ready**: Compatible with K8s probes
- ✅ **Low Overhead**: Minimal performance impact
- ✅ **Actionable Insights**: Clear status and remediation guidance
- ✅ **Integration Ready**: Works with standard monitoring tools

Use health checks to:
- Ensure service reliability
- Detect issues early
- Automate recovery
- Maintain SLAs
- Debug problems quickly