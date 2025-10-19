# Lab01-MCP Database Deployment

Complete database setup for Lab01-MCP with simplified deployment process.

## Quick Start

```bash
cd SQL/

# Configure schema name (optional - defaults to 'test')
vi .env  # Edit SCHEMA_NAME=test to desired value

# Deploy
./scripts/deploy.sh                    # Full deployment + verification
./scripts/verify.sh                    # Health checks
./scripts/verify.sh --quick            # Quick check only
./scripts/verify.sh --detailed         # Detailed diagnostics
```

### Schema Configuration

The schema name is **dynamically configurable** from the `.env` file:

```bash
# Default configuration
SCHEMA_NAME=test

# Alternative configurations
SCHEMA_NAME=dev          # Development
SCHEMA_NAME=staging      # Staging environment
SCHEMA_NAME=prod         # Production
SCHEMA_NAME=custom       # Custom schema name
```

**Important**: All SQL scripts automatically use the `SCHEMA_NAME` variable:
- Shell scripts load `.env` at startup
- `psql` receives schema name via `-v SCHEMA_NAME=...` flag
- SQL files reference it as `:SCHEMA_NAME` variable
- PostgreSQL substitutes the actual value at runtime

## Overview

| Component | Files | Purpose |
|-----------|-------|---------|
| **DDL** | 01_ddl/ (14 files) | Table definitions with inline indexes |
| **Indexes** | 03_indexes/01_indexes.sql | Consolidated indexes (60+) |
| **Functions** | 02_functions/ (4 files) | Business logic and triggers |
| **Seed Data** | 04_seed/01_products_data.sql | 90 products |
| **Orchestration** | 05_orchestration/ (2 files) | Deployment and validation |
| **External Data** | data/ (4 JSON files) | Reference data |
| **Deployment** | scripts/deploy.sh | Master orchestrator |
| **Verification** | scripts/verify.sh | Health checks |

## Architecture

### Deployment Flow

```
deploy.sh (scripts/)
  └─ Prerequisites check
     └─ 05_orchestration/01_deploy.sql (10 phases)
        ├─ Extensions & Schema
        ├─ 14 Tables with DDL
        ├─ Consolidated Indexes
        ├─ Functions & Triggers
        └─ Seed Data (90 products)
     └─ 05_orchestration/02_validate_deployment.sql (comprehensive checks)
     └─ scripts/verify.sh (health checks)
```

### Database Schema

```
Schema: [Configured from .env SCHEMA_NAME variable]
Default: test
Alternatives: dev, staging, prod, or custom

Tables (14):
├─ products (main catalog with embeddings)
├─ appointments, service_types, business_hours, blocked_times, service_hours
├─ email_queue
├─ conversation_sessions, conversation_messages, agent_memory_blocks
├─ user_memory_profiles, user_memory_blocks, agent_context_transfers
└─ pagination_contexts

Indexes (60+):
├─ B-tree (standard lookups)
├─ GIN Trigram (fuzzy search)
└─ IVFFlat (vector similarity)

Functions (30+):
├─ is_slot_available() - Booking availability
├─ create_email_task() - Async email queue
├─ store_agent_memory() - Context persistence
└─ archive_old_sessions() - Lifecycle management
```

## Deployment Scripts

### deploy.sh

Main deployment script with complete workflow:

```bash
./scripts/deploy.sh                    # Full deployment + verification
./scripts/deploy.sh --no-verify        # Deploy without verification
./scripts/deploy.sh --validate-only    # Validate existing database
./scripts/deploy.sh --help             # Show help
```

**Features:**
- Prerequisites validation
- Complete DDL/DML deployment
- Comprehensive validation
- Health checks
- Detailed logging

**Exit codes:**
- 0: Success
- 1: Failure

### verify.sh

Health check and diagnostics:

```bash
./scripts/verify.sh                    # Full verification (9 checks)
./scripts/verify.sh --quick            # Quick checks (5 checks)
./scripts/verify.sh --detailed         # Detailed report + diagnostics
./scripts/verify.sh --help             # Show help
```

**Checks:**
- Container status
- Database connectivity
- Schema and tables
- Products data (90 records)
- AI embeddings
- Indexes (60+)
- Functions (30+)
- Fuzzy search capability
- Vector search capability

## Project Structure

```
SQL/
├── 00_init/                    # Initialization (extensions, schema, permissions)
│   ├── 01_extensions.sql       # UUID, unaccent, pg_trgm, vector
│   ├── 02_schema.sql           # Schema 'test' creation
│   └── 03_users_permissions.sql # mcp_user permissions
│
├── 01_ddl/                     # Table definitions (14 tables)
│   ├── 01_products.sql         # Product catalog
│   ├── bookings/               # Appointment system
│   │   ├── 01_appointments.sql
│   │   ├── 02_service_types.sql
│   │   ├── 03_business_hours.sql
│   │   ├── 04_blocked_times.sql
│   │   └── 05_service_hours.sql
│   ├── email/                  # Email queue system
│   │   └── 01_email_queue.sql
│   ├── memory/                 # Multi-agent memory
│   │   ├── 01_conversation.sql
│   │   ├── 02_agent_memory.sql
│   │   └── 03_user_memory.sql
│   └── utils/                  # Utilities
│       └── 01_pagination_contexts.sql
│
├── 02_functions/               # Business logic (4 modules)
│   ├── 01_bookings.sql         # Availability, scheduling
│   ├── 02_email.sql            # Email queue management
│   ├── 03_memory.sql           # Memory persistence
│   └── 04_lifecycle.sql        # Data archiving, TTL
│
├── 03_indexes.sql              # Consolidated indexes (60+)
│   └── Organized by table:
│       ├─ Products (10+ indexes: text search, embedding, trigram)
│       ├─ Appointments (6 indexes: date, status, availability)
│       ├─ Email Queue (6 indexes: worker poll, retry, status)
│       ├─ Conversation (13 indexes: sessions, messages)
│       ├─ Memory (14 indexes: agents, users, blocks)
│       ├─ Utilities (11 indexes: pagination, context)
│       └─ Business Hours (4 indexes: service lookup)
│
├── 04_seed/                    # Seed data (DML)
│   └── 01_products_data.sql    # 90 products
│
├── data/                       # External data (JSON reference)
│   ├── 01_products.json        # Product catalog (26 KB)
│   ├── 02_service_types.json   # Services (1.2 KB)
│   ├── 03_business_hours.json  # Hours (525 B)
│   └── 04_blocked_times.json   # Blocked times (3 KB)
│
├── 05_orchestration/
│   ├── 01_deploy.sql           # Master orchestrator (10 phases)
│   └── 02_validate_deployment.sql # Comprehensive validation
│
├── README.md                   # This file
└── QUICK_START.txt             # Quick start guide
```

## Key Improvements

### Before
- 3 separate scripts (deploy.sql, validate.sql, verify.sh)
- Indexes scattered across 14 DDL files
- Empty 03_indexes/ directory
- Complex execution workflow
- Unclear single entry point

### After
- **2 shell scripts** (deploy.sh, verify.sh)
- **Orchestration directory** (05_orchestration/)
- **Consolidated indexes** in 03_indexes.sql
- **Single entry point**: `./deploy.sh`
- **Simplified workflow**
- **Clear, modular structure**

## Deployment Workflow

### 1. Prerequisites Check
```bash
✓ Docker installed
✓ Container 'mcp-postgres' running
✓ Database connectivity
✓ All SQL files present
```

### 2. Database Deployment (10 phases)
```
[1/10] Extensions (uuid-ossp, unaccent, pg_trgm, vector)
[2/10] Schema and permissions
[3/10] Products table
[4/10] Bookings system (5 tables)
[5/10] Email queue
[6/10] Memory system (3 tables)
[7/10] Utilities
[8/10] Consolidated indexes
[9/10] Functions and triggers
[10/10] Seed data (90 products)
```

### 3. Validation
Comprehensive checks covering:
- DDL structure (14 tables, 60+ indexes)
- Functions (30+)
- Seed data (90 products)
- Extensions (4 required)
- Triggers and constraints

### 4. Verification
Health checks:
- Container status
- Database connectivity
- Data integrity
- Search capabilities

## Usage Examples

### Complete Deployment
```bash
cd /path/to/Lab01-MCP/SQL
./deploy.sh
```

Output:
```
✅ Prerequisites check passed
✅ Deployment completed successfully
✅ All 90 products loaded
✅ All 90 embeddings ready
✅ All health checks passed
```

### Quick Health Check
```bash
./verify.sh --quick
```

Output:
```
✅ Container running
✅ Connection successful
✅ Schema exists
✅ Found 14 tables (expected 14+)
✅ All 90 products loaded
✅ All 90 embeddings ready
```

### Detailed Diagnostics
```bash
./verify.sh --detailed
```

Output:
```
📊 Container Information
📋 Schema Objects (14 tables, 60+ indexes, 30+ functions)
📦 Data Status (90 products, 90 embeddings)
🔍 Search Capabilities (Fuzzy search working, Vector search available)
```

## Troubleshooting

### Issue: Container not running
```bash
cd ../DockerConfig
docker-compose up -d
```

### Issue: Deployment failed
```bash
./deploy.sh --validate-only   # Check existing database
./verify.sh --detailed        # Get diagnostics
```

### Issue: Products not loaded
Check seed data:
```bash
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT COUNT(*) FROM test.products;"
```

## Configuration

Environment variables (if needed):
```bash
export DATABASE_URL="postgresql://mcp_user:password@localhost:5434/mcpdb"
export SCHEMA_NAME="test"
```

Database connection:
- Host: localhost
- Port: 5434 (external) / 5432 (internal)
- Database: mcpdb
- User: mcp_user
- Schema: test

## Performance

| Operation | Time |
|-----------|------|
| Full deployment | 2-3 minutes |
| Validation | 30-45 seconds |
| Health checks | 5-10 seconds |
| Schema verification | <1 second |
| Indexes creation | 30-45 seconds |
| Seed data load | 45-60 seconds |

## Environment Variables and Schema Configuration

### How SCHEMA_NAME Works

The deployment system uses a **dynamic schema name** loaded from `.env`:

#### 1. Shell Script Level (deploy.sh, verify.sh)
```bash
# Scripts load .env at startup
ENV_FILE="$SQL_ROOT_DIR/.env"
source "$ENV_FILE"

# Set default if not provided
SCHEMA_NAME="${SCHEMA_NAME:-test}"

# Pass to psql with -v flag
docker exec mcp-postgres psql -U mcp_user -d mcpdb \
  -v "SCHEMA_NAME=$SCHEMA_NAME" -f "$DEPLOY_SQL"
```

#### 2. SQL Level (05_orchestration/01_deploy.sql, 02_validate_deployment.sql, DDL files)
```sql
-- Variables referenced as :SCHEMA_NAME in SQL
CREATE SCHEMA IF NOT EXISTS :SCHEMA_NAME;
CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.products (...);

-- For quoted values (WHERE clauses)
WHERE schemaname = :'SCHEMA_NAME'
WHERE table_schema = :'SCHEMA_NAME'
```

#### 3. Python Level (populate.py, for data loading)
```python
# Python script reads .env independently
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")

# Uses in SQL string construction
sql = f"INSERT INTO {SCHEMA_NAME}.{table_name} ..."
```

### Multi-Environment Usage

Deploy to different environments with different schema names:

```bash
# Development
vi .env  # Set SCHEMA_NAME=dev
./scripts/deploy.sh  # Creates 'dev' schema

# Staging
vi .env  # Set SCHEMA_NAME=staging
./scripts/deploy.sh  # Creates 'staging' schema

# Production
vi .env  # Set SCHEMA_NAME=prod
./scripts/deploy.sh  # Creates 'prod' schema

# Verify multiple schemas exist
docker exec mcp-postgres psql -U mcp_user -d mcpdb \
  -c "SELECT schemaname FROM pg_namespace WHERE schemaname NOT LIKE 'pg_%';"
```

### Switching Between Schemas

```bash
# List all available schemas
docker exec mcp-postgres psql -U mcp_user -d mcpdb \
  -c "SELECT schemaname FROM pg_namespace;"

# Connect to specific schema
docker exec -it mcp-postgres psql -U mcp_user -d mcpdb \
  -c "SET search_path TO prod, public; SELECT COUNT(*) FROM products;"

# Or use schema-qualified table name
docker exec mcp-postgres psql -U mcp_user -d mcpdb \
  -c "SELECT COUNT(*) FROM prod.products;"
```

## Support

For issues or questions:
1. Check `/home/javort/Lab01-MCP/docs/NOTAS_CLAUDE.md`
2. Run `./scripts/verify.sh --detailed`
3. Review logs in deployment output
4. Verify SCHEMA_NAME setting: `cat .env | grep SCHEMA_NAME`

---

**Version:** 2.0 (Simplified Deployment)  
**Created:** 2025-10-18  
**Updated:** 2025-10-18  

