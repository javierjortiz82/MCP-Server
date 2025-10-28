# Lab01-MCP Environment Validation Guide

## Quick Start

### Before Starting Docker
```bash
# Recommended: Validate and start safely
make docker-start-safe

# Or validate first, then start manually
make validate
make docker-start
```

### For CI/CD Pipelines
```bash
# Strict validation (fail on warnings)
make validate-strict
```

### For Developers
```bash
# Full validation with detailed output
make validate

# Quick check (minimal output)
make validate-quiet

# Check Pydantic field mappings
make validate-pydantic
```

---

## What Gets Validated

### 1. Docker Infrastructure
- ✓ Docker is installed
- ✓ docker-compose is installed
- ✓ Docker daemon is running
- ✓ docker-compose.yml exists and has valid YAML syntax

### 2. Directory Structure
- ✓ All 8 required directories exist:
  - `mcp_server/`, `client_mcp/`, `agent/`, `email_service/`
  - `DockerConfig/`, `SQL/`, `scripts/`, `docs/`

### 3. Environment Files
- ✓ All `.env` files exist and are readable:
  - `.env` (root)
  - `mcp_server/.env`
  - `client_mcp/.env`
  - `agent/.env`
  - `DockerConfig/.env`
  - `SQL/.env`

### 4. Critical Variables
- ✓ `GOOGLE_API_KEY` is configured (not placeholder)
- ✓ `DATABASE_URL` is configured (not placeholder)
- ✓ `SCHEMA_NAME` is configured
- ✓ Service-specific critical variables present

### 5. Variable Formats
- ✓ `DATABASE_URL` matches pattern: `postgresql://user:pass@host:port/db`
- ✓ `GOOGLE_API_KEY` format is valid
- ✓ Port numbers are in valid range (1-65535)

### 6. Cross-References
- ✓ Database port in `DATABASE_URL` matches `POSTGRES_PORT`
- ✓ No port conflicts between services
- ✓ All services use same `DATABASE_URL`

### 7. Service Configuration
Validates each service has required variables:
- **PostgreSQL**: DATABASE_URL, SCHEMA_NAME
- **MCP Server**: GOOGLE_API_KEY, EMBEDDING_MODEL, DATABASE_URL
- **Email Service**: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, DATABASE_URL
- **Agent**: GOOGLE_API_KEY
- **Client**: GOOGLE_API_KEY, DATABASE_URL

### 8. Pydantic v2 Mapping
- ✓ mcp_server: 42 fields mapped
- ✓ client_mcp: 52 fields mapped
- ✓ agent: 21 fields mapped
- ✓ email_service: 18+ fields mapped

---

## Output Modes

### Normal Mode (Default)
Shows detailed validation results with colors:
- 🟢 Green checks (✓) = Passed
- 🟡 Yellow warnings (⚠) = Non-blocking issues
- 🔴 Red errors (✗) = Blocking issues

```bash
make validate
```

### Quiet Mode
Minimal output (summary only):
```bash
make validate-quiet
```

### Strict Mode
Treats warnings as errors (for CI/CD):
```bash
make validate-strict
```

### JSON Mode
Machine-readable output for automation:
```bash
python3 scripts/validate_environment.py --json > validation.json
```

---

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All validations passed | ✅ Safe to deploy |
| 1 | Warnings found | ⚠️ Review and proceed with caution |
| 2 | Errors found | ❌ Fix issues before deploying |

---

## Common Issues & Solutions

### Issue: "DATABASE_URL is missing"
**Solution**: Check `.env` file exists and contains DATABASE_URL:
```bash
grep DATABASE_URL .env
```

### Issue: "GOOGLE_API_KEY is missing"
**Solution**: Add your Google API key to `.env`:
```bash
echo "GOOGLE_API_KEY=your-api-key-here" >> .env
```

### Issue: "Port 5434 is already in use"
**Solution**: Change port in `.env`:
```bash
sed -i 's/POSTGRES_PORT=5434/POSTGRES_PORT=5433/g' .env
```

### Issue: "Pydantic field mapping failed"
**Solution**: Check that all service settings files exist:
```bash
ls -la mcp_server/config/settings.py
ls -la client_mcp/config/settings.py
ls -la agent/src/gemini_agent/config/settings.py
```

---

## Variable Source Mapping

The validator shows you where each variable comes from:

```
DATABASE_URL      | root    | postgres, mcp-server, email-worker
GOOGLE_API_KEY    | root    | mcp-server, agent
SMTP_PASSWORD     | docker  | email-worker
MCP_PORT          | root    | mcp-server
```

This helps you understand:
- Where to edit each variable (which `.env` file)
- Which services depend on it
- If a service is missing a required variable

---

## For New Developers

1. **First time setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   make validate    # Check configuration
   ```

2. **Before starting work**:
   ```bash
   make validate-quiet    # Quick health check
   ```

3. **Before deploying**:
   ```bash
   make docker-start-safe    # Validate + start Docker safely
   ```

---

## For DevOps/SRE

### Pre-deployment checks
```bash
#!/bin/bash
# In deployment script

# Validate environment
make validate-strict || exit 1

# Start Docker safely
make docker-start

# Monitor logs
make docker-logs
```

### CI/CD Integration
```yaml
# Example GitHub Actions
- name: Validate Lab01-MCP Environment
  run: make validate-strict
```

---

## For Security Teams

The validator checks:
- ✓ No placeholder/default values in critical variables
- ✓ Database URL format is correct
- ✓ API keys are configured (not empty)
- ✓ Port numbers are reasonable
- ✓ No exposed secrets in logs

---

## Tips & Tricks

### Check only Docker configuration
```bash
python3 scripts/validate_environment.py | grep -A 5 "\[Docker\]"
```

### Check only database configuration
```bash
python3 scripts/validate_environment.py | grep -A 5 "DATABASE"
```

### See all detected variables
```bash
python3 scripts/validate_environment.py | tail -20
```

### Generate a validation report
```bash
make validate > validation_report.txt
cat validation_report.txt
```

---

## Advanced Usage

### Run without color codes (for logs)
```bash
python3 scripts/validate_environment.py --quiet > validation.log
```

### Check Pydantic field count
```bash
make validate-pydantic
```

### Validate specific service
```bash
python3 scripts/validate_environment.py | grep "email_service"
```

---

## Troubleshooting

If validation fails, check:

1. **Are .env files present?**
   ```bash
   ls -la .env*
   ```

2. **Is Docker running?**
   ```bash
   docker ps
   ```

3. **Are all required directories present?**
   ```bash
   ls -d mcp_server client_mcp agent email_service DockerConfig SQL scripts docs
   ```

4. **Are Pydantic files present?**
   ```bash
   find . -name "settings.py" | head -10
   ```

---

## Support

For detailed information, see: `docs/NOTAS_CLAUDE.md`

For help with specific validators:
```bash
python3 scripts/validate_environment.py --help
python3 scripts/validate_pydantic_mapping.py --help
```

---

Last updated: 2025-10-27
