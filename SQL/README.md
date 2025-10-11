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

### Tables Created

#### `test.products`

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `sku` | TEXT | Unique product identifier |
| `name` | TEXT | Product name |
| `description` | TEXT | Product description |
| `category` | TEXT | Product category |
| `brand` | TEXT | Brand name |
| `tags` | TEXT[] | Array of tags |
| `color` | TEXT | Product color |
| `size` | TEXT | Product size |
| `price` | NUMERIC(12,2) | Product price |
| `embedding` | VECTOR(1536) | Gemini embedding vector |

**Indexes**: 15 optimized indexes including:
- Trigram indexes for fuzzy search
- Vector indexes (IVFFlat) for semantic search
- Full-text search indexes
- Tag and SKU indexes

#### `test.pagination_contexts`

Session-based pagination context storage with automatic cleanup.

### Functions Created

- `normalize_text(text)` - Text normalization (lowercase, no accents)
- `get_similarity_threshold()` - Returns configurable similarity threshold (0.3)
- `cleanup_expired_pagination_contexts()` - Cleans expired pagination data
- `update_pagination_timestamp()` - Auto-updates timestamps on updates

### Extensions Enabled

- `vector` - pgvector for embeddings
- `pg_trgm` - Trigram similarity search
- `unaccent` - Accent-insensitive search
- `uuid-ossp` - UUID generation
- `pgcrypto` - Cryptographic functions

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
