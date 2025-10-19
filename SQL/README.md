# Lab01-MCP Database Schema

Professional, modular PostgreSQL database schema for Lab01-MCP multi-agent booking system with vector embeddings and memory management.

## Structure

Modular, production-ready database deployment with clear separation of concerns:

```
SQL/
├── 00_init/                 # Database initialization (extensions, schema, permissions)
├── 01_ddl/                  # Data Definition Language (tables)
│   ├── bookings/            # Appointment & scheduling tables
│   ├── email/               # Email queue system
│   ├── memory/              # Multi-agent memory system
│   └── utils/               # Utility tables
├── 02_functions/            # Stored procedures & business logic
├── 03_indexes/              # (Indexes included inline in DDL)
├── 04_seed/                 # Optional seed data
└── deploy.sql               # Master deployment script

Legacy files archived: sql-backup/ (scripts_legacy, src_legacy, etc.)
```

## Features

- **14 Tables**: Products, bookings, email queue, multi-agent memory, pagination
- **Modular Deployment**: Execute individual files or use master `deploy.sql`
- **Vector Search**: pgvector embeddings (1536-dim) with IVFFlat indexes
- **Fuzzy Search**: Trigram GIN indexes for accent-insensitive search
- **Memory System**: Session-based and user-level memory with TTL management
- **Email Queue**: Asynchronous delivery with retry logic and priority
- **Hybrid Scheduling**: Service-specific hours with business_hours fallback
- **GDPR Compliant**: Soft-delete archiving and lifecycle management
- **29 Optimized Indexes**: B-tree, GIN, GiST, IVFFlat for various patterns
- **Production Ready**: Error handling, triggers, constraints, comprehensive functions

## Prerequisites

Before running the scripts, ensure you have:

- **PostgreSQL 15+** with pgvector extension installed
- **Python 3.10+**
- **Docker** (for containerized PostgreSQL deployment)
- **Google Gemini API Key** ([Get one here](https://aistudio.google.com/app/apikey))

### Required Python Packages

```bash
pip install psycopg2-binary python-dotenv google-genai pgvector tenacity
```

## Installation

### 1. Clone or Navigate to Project

```bash
cd /home/javort/Lab01-MCP/SQL
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
nano .env
```

Required variables:
```bash
DATABASE_URL=postgresql://mcp_user:mcp_password@localhost:5434/mcpdb
SCHEMA_NAME=test
GOOGLE_API_KEY=your_api_key_here
```

### 3. Start PostgreSQL Container

From the DockerConfig directory:

```bash
cd ../DockerConfig
./start.sh
```

Or directly with Docker Compose:

```bash
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `POSTGRES_USER` | Database user | `mcp_user` | Yes |
| `POSTGRES_PASSWORD` | Database password | `mcp_password` | Yes |
| `POSTGRES_DB` | Database name | `mcpdb` | Yes |
| `POSTGRES_HOST` | Database host | `localhost` | Yes |
| `POSTGRES_PORT` | Database port | `5434` | Yes |
| `SCHEMA_NAME` | Target schema for tables | `test` | Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | - | Yes |
| `EMBEDDING_MODEL` | Gemini embedding model | `gemini-embedding-001` | No |
| `OUTPUT_DIMENSIONALITY` | Embedding dimensions | `1536` | No |
| `BATCH_SIZE` | Batch size for API calls | `8` | No |
| `MAX_RETRIES` | Maximum API retry attempts | `5` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### Docker Configuration

The scripts are aligned with the PostgreSQL container configuration:

- **Container Name**: `mcp-postgres`
- **External Port**: `5434`
- **Internal Port**: `5432`
- **Database**: `mcpdb`
- **Network**: `docker-config`

## Usage

### Data Initialization Flow

```mermaid
flowchart TD
    Start([🚀 Start Database Setup]) --> CheckDocker{Docker<br/>PostgreSQL<br/>Running?}

    CheckDocker -->|❌ No| StartDocker["Start PostgreSQL<br/>cd DockerConfig<br/>docker-compose up -d"]
    CheckDocker -->|✅ Yes| CheckEnv{".env File<br/>Configured?"}

    StartDocker --> CheckEnv

    CheckEnv -->|❌ No| ConfigEnv["📝 Configure .env<br/>- DATABASE_URL<br/>- GOOGLE_API_KEY<br/>- SCHEMA_NAME=test"]
    CheckEnv -->|✅ Yes| InitDB["1️⃣ Initialize Database<br/>python3 src/init-db.py<br/>━━━━━━━━<br/>• Create schema 'test'<br/>• Create tables<br/>• Create indexes<br/>• Create functions"]

    ConfigEnv --> InitDB

    InitDB --> VerifySchema{Schema<br/>Created?}

    VerifySchema -->|❌ Failed| Error1["❌ Check Logs<br/>- Connection errors?<br/>- Permission issues?<br/>- Extensions missing?"]
    VerifySchema -->|✅ Success| LoadProducts["2️⃣ Load Products<br/>python3 src/populate-db.py<br/>━━━━━━━━<br/>Read 90 products<br/>from data/products.json"]

    Error1 --> Troubleshoot1["🔧 Fix Issues<br/>- Verify DATABASE_URL<br/>- Install extensions<br/>- Check PostgreSQL logs"]
    Troubleshoot1 --> InitDB

    LoadProducts --> GenerateEmbeddings["3️⃣ Generate Embeddings<br/>Batch processing (8 products/batch)<br/>━━━━━━━━<br/>Google Gemini API<br/>gemini-embedding-001<br/>1536 dimensions"]

    GenerateEmbeddings --> RateLimit{Rate Limit<br/>Hit?}

    RateLimit -->|❌ No| InsertData["4️⃣ Insert to Database<br/>UPSERT operations<br/>━━━━━━━━<br/>• Products + embeddings<br/>• Update existing<br/>• Insert new"]
    RateLimit -->|✅ Yes (429)| Wait["⏳ Exponential Backoff<br/>Retry with delay"]

    Wait --> GenerateEmbeddings

    InsertData --> VerifyData{Data<br/>Inserted?}

    VerifyData -->|❌ Failed| Error2["❌ Database Error<br/>Check constraints,<br/>data types,<br/>unique violations"]
    VerifyData -->|✅ Success| BuildIndexes["5️⃣ Build Indexes<br/>━━━━━━━━<br/>• IVFFlat vector index<br/>• Trigram GIN indexes<br/>• B-Tree indexes"]

    Error2 --> Troubleshoot2["🔧 Fix Data Issues<br/>- Check SKU uniqueness<br/>- Validate JSON format<br/>- Review data types"]
    Troubleshoot2 --> LoadProducts

    BuildIndexes --> Analyze["6️⃣ Analyze Tables<br/>ANALYZE test.products<br/>━━━━━━━━<br/>Update query planner<br/>statistics"]

    Analyze --> Verify["7️⃣ Verification<br/>━━━━━━━━<br/>SELECT COUNT(*)<br/>FROM test.products"]

    Verify --> VerifyCount{Count = 90<br/>products?}

    VerifyCount -->|❌ No| Error3["❌ Incomplete Data<br/>Missing products or<br/>embeddings"]
    VerifyCount -->|✅ Yes| TestSearch["8️⃣ Test Searches<br/>━━━━━━━━<br/>• Test fuzzy search<br/>• Test vector search<br/>• Test pagination"]

    Error3 --> Troubleshoot3["🔧 Re-run populate-db.py<br/>Check for API errors<br/>in logs"]
    Troubleshoot3 --> LoadProducts

    TestSearch --> Success["✅ Setup Complete!<br/>━━━━━━━━<br/>• 90 products loaded<br/>• 90 embeddings generated<br/>• 15 indexes created<br/>• All tests passed"]

    Success --> Ready([🎉 Database Ready for Use])

    style Start fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style Success fill:#c8e6c9,stroke:#1b5e20,stroke-width:3px
    style Ready fill:#a5d6a7,stroke:#388e3c,stroke-width:3px
    style Error1 fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style Error2 fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style Error3 fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style CheckDocker fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style CheckEnv fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style VerifySchema fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style RateLimit fill:#fff59d,stroke:#f9a825,stroke-width:2px
    style Wait fill:#ffe082,stroke:#ff8f00,stroke-width:2px
```

### Quick Start

#### ✨ **NEW: Automated Deployment Script (Recommended)**

Deploy the **complete database** from zero to functional with a single command:

```bash
cd SQL
./deploy_database.sh
```

This master deployment script handles **everything automatically**:
1. ✅ **Validates prerequisites** (Docker, Python, PostgreSQL, .env, packages)
2. ✅ **Deploys all schemas** (products, memory, bookings, email queue)
3. ✅ **Populates data** (90 products with Gemini embeddings)
4. ✅ **Creates indexes** (15 optimized indexes)
5. ✅ **Seeds test data** (optional booking data)
6. ✅ **Verifies deployment** (comprehensive health checks)
7. ✅ **Provides detailed reporting** (color-coded progress)

**Deployment Modes:**

```bash
# Full deployment (recommended for development)
./deploy_database.sh

# Production deployment (skip test data)
./deploy_database.sh --skip-seed

# Minimal deployment (core schema + products only)
./deploy_database.sh --only-core

# Verification only (check existing database)
./deploy_database.sh --verify-only

# Help and options
./deploy_database.sh --help
```

#### Quick Verification

Check database health after deployment:

```bash
# Full verification (11 checks)
./verify_database.sh

# Quick health check only
./verify_database.sh --quick

# Detailed status report
./verify_database.sh --report
```

#### Manual Deployment (Advanced)

For manual control, you can still run individual scripts:

```bash
# 1. Initialize core schema
python3 src/init-db.py

# 2. Populate products with embeddings
python3 src/populate-db.py

# 3. Initialize memory system
python3 src/init_memory_system.py

# 4. Initialize bookings
python3 src/init_bookings.py

# 5. Initialize email queue
python3 src/init_email_queue.py

# 6. Seed test data (optional)
python3 src/seed_booking_data.py
```

### Step-by-Step Deployment Guide

Complete walkthrough from **zero to functional database**:

#### Step 1: Verify Docker PostgreSQL Container

```bash
# Navigate to DockerConfig directory
cd /home/javort/Lab01-MCP/DockerConfig

# Check if container is running
docker ps | grep mcp-postgres

# If not running, start the container
docker-compose up -d

# Verify container is healthy
docker logs mcp-postgres --tail 50
```

**Expected output:**
```
✅ Container mcp-postgres is running
✅ PostgreSQL is ready to accept connections
✅ Port 5434:5432 is mapped correctly
```

#### Step 2: Configure Environment Variables

```bash
# Navigate to SQL directory
cd /home/javort/Lab01-MCP/SQL

# Check if .env exists
ls -la .env

# If not, copy the example
cp .env.example .env

# Edit the configuration
nano .env
```

**Required variables:**
```bash
DATABASE_URL=postgresql://mcp_user:mcp_password@localhost:5434/mcpdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_USER=mcp_user
POSTGRES_PASSWORD=mcp_password
POSTGRES_DB=mcpdb
SCHEMA_NAME=test
GOOGLE_API_KEY=your_google_api_key_here  # Get from https://aistudio.google.com/app/apikey
EMBEDDING_MODEL=text-embedding-004
OUTPUT_DIMENSIONALITY=1536
BATCH_SIZE=8
```

#### Step 3: Verify Python Dependencies

```bash
# Check Python version (requires 3.10+)
python3 --version

# Install required packages
pip install psycopg2-binary python-dotenv google-genai pgvector tenacity

# Verify installation
python3 -c "import psycopg2, dotenv, google.genai; print('✅ All packages installed')"
```

#### Step 4: Run Automated Deployment

```bash
# Ensure you're in the SQL directory
cd /home/javort/Lab01-MCP/SQL

# Make scripts executable (if not already)
chmod +x deploy_database.sh verify_database.sh

# Run full deployment
./deploy_database.sh
```

**What happens during deployment:**
```
🚀 Phase 1: Prerequisites Check
   ✅ Docker container running
   ✅ PostgreSQL accessible on port 5434
   ✅ .env file configured
   ✅ Python packages installed

🚀 Phase 2: Core Schema Deployment
   ✅ Schema 'test' created
   ✅ Extensions installed (vector, pg_trgm, unaccent, uuid-ossp)
   ✅ Products table created
   ✅ Pagination contexts table created

🚀 Phase 3: Data Population
   ✅ Loading 90 products from data/products.json
   ✅ Generating embeddings via Google Gemini API
   ✅ Batch processing (8 products per batch)
   ✅ UPSERT operations (insert new, update existing)

🚀 Phase 4: Index Creation
   ✅ 15 indexes created
   ✅ IVFFlat vector index (100 lists)
   ✅ Trigram GIN indexes (fuzzy search)
   ✅ B-Tree indexes (SKU, category, price)

🚀 Phase 5: Memory System
   ✅ Agent memory tables created
   ✅ Conversation contexts table
   ✅ Context transfers table

🚀 Phase 6: Bookings System
   ✅ Appointments table created
   ✅ Business hours configuration
   ✅ Available services table

🚀 Phase 7: Email Queue System
   ✅ Email queue table created
   ✅ Email templates support

🚀 Phase 8: Verification
   ✅ All 90 products loaded
   ✅ All 90 embeddings generated
   ✅ Fuzzy search working
   ✅ Vector search working

✅ DEPLOYMENT COMPLETE!
```

#### Step 5: Verify Deployment

```bash
# Run comprehensive verification
./verify_database.sh

# Or quick check only
./verify_database.sh --quick

# Or detailed status report
./verify_database.sh --report
```

**Expected verification output:**
```
╔═══════════════════════════════════════════════════════════╗
║       Lab01-MCP Database Verification                    ║
╚═══════════════════════════════════════════════════════════╝

Running quick health checks...

✅ Container running
✅ Connection successful
✅ Schema 'test' exists
✅ Found 7 tables
✅ All 90 products loaded
✅ All 90 embeddings generated

Running detailed checks...

✅ All 4 extensions installed
✅ Found 15 indexes
✅ Found 3 functions
✅ Fuzzy search working (12 results)
✅ Vector search available

═══════════════════════════════════════════════════════════
  VERIFICATION SUMMARY
═══════════════════════════════════════════════════════════

✅ All checks passed! Database is healthy. 🎉
ℹ️  Port: 5434
ℹ️  Database: mcpdb
ℹ️  Schema: test

ℹ️  Run './verify_database.sh --report' for detailed status
```

#### Step 6: Test Database Queries

```bash
# Connect to database
docker exec -it mcp-postgres psql -U mcp_user -d mcpdb

# Test queries
mcpdb=# SELECT COUNT(*) FROM test.products;
 count
-------
    90
(1 row)

mcpdb=# SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;
 count
-------
    90
(1 row)

mcpdb=# SELECT name, brand, price FROM test.products LIMIT 5;
                    name                    |    brand     |  price
--------------------------------------------+--------------+---------
 Laptop Gaming Asus ROG Strix G15           | Asus         | 1299.99
 Laptop HP Pavilion 15                      | HP           |  749.99
 MacBook Air M2                             | Apple        | 1199.99
 Dell XPS 13 Plus                           | Dell         | 1399.99
 Lenovo ThinkPad X1 Carbon Gen 11           | Lenovo       | 1599.99
(5 rows)

mcpdb=# \dt test.*
              List of relations
 Schema |         Name          | Type  |   Owner
--------+-----------------------+-------+-----------
 test   | agent_memory          | table | mcp_user
 test   | appointments          | table | mcp_user
 test   | context_transfers     | table | mcp_user
 test   | conversation_contexts | table | mcp_user
 test   | email_queue           | table | mcp_user
 test   | pagination_contexts   | table | mcp_user
 test   | products              | table | mcp_user
(7 rows)

mcpdb=# \q
```

#### Step 7: Test Search Capabilities

```bash
# Test fuzzy search
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
SELECT name,
       similarity(normalize_text(name), normalize_text('laptop')) as score
FROM test.products
WHERE similarity(normalize_text(name), normalize_text('laptop')) > 0.3
ORDER BY score DESC
LIMIT 5;"

# Test vector search availability
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
SELECT COUNT(*) as products_with_vectors
FROM test.products
WHERE embedding IS NOT NULL;"

# Test category search
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "
SELECT category, COUNT(*) as count
FROM test.products
GROUP BY category
ORDER BY count DESC;"
```

### Verify Installation

```bash
# Quick count checks
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT COUNT(*) FROM test.products;"
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;"

# Or use the verification script (recommended)
./verify_database.sh
```

Expected output: **90 products** with embeddings

## Project Structure

```
SQL/
├── deploy_database.sh         # ✨ MASTER DEPLOYMENT SCRIPT (680 lines) - NEW!
├── verify_database.sh         # ✨ VERIFICATION SCRIPT (450 lines) - NEW!
├── data/
│   └── products.json          # 90 products dataset (laptops, electronics)
├── src/
│   ├── init-db.py             # Products schema initialization (324 lines)
│   ├── populate-db.py         # Data population with embeddings (221 lines)
│   ├── init_memory_system.py  # Agent memory system initialization
│   ├── init_bookings.py       # Bookings schema initialization
│   ├── init_email_queue.py    # Email queue system initialization
│   ├── seed_booking_data.py   # Seed booking test data
│   └── migrations/            # Database migration scripts
│       └── *.sql              # SQL migration files
├── scripts/
│   ├── create_bookings_schema.sql  # Bookings SQL DDL
│   ├── create_email_queue.sql      # Email queue SQL DDL
│   ├── init-db.sh             # Legacy shell wrapper
│   └── populate-db.sh         # Legacy shell wrapper
├── examples/
│   ├── README_TESTING.md      # Testing guide
│   ├── test_pagination.sh     # Pagination test script
│   └── test_pagination_persistence.sql  # SQL pagination tests
├── .env                       # Environment configuration (DO NOT commit)
├── .env.example               # Environment template (safe to commit)
└── README.md                  # This comprehensive guide
```

### Deployment Scripts Overview

| Script | Lines | Purpose | Usage |
|--------|-------|---------|-------|
| `deploy_database.sh` | 680 | Master deployment orchestrator | `./deploy_database.sh` |
| `verify_database.sh` | 450 | Health check and verification | `./verify_database.sh` |
| `init-db.py` | 324 | Core schema initialization | Called by deploy script |
| `populate-db.py` | 221 | Data population with embeddings | Called by deploy script |
| `init_memory_system.py` | ~200 | Memory system tables | Called by deploy script |
| `init_bookings.py` | ~180 | Bookings system tables | Called by deploy script |
| `init_email_queue.py` | ~150 | Email queue system | Called by deploy script |

## Database Schema

### Entity-Relationship Diagram

```mermaid
erDiagram
    PRODUCTS ||--o{ PRODUCT_EMBEDDINGS : has
    PRODUCTS {
        serial id PK "Auto-increment primary key"
        text sku UK "Unique product identifier (COMP-001)"
        text name "Product name"
        text description "Detailed description"
        text category "Product category"
        text brand "Brand name"
        text[] tags "Array of searchable tags"
        text color "Product color"
        text size "Product size"
        numeric price "Price (12,2 precision)"
        vector_1536 embedding "Gemini AI embedding vector"
        timestamp created_at "Record creation time"
        timestamp updated_at "Last update time"
    }

    PRODUCT_EMBEDDINGS {
        int product_id FK "References products(id)"
        vector_1536 embedding "1536-dimensional vector"
        text model_version "gemini-embedding-001"
        timestamp generated_at "Embedding generation time"
    }

    PAGINATION_CONTEXTS {
        uuid session_id PK "Session identifier"
        text category "Search category"
        text tool_name "MCP tool used"
        text query "Original search query"
        jsonb results "Paginated results array"
        int current_page "Current page number (1-based)"
        int page_size "Items per page (default: 4)"
        int total_items "Total result count"
        timestamp created_at "Context creation time"
        timestamp updated_at "Last access time"
    }

    USER_SESSIONS ||--o{ PAGINATION_CONTEXTS : creates
    USER_SESSIONS {
        uuid session_id PK "Unique session identifier"
        text user_agent "Browser/client info"
        inet ip_address "Client IP address"
        timestamp started_at "Session start time"
        timestamp last_activity "Last activity timestamp"
    }
```

### Database Architecture

```mermaid
graph TB
    subgraph Schema["📊 Database Schema: test"]
        direction TB

        subgraph Core["Core Tables"]
            Products["🛍️ products<br/>━━━━━━━━<br/>90 product records<br/>15 optimized indexes"]
            Pagination["📄 pagination_contexts<br/>━━━━━━━━<br/>Session-based pagination<br/>Auto-cleanup (24h TTL)"]
        end

        subgraph Indexes["🔍 Index Types"]
            IVFFlat["Vector Index (IVFFlat)<br/>━━━━━━━━<br/>embedding column<br/>100 lists, L2 distance"]
            Trigram["Trigram GIN Index<br/>━━━━━━━━<br/>name, description, brand<br/>Fuzzy text search"]
            BTree["B-Tree Indexes<br/>━━━━━━━━<br/>SKU (unique), category,<br/>price, tags (GIN)"]
        end

        subgraph Functions["⚙️ PostgreSQL Functions"]
            Normalize["normalize_text(text)<br/>━━━━━━━━<br/>Lowercase + unaccent<br/>Used in searches"]
            Similarity["get_similarity_threshold()<br/>━━━━━━━━<br/>Returns: 0.3<br/>Configurable threshold"]
            Cleanup["cleanup_expired_contexts()<br/>━━━━━━━━<br/>Removes old pagination<br/>Runs on schedule"]
        end
    end

    subgraph Extensions["📦 PostgreSQL Extensions"]
        Vector["vector<br/>pgvector 0.5+<br/>Vector operations"]
        PgTrgm["pg_trgm<br/>Trigram similarity<br/>Fuzzy matching"]
        Unaccent["unaccent<br/>Accent removal<br/>Normalization"]
        UUIDOSSP["uuid-ossp<br/>UUID generation<br/>Session IDs"]
        PgCrypto["pgcrypto<br/>Cryptographic funcs<br/>Security"]
    end

    Products --> IVFFlat
    Products --> Trigram
    Products --> BTree

    Pagination --> Cleanup

    Products -.->|Uses| Normalize
    Products -.->|Uses| Similarity

    IVFFlat -.->|Requires| Vector
    Trigram -.->|Requires| PgTrgm
    Normalize -.->|Requires| Unaccent
    Pagination -.->|Uses| UUIDOSSP

    style Core fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style Indexes fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style Functions fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Extensions fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```

### Table Specifications

#### `test.products`

**Primary Table for Product Catalog**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-increment primary key |
| `sku` | TEXT | UNIQUE NOT NULL | Unique product identifier (e.g., COMP-001) |
| `name` | TEXT | NOT NULL | Product name |
| `description` | TEXT | | Detailed description |
| `category` | TEXT | | Product category |
| `brand` | TEXT | | Brand name |
| `tags` | TEXT[] | | Array of searchable tags |
| `color` | TEXT | | Product color |
| `size` | TEXT | | Product size |
| `price` | NUMERIC(12,2) | | Product price |
| `embedding` | VECTOR(1536) | | Gemini AI embedding vector |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update time |

**Indexes** (15 total):
- `idx_products_sku` - B-Tree unique index on SKU
- `idx_products_embedding_ivf` - IVFFlat vector index (100 lists, L2 distance)
- `idx_products_name_trigram` - GIN trigram index for fuzzy name search
- `idx_products_description_trigram` - GIN trigram index for description search
- `idx_products_brand_trigram` - GIN trigram index for brand search
- `idx_products_category` - B-Tree index on category
- `idx_products_price` - B-Tree index on price
- `idx_products_tags` - GIN index on tags array
- ... and 7 more specialized indexes

#### `test.pagination_contexts`

**Session-based Pagination Storage**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `session_id` | UUID | PRIMARY KEY | Unique session identifier |
| `category` | TEXT | NOT NULL | Search category |
| `tool_name` | TEXT | | MCP tool used for search |
| `query` | TEXT | | Original search query |
| `results` | JSONB | | Paginated results array |
| `current_page` | INTEGER | DEFAULT 1 | Current page number (1-based) |
| `page_size` | INTEGER | DEFAULT 4 | Items per page |
| `total_items` | INTEGER | | Total result count |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Context creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last access time |

**Auto-Cleanup:** Contexts older than 24 hours are automatically removed.

### Database Functions

#### `normalize_text(text)`
**Purpose:** Text normalization for consistent search
```sql
CREATE OR REPLACE FUNCTION normalize_text(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN lower(unaccent(input_text));
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```
**Used in:** Fuzzy search queries, trigram matching

#### `get_similarity_threshold()`
**Purpose:** Returns configurable similarity threshold
```sql
CREATE OR REPLACE FUNCTION get_similarity_threshold()
RETURNS FLOAT AS $$
BEGIN
    RETURN 0.3; -- Configurable threshold
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```
**Used in:** Fuzzy search filtering

#### `cleanup_expired_pagination_contexts()`
**Purpose:** Removes expired pagination contexts
```sql
CREATE OR REPLACE FUNCTION cleanup_expired_pagination_contexts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM test.pagination_contexts
    WHERE updated_at < NOW() - INTERVAL '24 hours';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```
**Scheduled:** Run daily via cron job

### PostgreSQL Extensions

| Extension | Version | Purpose | Status |
|-----------|---------|---------|--------|
| **vector** | 0.5+ | Vector embeddings (pgvector) | ✅ Required |
| **pg_trgm** | 1.6+ | Trigram similarity search | ✅ Required |
| **unaccent** | 1.1+ | Accent-insensitive search | ✅ Required |
| **uuid-ossp** | 1.1+ | UUID generation | ✅ Required |
| **pgcrypto** | 1.3+ | Cryptographic functions | ⚠️ Optional |

## Product Dataset Statistics

### Overview

| Metric | Value |
|--------|-------|
| Total Products | 90 |
| Laptops (COMP-00xx) | 43 |
| Products with Embeddings | 90 (100%) |
| Unique Categories | 23 |
| Unique Brands | 57 |

### Laptop Categories

| Category | Count | Price Range | Average |
|----------|-------|-------------|---------|
| Gaming | 12 | $699 - $2,499 | $1,338 |
| Business/Workstation | 10 | $849 - $2,399 | $1,519 |
| Students | 10 | $449 - $699 | $563 |
| Ultrabooks Premium | 7 | $899 - $2,299 | $1,556 |

## Example Queries

### Search by Category

```sql
SELECT sku, name, brand, price
FROM test.products
WHERE category = 'Computación'
  AND name LIKE '%Gaming%'
ORDER BY price DESC
LIMIT 10;
```

### Fuzzy Search with Typos

```sql
SELECT name,
       similarity(normalize_text(name), normalize_text('camputadora gaming')) as score
FROM test.products
WHERE similarity(normalize_text(name), normalize_text('camputadora gaming')) > 0.3
ORDER BY score DESC
LIMIT 5;
```

### Vector Similarity Search

```sql
SELECT name, price,
       embedding <-> '[0.1, 0.2, ...]'::vector as distance
FROM test.products
ORDER BY distance
LIMIT 10;
```

### Statistics by Brand

```sql
SELECT
    brand,
    COUNT(*) as total,
    MIN(price) as min_price,
    MAX(price) as max_price,
    ROUND(AVG(price), 2) as avg_price
FROM test.products
WHERE sku LIKE 'COMP-00%'
GROUP BY brand
ORDER BY total DESC;
```

## Troubleshooting

### Common Issues with Automated Deployment

#### ✅ Using the Verification Script

Before troubleshooting manually, **always run the verification script first**:

```bash
./verify_database.sh --report
```

This provides a comprehensive diagnostic report that identifies most issues automatically.

### Deployment Script Issues

#### Error: "Permission denied: ./deploy_database.sh"

**Cause**: Script not executable

**Solution**:
```bash
chmod +x deploy_database.sh verify_database.sh
./deploy_database.sh
```

#### Error: "Prerequisites check failed"

**Cause**: Missing Docker, Python, or PostgreSQL container

**Solution**:
```bash
# Check what's missing
./deploy_database.sh --verify-only

# Start PostgreSQL if needed
cd ../DockerConfig && docker-compose up -d

# Verify Python version
python3 --version  # Must be 3.10+

# Install missing packages
pip install psycopg2-binary python-dotenv google-genai pgvector tenacity
```

#### Error: "Phase X failed" during deployment

**Cause**: Specific phase encountered an error

**Solution**:
```bash
# Check the detailed error message in the output
# The script shows exactly which phase failed

# Common fixes:
# - Phase 1 (Prerequisites): Check .env file and Docker
# - Phase 2 (Core Schema): Database connection issues
# - Phase 3 (Data Population): Google API key or rate limiting
# - Phase 4-7 (Additional Schemas): Permission or schema conflicts

# Re-run deployment after fixing the issue
./deploy_database.sh
```

### Database Connection Issues

#### Error: "DATABASE_URL not found"

**Cause**: Missing `.env` file or incorrect variable name

**Solution**:
```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env

# Verify .env contains required variables
grep -E "DATABASE_URL|GOOGLE_API_KEY|SCHEMA_NAME" .env
```

#### PostgreSQL Connection Failed

**Cause**: Container not running or incorrect credentials

**Solution**:
```bash
# Check container status
docker ps | grep mcp-postgres

# If not running, start it
cd ../DockerConfig && docker-compose up -d

# Wait for PostgreSQL to be ready (10-15 seconds)
sleep 15

# Verify connection
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT version();"

# Check logs if still failing
docker logs mcp-postgres --tail 50
```

#### Error: "Port 5434 already in use"

**Cause**: Another service using port 5434

**Solution**:
```bash
# Check what's using the port
lsof -i :5434

# Option 1: Stop the conflicting service
# Option 2: Change the port in docker-compose.yml and .env

# Restart PostgreSQL
cd ../DockerConfig && docker-compose down && docker-compose up -d
```

### Google API Issues

#### Error: "GOOGLE_API_KEY not found"

**Cause**: Missing or invalid Google API key

**Solution**:
1. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Add to `.env`:
   ```bash
   GOOGLE_API_KEY=AIzaSy...your_key_here
   ```
3. Re-run deployment:
   ```bash
   ./deploy_database.sh
   ```

#### Error: "Embedding response not contains embedding"

**Cause**: API structure change or outdated `google-genai` package

**Solution**:
```bash
# Update package to latest version
pip install --upgrade google-genai

# Verify version
pip show google-genai

# The populate-db.py script has automatic fallback handling
# Re-run deployment
./deploy_database.sh
```

#### Rate Limiting (429 Error)

**Cause**: Too many API calls to Google Gemini

**Solution**:
```bash
# Option 1: Reduce batch size in .env
nano .env
# Change: BATCH_SIZE=4  (from 8)

# Option 2: Wait and retry (script has auto-retry)
# The deploy script automatically retries with exponential backoff

# Option 3: Check your API quota
# Visit https://aistudio.google.com/app/apikey
```

### Data and Schema Issues

#### Error: "Table already exists"

**Cause**: Re-running deployment on existing database

**Solution**:
```bash
# Option 1: Drop existing schema (⚠️ DESTROYS DATA)
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "DROP SCHEMA test CASCADE;"
./deploy_database.sh

# Option 2: Use UPSERT behavior (populate-db.py handles this)
# Just re-run populate script
python3 src/populate-db.py

# Option 3: Fresh start with new database
cd ../DockerConfig
docker-compose down -v  # ⚠️ Removes all data
docker-compose up -d
cd ../SQL
./deploy_database.sh
```

#### Error: "Only X/90 products loaded"

**Cause**: Incomplete data population (API errors, interruption)

**Solution**:
```bash
# Re-run just the population phase
python3 src/populate-db.py

# Or re-deploy everything
./deploy_database.sh

# Verify with detailed report
./verify_database.sh --report
```

#### Error: "Embeddings not generated"

**Cause**: Google API key issue or network problem

**Solution**:
```bash
# Verify API key is correct
echo $GOOGLE_API_KEY

# Test API key manually
python3 -c "
from dotenv import load_dotenv
import os
import google.genai as genai
load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
print('✅ API key is valid')
"

# Re-run population with embeddings
python3 src/populate-db.py
```

### Extension Issues

#### Error: "Extension 'vector' does not exist"

**Cause**: pgvector extension not installed in PostgreSQL

**Solution**:
```bash
# Check if extension is available
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT * FROM pg_available_extensions WHERE name='vector';"

# If not available, rebuild container with pgvector
cd ../DockerConfig
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for PostgreSQL to start
sleep 15

# Re-run deployment
cd ../SQL
./deploy_database.sh
```

### Verification Failures

#### Verification shows "X/11 checks failed"

**Cause**: Incomplete or failed deployment

**Solution**:
```bash
# Get detailed report
./verify_database.sh --report

# Common fixes based on failed checks:
# - Container not running → cd ../DockerConfig && docker-compose up -d
# - Connection failed → Check DATABASE_URL in .env
# - Schema missing → Re-run: python3 src/init-db.py
# - Products missing → Re-run: python3 src/populate-db.py
# - Embeddings missing → Check GOOGLE_API_KEY and re-run populate-db.py
# - Indexes missing → Already created by init-db.py, check logs
# - Functions missing → Re-run: python3 src/init-db.py
# - Search not working → Check extensions: \dx in psql

# Full re-deployment (safest option)
./deploy_database.sh
```

### Performance Issues

#### Deployment is very slow (>5 minutes)

**Cause**: Rate limiting or network latency

**Solution**:
```bash
# Check current batch size
grep BATCH_SIZE .env

# Reduce batch size to avoid rate limits
# Edit .env: BATCH_SIZE=4

# Monitor API calls during deployment
# The script shows progress for each batch

# Check network connectivity
ping ai.google.dev
```

### Getting Help

If issues persist after trying these solutions:

1. **Check detailed logs**:
   ```bash
   # PostgreSQL logs
   docker logs mcp-postgres --tail 100

   # Deployment script output (run in verbose mode)
   ./deploy_database.sh 2>&1 | tee deployment.log
   ```

2. **Get comprehensive status**:
   ```bash
   ./verify_database.sh --report > status_report.txt
   cat status_report.txt
   ```

3. **Test individual components**:
   ```bash
   # Test database connection
   python3 -c "import psycopg2; from dotenv import load_dotenv; import os; load_dotenv(); print('✅ Can import required packages')"

   # Test Google API
   python3 -c "import google.genai; print('✅ Google GenAI available')"
   ```

4. **Review environment**:
   ```bash
   # Check all environment variables (⚠️ be careful not to expose secrets)
   cat .env | grep -v "PASSWORD\|API_KEY"
   ```

## Performance

| Metric | Value |
|--------|-------|
| Products Processed | 90 |
| Total Time | ~90 seconds |
| Processing Rate | ~1 product/second |
| API Calls | 90 |
| Embeddings Generated | 90 |
| Embedding Dimensions | 1536 |
| Batch Size | 8 |

## Development

### Running Tests

```bash
# Test pagination
cd examples
bash test_pagination.sh

# Test SQL queries
docker exec -i mcp-postgres psql -U mcp_user -d mcpdb < test_pagination_persistence.sql
```

### Modifying Batch Size

```bash
# Edit .env
BATCH_SIZE=16  # Faster, but risk of rate limits
BATCH_SIZE=4   # Slower, safer for rate limits
```

### Adding New Products

1. Add products to `data/products.json`
2. Run populate script: `python3 src/populate-db.py`
3. The script automatically handles UPSERT (updates existing, inserts new)

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review PostgreSQL logs: `docker logs mcp-postgres`
3. Check script logs (console output)
4. Verify environment variables are correctly set

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly with the provided dataset
5. Submit a pull request

### Development Guidelines

- Follow PEP 8 for Python code
- Add docstrings to all functions
- Update README.md for new features
- Include examples for new functionality
- Test with different batch sizes

## References

- **PostgreSQL pgvector**: https://github.com/pgvector/pgvector
- **Google Gemini Embedding API**: https://ai.google.dev/gemini-api/docs/embeddings
- **psycopg2 Documentation**: https://www.psycopg.org/docs/
- **python-dotenv**: https://github.com/theskumar/python-dotenv
- **PostgreSQL Trigram Extension**: https://www.postgresql.org/docs/current/pgtrgm.html

## License

This project is part of Lab01-MCP. See the root project LICENSE file for details.

## Project Status

Active development. Current version supports:
- ✅ Database initialization with pgvector
- ✅ Product data population with embeddings
- ✅ Fuzzy search capabilities
- ✅ Semantic vector search
- ✅ Pagination context management
- ✅ 90-product test dataset

---

**Last Updated**: October 2025
**Database Version**: PostgreSQL 15 + pgvector 0.8.1
**Python Version**: 3.10+
