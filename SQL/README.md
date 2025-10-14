# SQL - Database Initialization and Population Scripts

Database initialization and data population tools for Lab01-MCP PostgreSQL database with vector embeddings support.

## Description

This directory contains Python scripts and SQL utilities to initialize and populate a PostgreSQL database with product data, including automatic generation of multilingual embeddings using Google Gemini AI. The database is optimized for fuzzy search, semantic search, and pagination features.

## Features

- **Automated Database Initialization**: Creates schemas, tables, indexes, and functions
- **Vector Embeddings**: Automatic generation of 1536-dimensional embeddings using Google Gemini
- **Fuzzy Search Support**: Trigram-based search with accent and case insensitivity
- **Pagination System**: Persistent pagination context storage for stateful sessions
- **UPSERT Operations**: Smart insert/update of products without duplicates
- **Batch Processing**: Configurable batch size for API calls with retry logic
- **Multilingual Support**: Embeddings optimized for Spanish and English
- **90 Product Dataset**: Pre-loaded with 90 realistic products (laptops, electronics, etc.)

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

```bash
# 1. Initialize database (create schema, tables, indexes)
python3 src/init-db.py

# 2. Populate with products and embeddings
python3 src/populate-db.py
```

### Using Shell Scripts

```bash
# Initialize database
./scripts/init-db.sh

# Populate database
./scripts/populate-db.sh
```

### Verify Installation

```bash
# Check products count
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT COUNT(*) FROM test.products;"

# Check embeddings
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "SELECT COUNT(*) FROM test.products WHERE embedding IS NOT NULL;"
```

Expected output: **90 products** with embeddings

## Project Structure

```
SQL/
├── data/
│   └── products.json          # 90 products dataset (laptops, electronics)
├── src/
│   ├── init-db.py             # Database initialization script (324 lines)
│   └── populate-db.py         # Data population with embeddings (221 lines)
├── scripts/
│   ├── init-db.sh             # Shell wrapper for init-db.py
│   └── populate-db.sh         # Shell wrapper for populate-db.py
├── examples/
│   ├── README_TESTING.md      # Testing guide
│   ├── test_pagination.sh     # Pagination test script
│   └── test_pagination_persistence.sql  # SQL pagination tests
├── .env                       # Environment configuration (DO NOT commit)
├── .env.example               # Environment template (safe to commit)
└── README.md                  # This file
```

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

### Error: "DATABASE_URL not found"

**Cause**: Missing `.env` file or incorrect variable name

**Solution**:
```bash
# Copy example file
cp .env.example .env

# Edit with your credentials
nano .env
```

### Error: "GOOGLE_API_KEY not found"

**Cause**: Missing or invalid Google API key

**Solution**:
1. Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Add to `.env`:
   ```bash
   GOOGLE_API_KEY=AIzaSy...
   ```

### Error: "Embedding response not contains embedding"

**Cause**: API structure change or outdated `google-genai` package

**Solution**:
```bash
# Update package
pip install --upgrade google-genai

# The script has automatic fallback handling
```

### Rate Limiting (429 Error)

**Cause**: Too many API calls

**Solution**:
```bash
# Reduce batch size in .env
BATCH_SIZE=4

# The script has automatic retry with exponential backoff
```

### PostgreSQL Connection Failed

**Cause**: Container not running or incorrect credentials

**Solution**:
```bash
# Check container status
docker ps | grep mcp-postgres

# Start container if needed
cd ../DockerConfig && ./start.sh

# Verify connection
docker exec mcp-postgres psql -U mcp_user -d mcpdb -c "\dt test.*"
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
