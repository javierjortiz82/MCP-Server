# Environment Configuration Guide

This document explains how to configure environment variables for Lab01-MCP after cloning the repository.

> **Note**: There is NO `.env.example` at the project root. Each microservice has its own `.env.example` template in its directory.

## Architecture Overview

```
📁 Lab01-MCP/
├── 📁 DockerConfig/
│   ├── .env.example              ← Infrastructure (PostgreSQL, pgAdmin)
│   └── docker-compose.yml        ← Uses each service's .env
│
├── 📁 mcp_server/
│   ├── .env.example              ← MCP Server configuration
│   ├── config/settings.py        ← Loads from .env
│   └── ...
│
├── 📁 email_service/
│   ├── .env.example              ← Email service configuration
│   └── ...
│
├── 📁 agent/
│   ├── .env.example              ← Agent configuration
│   └── ...
│
├── 📁 client_mcp/
│   ├── .env.example              ← Client configuration
│   └── ...
│
├── 📁 SQL/
│   ├── .env.example              ← Database scripts configuration
│   └── src/populate.py           ← Loads from SQL/.env
│
└── 📁 scripts/
    ├── deploy.sh                 ← Checks all microservice .env files
    └── docker-manage.sh          ← Checks DockerConfig/.env
```

## Using Makefile Commands (Recommended)

### Create Environment Files Automatically

Instead of manually copying files, use the Makefile:

```bash
# Create all .env files from templates
$ make setup-env

# Check if all .env files exist
$ make env-check
```

**Output of `make env-check`:**
```
✓ DockerConfig/.env     - Found
✓ mcp_server/.env       - Found
✓ email_service/.env    - Found
✓ agent/.env            - Found
✓ client_mcp/.env       - Found
✓ SQL/.env              - Found

✓ All .env files are present!

Next steps:
  1. Edit .env files with your credentials:
     - DockerConfig/.env: POSTGRES_PASSWORD, PGADMIN_PASSWORD
     - mcp_server/.env: GOOGLE_API_KEY, DATABASE_URL
     - email_service/.env: GOOGLE_API_KEY, SMTP_*

  2. Validate configuration:
     make validate

  3. Start Docker:
     make docker-start-safe (or make docker-start)
```

---

## Setup Instructions

### Option A: Docker Deployment (Recommended)

#### Step 1: Create All .env Files

Use the automated Makefile command:

```bash
make setup-env          # Creates all .env files from templates
make env-check          # Verify all files were created
```

Or manually:

```bash
cd DockerConfig
cp .env.example .env

cd ../mcp_server
cp .env.example .env

cd ../email_service
cp .env.example .env

cd ../agent
cp .env.example .env

cd ../client_mcp
cp .env.example .env
```

#### Step 2: Edit Configuration Files

Now edit each `.env` file with your credentials:

**DockerConfig/.env:**
```bash
POSTGRES_PASSWORD=your-strong-password-here  # ⚠️ Change this!
POSTGRES_PORT=5434                           # Optional: change if needed
PGADMIN_PASSWORD=your-pgadmin-password       # ⚠️ Change this!
```

**mcp_server/.env:**
```bash
GOOGLE_API_KEY=AIzaSy...                     # Your Google API Key
DATABASE_URL=postgresql://mcp_user:password@postgres:5432/mcpdb
SCHEMA_NAME=test
```

**email_service/.env:**
```bash
GOOGLE_API_KEY=AIzaSy...                     # Your Google API Key
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password              # Gmail App Password (not regular password)
```

#### Step 3: Start Docker Services

```bash
cd DockerConfig
docker-compose up -d
```

Docker automatically:
- Loads `DockerConfig/.env` for infrastructure variables
- Loads each service's `.env` from their respective directories (via `env_file` directives)
- Starts PostgreSQL, pgAdmin, mcp-server, email-worker, and other services

#### Step 4: Initialize Database

```bash
cd ../SQL
cp .env.example .env
# Edit .env: Ensure DATABASE_URL and GOOGLE_API_KEY match mcp_server/.env

make db                 # or: ./scripts/deploy.sh, or: ./src/populate.sh
```

### Option B: Local Development (Without Docker)

#### Step 1: Create All .env Files

```bash
make setup-env          # Creates all .env files from templates
make env-check          # Verify all files were created
```

#### Step 2: Edit Configuration Files

Edit each service's `.env` with your local settings:

```bash
# MCP Server
nano mcp_server/.env
# Set: GOOGLE_API_KEY, DATABASE_URL (use local PostgreSQL)

# Email Service
nano email_service/.env
# Set: GOOGLE_API_KEY, SMTP_*

# Agent (optional)
nano agent/.env

# Client (optional)
nano client_mcp/.env
```

#### Step 3: Set Up Database

For local PostgreSQL:

```bash
cd SQL
cp .env.example .env
# Edit .env with your local PostgreSQL credentials
# Example: DATABASE_URL=postgresql://postgres:password@localhost:5432/mcpdb

make db                 # or: ./src/populate.sh
```

#### Step 4: Run Services Individually

Each service loads from its own `.env`:

```bash
# Terminal 1: MCP Server
cd mcp_server
python -m uvicorn health:app --host 0.0.0.0 --port 8009

# Terminal 2: Agent (if using standalone)
cd agent
python -m uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 3: Client
cd client_mcp
python -m client_mcp

# Terminal 4: Email Service (if needed)
cd email_service
python -m email_service.worker
```

Or use the Makefile helper:

```bash
make dev                # Starts development environment interactively
```

---

## Environment Variables by Service

### All Services (Shared)

```env
GOOGLE_API_KEY=AIzaSy...              # Required: From https://aistudio.google.com/app/apikey
DATABASE_URL=postgresql://...         # Required: PostgreSQL connection string
SCHEMA_NAME=test                       # Schema name (default: test)
LOG_LEVEL=INFO                         # Logging level
DEBUG_MODE=false                       # Debug mode
```

### MCP Server (`mcp_server/.env`)

```env
GOOGLE_CALENDAR_ENABLED=true           # Google Calendar integration
GOOGLE_CALENDAR_ID=primary             # Calendar ID for bookings
GOOGLE_CALENDAR_TIMEZONE=America/Costa_Rica  # Timezone
EMBEDDING_MODEL=gemini-embedding-001   # Embedding model
BATCH_SIZE=8                           # Batch processing size
PGVECTOR_IVF_LISTS=100                 # Vector search optimization
```

### Email Service (`email_service/.env`)

```env
SMTP_HOST=smtp.gmail.com               # SMTP server
SMTP_PORT=587                          # SMTP port (usually 587 for TLS)
SMTP_USER=your-email@gmail.com         # SMTP username
SMTP_PASSWORD=your-app-password        # App password (not regular password!)
SMTP_FROM_EMAIL=noreply@lab01.com      # Sender email
SMTP_USE_TLS=true                      # Enable TLS
```

### Agent (`agent/.env`)

```env
MODEL=gemini-2.0-flash-exp             # Model selection
TEMPERATURE=0.3                        # Generation randomness
AGENT_PORT=8000                        # Service port
ENABLE_THINKING=true                   # Thinking mode (Gemini 2.5+)
```

### Client (`client_mcp/.env`)

```env
MCP_HOST=localhost                     # MCP server host
MCP_PORT=8009                          # MCP server port
PAGINATION_PAGE_SIZE=4                 # Items per page
ENABLE_CACHE=true                      # Tool result caching
CACHE_TTL_SECONDS=300                  # Cache duration
```

### Docker Infrastructure (`DockerConfig/.env`)

```env
POSTGRES_DB=mcpdb                      # Database name
POSTGRES_USER=mcp_user                 # Database user
POSTGRES_PASSWORD=change-me            # ⚠️ CHANGE THIS
POSTGRES_PORT=5434                     # Database port (host side)
PGADMIN_EMAIL=admin@example.com        # pgAdmin email
PGADMIN_PASSWORD=change-me             # ⚠️ CHANGE THIS
PGADMIN_PORT=8090                      # pgAdmin port
```

---

## Where to Get Credentials

### Google API Key

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the generated key
4. Paste into `.env` files

### Gmail SMTP Password (Not Your Regular Password!)

**For Gmail:**
1. Enable 2FA: https://myaccount.google.com/security
2. Go to App Passwords: https://myaccount.google.com/apppasswords
3. Select "Mail" and your OS (Windows/Mac/Linux)
4. Google generates a 16-character password
5. Use that password in `SMTP_PASSWORD`

**For Other Providers:**
- Consult your email provider's SMTP documentation
- Many use app-specific passwords or API keys

### Database Credentials

**For Docker:**
- Create strong passwords (16+ chars with uppercase, numbers, symbols)
- PostgreSQL: `POSTGRES_PASSWORD`
- pgAdmin: `PGADMIN_PASSWORD`

**For Local PostgreSQL:**
- Use your existing PostgreSQL credentials
- Example: `DATABASE_URL=postgresql://postgres:password@localhost:5432/mcpdb`

---

## Validation & Troubleshooting

### Validate Configuration

```bash
# Full validation
make validate

# Strict mode (fail on warnings)
make validate-strict

# Quick check
make validate-quiet
```

### Common Issues

**Issue**: `FileNotFoundError: .env.example not found`
- **Solution**: Each service directory should have `.env.example`. Check that:
  - `mcp_server/.env.example` exists
  - `email_service/.env.example` exists
  - `DockerConfig/.env.example` exists

**Issue**: `Docker container exits immediately`
- **Solution**: Check that all required `GOOGLE_API_KEY` and database credentials are set in the service's `.env` file

**Issue**: `Database connection refused`
- **Solution**: Ensure `DATABASE_URL` in all services matches the PostgreSQL connection details

**Issue**: `SMTP authentication failed`
- **Solution**: For Gmail, make sure you're using an App Password (not your regular password)

---

## Security Best Practices

1. **Never commit `.env` files to Git**
   - They're already in `.gitignore`
   - Always use `.env.example` as template

2. **Use strong passwords**
   - Minimum 16 characters
   - Mix uppercase, lowercase, numbers, symbols
   - Example: `MySecure#Pass2025!`

3. **Rotate API keys regularly**
   - Especially in production
   - Keep Google API Key separate for each environment

4. **Use Docker secrets for production**
   - Don't hardcode credentials
   - Use Docker Secrets or environment variables from CI/CD

---

## Environment Files Checklist

### Before Running Docker

- [ ] `DockerConfig/.env` created from `DockerConfig/.env.example`
- [ ] `POSTGRES_PASSWORD` changed in `DockerConfig/.env`
- [ ] `PGADMIN_PASSWORD` changed in `DockerConfig/.env`
- [ ] `mcp_server/.env` created and configured
- [ ] `email_service/.env` created and configured
- [ ] `GOOGLE_API_KEY` added to all services
- [ ] `DATABASE_URL` updated for Docker (use `postgres:5432` not `localhost`)

### Before Running Local Services

- [ ] All `.env` files created from `.env.example`
- [ ] `GOOGLE_API_KEY` added
- [ ] `DATABASE_URL` points to local PostgreSQL
- [ ] `SMTP_*` credentials configured for email service
- [ ] Port numbers don't conflict

---

## Support

For questions or issues with environment setup:
- Check `DEPLOYMENT_GUIDE.md` for full deployment instructions
- Review `VALIDATION_GUIDE.md` for validation commands
- Check service-specific READMEs in each microservice directory
