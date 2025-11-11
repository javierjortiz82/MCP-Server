# Unified Data Loader: populate.py

Single entry point for all Lab01-MCP data loading operations.

## Quick Start

```bash
cd SQL/src
python3 populate.py --db                    # Load all tables to database
python3 populate.py --db --table products   # Load only products (with embeddings)
```

## Execution Modes

### Insert to Database (with automatic embedding generation for products)
```bash
# All tables
python3 populate.py --db

# Only products (generates embeddings via Google Gemini)
python3 populate.py --db --table products

# Other specific tables
python3 populate.py --db --table service_types
python3 populate.py --db --table appointments
```

### Generate SQL Files (without database insertion)
```bash
# All tables
python3 populate.py --output-sql-dir ../04_seed/

# Only products (with embeddings in SQL)
python3 populate.py --output-sql-dir ../04_seed/ --table products
```

### Force Embedding Generation (non-database mode)
```bash
# Generate embeddings even when outputting SQL (products only)
python3 populate.py --output-sql-dir ../04_seed/ --embeddings
```

## Configuration

Set in `.env` file:
```
DATABASE_URL=postgresql://user:pass@localhost:5434/mcpdb
GOOGLE_API_KEY=your-gemini-api-key
SCHEMA_NAME=test
EMBEDDING_MODEL=text-embedding-004
OUTPUT_DIMENSIONALITY=1536
BATCH_SIZE=8
```

## Supported Tables

| Table | Source JSON | Embeddings | Notes |
|-------|-------------|-----------|-------|
| products | 01_products.json | ✅ Auto-generated | Uses Google Gemini API |
| service_types | 02_service_types.json | ❌ | 5 records |
| business_hours | 03_business_hours.json | ❌ | 6 records |
| blocked_times | 04_blocked_times.json | ❌ | 25 records |
| service_hours | 05_service_hours.json | ❌ | 6 records |
| appointments | 06_appointments.json | ❌ | Empty seed |
| email_queue | 07_email_queue.json | ❌ | Empty seed |
| conversation_sessions | 08_conversation_sessions.json | ❌ | Empty seed |
| conversation_messages | 09_conversation_messages.json | ❌ | Empty seed |
| agent_memory_blocks | 10_agent_memory_blocks.json | ❌ | Empty seed |
| user_memory_profiles | 11_user_memory_profiles.json | ❌ | Empty seed |
| user_memory_blocks | 12_user_memory_blocks.json | ❌ | Empty seed |
| agent_context_transfers | 13_agent_context_transfers.json | ❌ | Empty seed |
| pagination_contexts | 14_pagination_contexts.json | ❌ | Empty seed |

## Key Features

### For Products Table
- **Automatic Embedding Generation**: Generates 1536-dimensional vectors via Google Gemini
- **On-the-Fly Processing**: Embeddings created during insertion (not pre-computed)
- **Semantic Text**: Combines name + description + brand + category + tags
- **Retry Logic**: Exponential backoff (2s→30s, 5 attempts) via tenacity
- **Rate Limiting**: 50ms delay between API calls

### For Other Tables
- **Generic JSON Loading**: Simple field mapping from JSON
- **Batch Insertion**: page_size=100 for efficient PostgreSQL writes
- **ON CONFLICT Handling**: Graceful upserts without error on duplicates
- **No API Dependency**: Runs without Google API key

## Output Examples

### Database Insertion
```
[INFO] Loaded 90 records from products.json
[INFO] Processing 90 products for embeddings...
[INFO] Generated embeddings for 8/90 products
[INFO] Generated embeddings for 16/90 products
...
[INFO] ✅ All 90 products processed
[INFO] ✅ Inserted 90 records to products
```

### SQL File Generation
```
[INFO] Generating SQL INSERT for products with embeddings...
[INFO] ✅ SQL generated to ../04_seed/products.sql
```

Generated SQL includes:
- `ALTER TABLE ... DISABLE TRIGGER ALL` for performance
- Product records with vector embeddings: `'{[1.23, -0.45, ...]}'::vector`
- `ALTER TABLE ... ENABLE TRIGGER ALL` for safety

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "DATABASE_URL not in .env" | Create .env from .env.example |
| "Google Gemini not available" | Install: `pip install google-genai` |
| "psycopg2 required" | Install: `pip install psycopg2-binary` |
| "pgvector not available" | Install: `pip install pgvector` (for products) |
| "GOOGLE_API_KEY not found" | Set GOOGLE_API_KEY in .env (required for products) |
| Timeout on embeddings | Check network connectivity to Google API |
| "File not found" warnings | Ensure JSON files exist in @SQL/data/ |

## Performance Considerations

- **Products insertion time**: ~5-10 minutes for 90 products (includes API calls)
- **Other tables**: ~1-2 seconds each
- **SQL generation**: Instant
- **Memory usage**: Minimal (<100MB for all tables)

## Integration with deploy.sql

The master deployment script can be updated to use the unified loader:

```sql
-- In deploy.sql, replace Phase 9:
\\echo '[9/9] Seeding data using unified loader...'
\\! cd ../src && python3 populate.py --db

-- Or for SQL generation first:
\\! cd ../src && python3 populate.py --output-sql-dir ../04_seed/
```

## File Structure

```
@SQL/
├── data/
│   ├── 01_products.json (90 products, no embeddings)
│   ├── 02_service_types.json
│   ├── 03_business_hours.json
│   └── ...
├── src/
│   ├── populate.py (this unified script)
│   └── USAGE.md (this file)
├── 04_seed/
│   ├── products.sql (generated by --output-sql-dir)
│   ├── service_types.sql
│   └── ...
└── deploy.sql (master deployment orchestrator)
```

## Development Notes

- Single unified entry point replaces separate populate.py and populate_products.py
- Products get special handling: `if table_name == "products"`
- All table metadata in TABLES list for easy extension
- Conditional logic: products → embeddings + Google API, others → generic JSON
- Error handling with graceful degradation (missing API key, pgvector, etc.)

---

**Last Updated**: 2025-10-18  
**Unified Version**: 1.0  
**Source Files**: populate.py (13 KB merged from 2 original scripts)
