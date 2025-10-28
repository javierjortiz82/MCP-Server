# Make DB Process - Complete Guide

**Document Purpose:** Comprehensive guide to the `make db` command, its execution flow, prerequisites, and validation.

**Last Updated:** 2025-10-28
**Status:** ✅ Fully tested and documented

---

## 📋 Overview

The `make db` command orchestrates a **complete database deployment** for Lab01-MCP:

```bash
make db
```

This single command executes **4 phases**:
1. **Phase 1:** DDL Deployment (schema, tables, indexes, functions)
2. **Phase 2:** DML Data Loading (with AI embeddings)
3. **Phase 3:** Validation (sanity checks)
4. **Phase 4:** Health Checks (connectivity tests)

**Total execution time:** 2-5 minutes (depending on API latency)

---

## ✅ Prerequisites

Before running `make db`, verify these requirements:

### 1. Docker Running

```bash
# Check Docker version
docker --version
# Output: Docker version 28.5.1 or higher ✅

# Check docker-compose
docker-compose --version
# Output: Docker Compose version v2.40.2 or higher ✅
```

### 2. PostgreSQL Container Running

```bash
# Check if mcp-postgres container exists and is running
docker ps | grep mcp-postgres

# Expected output:
# fcf92659d089   docker-config-postgres   ...   Up 29 minutes   0.0.0.0:5434->5432/tcp   mcp-postgres
```

**If not running, start Docker services:**
```bash
cd DockerConfig
docker-compose up -d
cd ..
```

### 3. Database Connectivity

```bash
# Test connection to database
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT version();"

# Expected: PostgreSQL 15.14 output ✅
```

### 4. Environment Files

```bash
# Verify SQL/.env exists with required variables
test -f SQL/.env && echo "✅ SQL/.env exists" || echo "❌ SQL/.env missing"

# Required variables in SQL/.env:
# - DATABASE_URL=postgresql://mcp_user:password@localhost:5434/mcpdb
# - GOOGLE_API_KEY=AIza... (for embeddings)
# - SCHEMA_NAME=test (default)
# - EMBEDDING_MODEL=gemini-embedding-001
# - BATCH_SIZE=8
```

### 5. Python Dependencies

```bash
# Check Python 3 is available
python3 --version
# Output: Python 3.8 or higher ✅

# Verify required packages installed
python3 -c "import psycopg2, dotenv, tenacity, pgvector, google.genai; print('✅ All dependencies available')"

# If missing, install:
pip3 install psycopg2-binary python-dotenv tenacity google-generativeai pgvector
```

### 6. SQL Files Present

```bash
# Verify deployment scripts exist
ls -lh SQL/scripts/deploy.sh SQL/scripts/verify.sh

# Verify SQL files exist
ls -lh SQL/05_orchestration/{01_deploy.sql,02_validate_deployment.sql}

# Verify data files exist (14 JSON files for seed data)
ls SQL/data/*.json | wc -l
# Expected: 14 files ✅
```

---

## 🔄 Execution Flow

### Phase 1: DDL Deployment

**File:** `SQL/scripts/deploy.sh` (line 186-241)
**Action:** Creates database schema, tables, indexes, and functions

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: DATABASE DEPLOYMENT (DDL)                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Copy SQL files to Docker container                       │
│ 2. Preprocess function files (replace :SCHEMA_NAME)         │
│ 3. Fix unaccent() function references                       │
│ 4. Execute 01_deploy.sql via psql                           │
│ 5. Clean up temporary files                                 │
└─────────────────────────────────────────────────────────────┘
```

**Output:**
- 1 schema (`test`)
- 14 tables
- 80+ indexes
- 31 functions (for bookings, emails, memory management)

**Prerequisites for Phase 1:**
- Docker container running ✅
- Database connectivity ✅
- SQL files in place ✅

### Phase 2: Data Loading with Embeddings

**File:** `SQL/scripts/deploy.sh` (line 247-306)
**Action:** Loads JSON seed data and generates AI embeddings

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: DATA LOADING (DML + EMBEDDINGS)                    │
├─────────────────────────────────────────────────────────────┤
│ 1. Verify Python dependencies                               │
│ 2. Load populate.py from SQL/src/                           │
│ 3. Load 14 JSON files from SQL/data/                        │
│ 4. Insert data into all tables                              │
│ 5. Generate embeddings for 90 products                      │
│    (calls Google Gemini API)                                │
│ 6. Store embeddings in pgvector format                      │
└─────────────────────────────────────────────────────────────┘
```

**Data Loaded:**
- **Products:** 90 items with embeddings (text-embedding-004)
- **Service Types:** 5 records (booking, cleaning, maintenance, etc.)
- **Business Hours:** 6 records (weekly schedule)
- **Blocked Times:** 25 records (unavailable slots)
- **Service Hours:** 5 records (service-specific availability)
- **Appointments:** 0 (transactional data, empty at startup)
- **Email Queue:** 0 (transactional data)
- **Conversation Sessions:** 0 (transactional data)
- **Agent Memory:** 0 (transactional data)

**Prerequisites for Phase 2:**
- Phase 1 completed ✅
- Python 3 available ✅
- Python dependencies installed ✅
- Google API key in SQL/.env ✅
- Database connectivity ✅

### Phase 3: Validation

**File:** `SQL/scripts/deploy.sh` (line 312-324)
**Action:** Validates deployment completeness

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: DEPLOYMENT VALIDATION                              │
├─────────────────────────────────────────────────────────────┤
│ 1. Check schema exists                                      │
│ 2. Verify all 14 tables created                             │
│ 3. Verify all 31 functions exist                            │
│ 4. Check indexes are in place                               │
│ 5. Validate data loading (row counts)                       │
│ 6. Check constraints and triggers                           │
│ 7. Verify pgvector extension installed                      │
└─────────────────────────────────────────────────────────────┘
```

**Expected Output:**
```
✅ Schema test exists
✅ All tables created (14/14)
✅ All functions created (31/31)
✅ All indexes created (80+)
✅ Data validation passed
✅ Products loaded: 90
✅ Service types: 5
✅ pgvector extension active
```

### Phase 4: Health Checks

**File:** `SQL/scripts/verify.sh`
**Action:** Runs comprehensive health checks

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: HEALTH CHECKS                                      │
├─────────────────────────────────────────────────────────────┤
│ 1. Database connectivity                                    │
│ 2. All tables accessible                                    │
│ 3. All functions callable                                   │
│ 4. Embeddings searchable (vector similarity)                │
│ 5. Booking functions operational                            │
│ 6. Memory functions operational                             │
│ 7. Email functions operational                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Running the Full Process

### Standard Execution

```bash
make db
```

**Expected output:**
```
╔═══════════════════════════════════════════════════════════╗
║  LAB01-MCP DATABASE DEPLOYMENT                            ║
╚═══════════════════════════════════════════════════════════╝

[STEP] Checking prerequisites...
✅ Docker found
✅ Container 'mcp-postgres' is running
✅ Database connectivity verified
✅ Deploy script found: 01_deploy.sql
✅ Validate script found: 02_validate_deployment.sql
✅ Verify script found: verify.sh
✅ All prerequisites passed

╔═══════════════════════════════════════════════════════════╗
║  PHASE 1: DATABASE DEPLOYMENT (DDL)                       ║
╚═══════════════════════════════════════════════════════════╝

[STEP] Running database deployment...
...
✅ Deployment completed successfully

╔═══════════════════════════════════════════════════════════╗
║  PHASE 2: DATA LOADING (DML + EMBEDDINGS)                 ║
╚═══════════════════════════════════════════════════════════╝

[STEP] Loading data via Python (with embeddings)...
✅ Data loaded successfully (including embeddings)

╔═══════════════════════════════════════════════════════════╗
║  PHASE 3: DEPLOYMENT VALIDATION                           ║
╚═══════════════════════════════════════════════════════════╝

[STEP] Running deployment validation...
✅ Validation completed

╔═══════════════════════════════════════════════════════════╗
║  PHASE 4: HEALTH CHECKS                                   ║
╚═══════════════════════════════════════════════════════════╝

[STEP] Running health checks...
✅ All health checks passed

╔═══════════════════════════════════════════════════════════╗
║  DEPLOYMENT SUMMARY                                       ║
╚═══════════════════════════════════════════════════════════╝

✅ Database deployment completed
ℹ️  Schema: test
ℹ️  Tables: 14 (DDL)
ℹ️  Indexes: 80+ (optimized)
ℹ️  Functions: 31 (bookings, email, memory)
ℹ️  Data loaded:
  • Products: 90 (with embeddings)
  • Service types: 5
  • Business hours: 6
  • Blocked times: 25
```

---

## ✅ Verification After Deployment

### Quick Verification

```bash
# Run quick health check
SQL/scripts/verify.sh --quick

# OR from Makefile
make db --validate-only
```

### Manual Verification

```bash
# Check schema exists
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "\dn"
# Expected: test schema with mcp_user owner ✅

# Check all tables
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "\dt test.*"
# Expected: 14 tables ✅

# Count functions
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
  SELECT COUNT(*) FROM pg_proc p
  JOIN pg_namespace n ON p.pronamespace = n.oid
  WHERE n.nspname = 'test';"
# Expected: 31 functions ✅

# Check data loaded
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
  SELECT
    'products' as table_name, COUNT(*) as rows
  FROM test.products
  UNION ALL
  SELECT 'service_types', COUNT(*) FROM test.service_types
  UNION ALL
  SELECT 'business_hours', COUNT(*) FROM test.business_hours;"
# Expected: products=90, service_types=5, business_hours=6 ✅

# Check embeddings exist
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
  SELECT COUNT(*) as products_with_embeddings
  FROM test.products
  WHERE embedding IS NOT NULL;"
# Expected: 90 ✅

# Search embeddings (semantic search test)
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
  SELECT COUNT(*) FROM test.products
  WHERE embedding IS NOT NULL LIMIT 1;"
# Expected: at least 1 row ✅
```

---

## 🔧 Troubleshooting

### Issue 1: Container Not Running

**Error:**
```
Container 'mcp-postgres' not found
```

**Solution:**
```bash
cd DockerConfig
docker-compose up -d
cd ..
make db
```

### Issue 2: Database Connectivity Failed

**Error:**
```
Cannot connect to database. Check credentials.
```

**Solution:**
```bash
# Check container is healthy
docker ps | grep mcp-postgres

# Check credentials in SQL/.env
cat SQL/.env | grep DATABASE_URL

# Test connection manually
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT 1;"
```

### Issue 3: Missing Python Dependencies

**Error:**
```
Failed to install Python packages: psycopg2, google-generativeai, etc.
```

**Solution:**
```bash
# Install dependencies manually
pip3 install psycopg2-binary python-dotenv tenacity google-generativeai pgvector

# Try with --break-system-packages if needed
pip3 install --break-system-packages psycopg2-binary python-dotenv tenacity google-generativeai pgvector

# Retry make db
make db
```

### Issue 4: Deployment Script Not Found

**Error:**
```
Database deploy script not found
```

**Solution:**
```bash
# Verify script exists
test -f SQL/scripts/deploy.sh && echo "✅ Found" || echo "❌ Missing"

# Make sure it's executable
chmod +x SQL/scripts/deploy.sh
chmod +x SQL/scripts/verify.sh

# Retry
make db
```

### Issue 5: Missing Google API Key

**Error:**
```
GOOGLE_API_KEY not found in .env
```

**Solution:**
```bash
# Get Google API Key from https://aistudio.google.com/app/apikey
# Add to SQL/.env
echo "GOOGLE_API_KEY=AIzaSy..." >> SQL/.env

# Retry
make db
```

### Issue 6: Validation Warnings

**Warning:**
```
⚠️  Some validation checks failed (see above)
```

**Action:** Check the specific error messages above. Some warnings are non-critical (like missing data in transactional tables).

---

## 🔍 Database State After Deployment

### Schema Structure

```
Database: mcpdb
Schema: test (owner: mcp_user)
├── Tables (14)
│   ├── products (90 rows, with embeddings)
│   ├── service_types (5 rows)
│   ├── business_hours (6 rows)
│   ├── blocked_times (25 rows)
│   ├── service_hours (5 rows)
│   ├── appointments (0 rows - transactional)
│   ├── email_queue (0 rows - transactional)
│   ├── conversation_sessions (0 rows - transactional)
│   ├── conversation_messages (0 rows - transactional)
│   ├── agent_memory_blocks (0 rows - transactional)
│   ├── user_memory_profiles (0 rows - transactional)
│   ├── user_memory_blocks (0 rows - transactional)
│   ├── agent_context_transfers (0 rows - transactional)
│   └── pagination_contexts (0 rows - transactional)
├── Indexes (80+)
│   ├── Primary keys on all tables
│   ├── Foreign key constraints
│   ├── Unique constraints
│   ├── Vector similarity indexes (pgvector)
│   └── Text search indexes (for fuzzy matching)
├── Functions (31)
│   ├── Booking functions (book_appointment, reschedule_appointment, etc.)
│   ├── Email functions (queue_notification, send_email, etc.)
│   ├── Memory functions (save_memory_block, retrieve_memory, etc.)
│   ├── Session functions (create_session, archive_session, etc.)
│   └── Helper functions (calculate_availability, validate_slot, etc.)
└── Extensions
    ├── pgvector (vector similarity search)
    ├── unaccent (accent-insensitive search)
    ├── uuid-ossp (unique identifiers)
    └── pg_trgm (trigram similarity)
```

### Vector Embeddings

**Product embeddings** are stored using:
- **Model:** text-embedding-004 (Google Gemini)
- **Dimensions:** 1536 (default)
- **Type:** pgvector (PostgreSQL vector column)
- **Storage:** test.products.embedding column
- **Count:** 90 products with embeddings

---

## 📊 Performance Expectations

### Timing Breakdown

| Phase | Duration | Notes |
|-------|----------|-------|
| Phase 1 (DDL) | 30-60 sec | Creating schema, tables, functions |
| Phase 2 (Data) | 1-2 min | Depends on Google API latency |
| Phase 3 (Validation) | 10-15 sec | Database checks |
| Phase 4 (Health) | 5-10 sec | Connectivity tests |
| **Total** | **2-5 min** | Typical end-to-end time |

### API Rate Limiting

The Google Gemini API has rate limits:
- **Free tier:** 15 requests per minute
- **Batch size:** 8 products per batch
- **Total products:** 90 (requires ~11 API calls)
- **Expected API time:** 45-90 seconds

---

## 🔄 Re-running the Deployment

**Important:** The deployment is **idempotent** but requires **schema cleanup** on re-runs.

### Option 1: Fresh Deployment (Drop and Recreate)

```bash
# Drop the entire schema (WARNING: Deletes all data!)
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "DROP SCHEMA test CASCADE;"

# Run deployment fresh
make db
```

### Option 2: Data-Only Reload (Keep Schema, Reload Data)

```bash
# Clear data but keep schema
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
  DELETE FROM test.products;
  DELETE FROM test.service_types;
  DELETE FROM test.business_hours;
  DELETE FROM test.blocked_times;"

# Re-run deployment (only Phase 2 will work, Phase 1 will warn about existing objects)
make db --no-verify
```

### Option 3: Validation Only

```bash
# Check deployment without changes
make db --validate-only
```

---

## 🎯 Common Workflows

### First Time Setup

```bash
# 1. Start Docker services
cd DockerConfig && docker-compose up -d && cd ..

# 2. Create environment files
make setup-env

# 3. Configure credentials
nano SQL/.env          # Set GOOGLE_API_KEY
nano mcp_server/.env   # Set credentials
nano email_service/.env # Set SMTP

# 4. Deploy database
make db

# 5. Validate everything works
make validate
```

### Development Workflow

```bash
# After making schema changes:
make db --no-verify  # Skip health checks for faster iterations

# After completing changes:
make db  # Run full deployment with validation
```

### Production Deployment

```bash
# Check all prerequisites first
make validate

# Run full deployment with verification
make db

# Run comprehensive health checks
SQL/scripts/verify.sh

# Monitor logs
tail -f logs/*.log
```

---

## 📝 Environment File Checklist

Before running `make db`, ensure:

```bash
# SQL/.env has these variables:
DATABASE_URL=postgresql://mcp_user:password@localhost:5434/mcpdb
GOOGLE_API_KEY=AIza... (from https://aistudio.google.com/app/apikey)
SCHEMA_NAME=test
EMBEDDING_MODEL=gemini-embedding-001
BATCH_SIZE=8
LOG_LEVEL=INFO

# Verify:
grep -E "DATABASE_URL|GOOGLE_API_KEY|SCHEMA_NAME" SQL/.env
```

---

## ✅ Summary

| Requirement | Status | Command |
|------------|--------|---------|
| Docker installed | ✅ Required | `docker --version` |
| Container running | ✅ Required | `docker ps \| grep mcp-postgres` |
| DB connectivity | ✅ Required | `docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT 1;"` |
| Python 3 | ✅ Required | `python3 --version` |
| Python packages | ✅ Required | `python3 -c "import psycopg2, google.genai"` |
| SQL files | ✅ Required | `ls SQL/scripts/deploy.sh` |
| .env file | ✅ Required | `test -f SQL/.env` |
| Google API key | ✅ Required | `grep GOOGLE_API_KEY SQL/.env` |

**All requirements met?** → Ready for `make db` ✅

---

## 🔗 Related Documentation

- [`docs/ENVIRONMENT_SETUP.md`](./ENVIRONMENT_SETUP.md) - Environment variable configuration
- [`docs/ENV_VARIABLE_MAPPING.md`](./ENV_VARIABLE_MAPPING.md) - Complete variable mapping
- `SQL/scripts/deploy.sh` - Actual deployment script
- `SQL/scripts/verify.sh` - Health check script
- `SQL/src/populate.py` - Data loader with embeddings

---

## 📞 Support

If `make db` fails:
1. Check prerequisites above
2. Review error messages in output
3. Consult troubleshooting section
4. Check logs: `tail -f logs/*.log`
5. Run manual verification commands above

