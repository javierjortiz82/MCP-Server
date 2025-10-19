# Pagination Persistence - Testing Guide

This directory contains tools to test the PostgreSQL persistence functionality for the Odiseo Bot pagination system.

## 📋 Files

- **test_pagination_persistence.sql** - Comprehensive SQL testing queries (12 sections)
- **test_pagination.sh** - Quick bash script for common operations
- **README_TESTING.md** - This file

## 🚀 Quick Start

### Option 1: Using the Bash Script (Recommended for quick tests)

```bash
# Make script executable
chmod +x test_pagination.sh

# View all commands
./test_pagination.sh

# Insert test data
./test_pagination.sh insert-test

# View all contexts
./test_pagination.sh view-all

# View statistics
./test_pagination.sh stats

# View contexts for specific session
./test_pagination.sh view-session 12345678-1234-5678-1234-567812345678

# Run cleanup
./test_pagination.sh cleanup
```

### Option 2: Using SQL File Directly (Recommended for detailed testing)

```bash
# Connect to PostgreSQL and run all queries interactively
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -f test_pagination_persistence.sql

# Or connect and run queries manually
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb

# Then copy-paste queries from test_pagination_persistence.sql
```

## 📊 Common Testing Workflows

### Workflow 1: Verify Persistence is Working

**Step 1:** Start the bot and note the session_id from logs
```bash
cd /home/javort/Lab01-MCP/client_mcp
python -m cli.main
```

Look for this line in the output:
```
💾 Persistencia de paginación: ACTIVA
   📊 Database: mcpdb (schema: test, port: 5434)
   ⏱️  TTL: 24h | Page size: 4 | Session: 12345678...
```

**Step 2:** Perform a search in the bot
```
Usuario: busca laptops gaming baratos para estudiantes
```

**Step 3:** Check database to verify context was saved
```bash
./test_pagination.sh view-recent
```

**Step 4:** Request more results
```
Usuario: muéstrame más
```

**Step 5:** Verify page advancement in database
```bash
./test_pagination.sh view-session <your_session_id>
```

**Step 6:** Restart the bot (Ctrl+C and start again)

**Step 7:** Request more results again - should continue from where it left off

**Step 8:** Verify persistence worked
```bash
./test_pagination.sh view-session <your_session_id>
```

### Workflow 2: Test with Manual Data

**Step 1:** Insert test data
```bash
./test_pagination.sh insert-test
```

**Step 2:** Note the generated session_id from output

**Step 3:** View the inserted data
```bash
./test_pagination.sh view-session <session_id_from_step_1>
```

**Step 4:** Simulate page advancement (using SQL)
```bash
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -c "
UPDATE test.pagination_contexts
SET current_page = 1, updated_at = CURRENT_TIMESTAMP
WHERE session_id = '<session_id_from_step_1>'
  AND category = 'laptops gaming baratos estudiantes';
"
```

**Step 5:** Verify update
```bash
./test_pagination.sh view-session <session_id_from_step_1>
```

### Workflow 3: Test TTL Expiration

**Step 1:** Insert test data
```bash
./test_pagination.sh insert-test
```

**Step 2:** Manually expire the context (using SQL)
```bash
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -c "
UPDATE test.pagination_contexts
SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 hour'
WHERE category = 'laptops gaming baratos estudiantes';
"
```

**Step 3:** View contexts (should show as expired)
```bash
./test_pagination.sh view-all
```

**Step 4:** Run cleanup function
```bash
./test_pagination.sh cleanup
```

**Step 5:** Verify expired context was deleted
```bash
./test_pagination.sh view-all
```

## 🔍 Detailed SQL Queries

The **test_pagination_persistence.sql** file contains 12 sections:

1. **Verify Table Structure** - Check table exists and has correct schema
2. **View All Contexts** - See all pagination contexts with status
3. **View Session Contexts** - Query specific session
4. **Insert Test Data** - Create sample pagination context
5. **Test UPSERT** - Verify ON CONFLICT DO UPDATE works
6. **Test TTL Expiration** - Test automatic expiration
7. **Monitor Activity** - Track recent activity
8. **Query JSONB Products** - Extract product data
9. **Cleanup** - Delete contexts and run maintenance
10. **Real-World Workflow** - Step-by-step testing guide
11. **Troubleshooting** - Debug queries
12. **Performance Testing** - Measure query performance

## 📈 Monitoring Queries

### View Active Sessions
```sql
SELECT
    session_id,
    COUNT(*) as context_count,
    MIN(created_at) as session_start,
    MAX(updated_at) as last_activity
FROM test.pagination_contexts
GROUP BY session_id
ORDER BY last_activity DESC;
```

### View Contexts Expiring Soon
```sql
SELECT
    session_id,
    category,
    expires_at - CURRENT_TIMESTAMP as time_remaining
FROM test.pagination_contexts
WHERE expires_at IS NOT NULL
  AND expires_at - CURRENT_TIMESTAMP < INTERVAL '1 hour'
ORDER BY expires_at;
```

### View Pagination Statistics
```sql
SELECT
    COUNT(*) as total_contexts,
    COUNT(DISTINCT session_id) as unique_sessions,
    ROUND(AVG(total_items), 2) as avg_products_per_context,
    SUM(total_items) as total_products_cached
FROM test.pagination_contexts;
```

## 🧪 Testing Checklist

- [ ] Table exists and has correct structure
- [ ] Indexes are created (session_id, category, expires_at)
- [ ] Triggers are active (update_pagination_timestamp)
- [ ] UPSERT works (ON CONFLICT DO UPDATE)
- [ ] Context is saved when bot performs search
- [ ] Context is loaded when requesting more results
- [ ] Current_page is updated when advancing pages
- [ ] Context survives bot restart
- [ ] TTL expiration works correctly
- [ ] Cleanup function deletes expired contexts
- [ ] Multiple sessions are isolated (no conflicts)
- [ ] JSONB products are stored and retrieved correctly
- [ ] Performance is acceptable (< 10ms for load_context)

## 🛠️ Troubleshooting

### Issue: Connection refused
**Solution:** Ensure PostgreSQL container is running
```bash
docker ps | grep postgres
# If not running:
cd /home/javort/Lab01-MCP/SQL
docker-compose up -d
```

### Issue: Table doesn't exist
**Solution:** Apply migration
```bash
cd /home/javort/Lab01-MCP/SQL/migrations
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -f 001_add_pagination_contexts.sql
```

### Issue: Permission denied
**Solution:** Grant permissions to mcp_user
```bash
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -c "
GRANT SELECT, INSERT, UPDATE, DELETE ON test.pagination_contexts TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE test.pagination_contexts_id_seq TO mcp_user;
"
```

### Issue: ON CONFLICT not working
**Solution:** Ensure UNIQUE constraint exists
```bash
PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -c "
ALTER TABLE test.pagination_contexts
ADD CONSTRAINT uq_session_category UNIQUE (session_id, category);
"
```

## 📚 Additional Resources

- **Pagination Manager**: `/home/javort/Lab01-MCP/client_mcp/core/pagination_manager.py`
- **Database Adapter**: `/home/javort/Lab01-MCP/client_mcp/core/pagination_db.py`
- **Migration SQL**: `/home/javort/Lab01-MCP/SQL/migrations/001_add_pagination_contexts.sql`
- **Unit Tests**: `/home/javort/Lab01-MCP/client_mcp/test/unit/test_pagination_db.py`
- **Settings**: `/home/javort/Lab01-MCP/client_mcp/.env`

## 💡 Tips

1. **Use the bash script for quick checks** - Faster than typing SQL queries
2. **Use the SQL file for deep diving** - More control and detailed queries
3. **Monitor the updated_at column** - Shows when contexts are actively used
4. **Check expires_at regularly** - Ensure TTL is working correctly
5. **Test with multiple sessions** - Verify isolation between different bot instances
6. **Simulate bot restarts** - Kill and restart to test persistence
7. **Check database size periodically** - Ensure cleanup is working

## 🎯 Expected Results

When persistence is working correctly:

✅ **After search**: Context appears in database with current_page=0
✅ **After "más"**: current_page increments, updated_at changes
✅ **After bot restart**: Context still exists and can be loaded
✅ **After 24 hours**: Context is automatically deleted by cleanup
✅ **Multiple searches**: Each category gets its own context (no overwrites)
✅ **UPSERT**: Same category updates existing context instead of creating duplicate

## 🔗 Database Connection Details

- **Host**: localhost
- **Port**: 5434
- **Database**: mcpdb
- **Schema**: test
- **User**: mcp_user
- **Password**: mcp_password
- **Table**: test.pagination_contexts

## 📞 Support

If you encounter issues:

1. Check PostgreSQL logs: `docker logs mcp-postgres`
2. Verify database connection: `PGPASSWORD=mcp_password psql -h localhost -p 5434 -U mcp_user -d mcpdb -c "SELECT 1;"`
3. Check bot logs for error messages
4. Review unit tests: `python -m pytest test/unit/test_pagination_db.py -v`
