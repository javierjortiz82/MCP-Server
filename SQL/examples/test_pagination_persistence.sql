-- ============================================================================
-- PAGINATION PERSISTENCE - Testing Guide
-- ============================================================================
-- Database: mcpdb (port 5434)
-- Schema: test
-- User: mcp_user
-- Password: mcp_password
--
-- This file contains practical examples to test the pagination persistence
-- functionality implemented in the Odiseo Bot.
-- ============================================================================

-- ============================================================================
-- 1. VERIFY TABLE STRUCTURE
-- ============================================================================
-- Check that the pagination_contexts table exists and has correct structure
\dt test.pagination_contexts

-- View table definition
\d test.pagination_contexts

-- Expected columns:
-- - id (serial primary key)
-- - session_id (uuid)
-- - category (varchar(100))
-- - tool_name (varchar(100))
-- - query (text)
-- - current_page (integer)
-- - page_size (integer)
-- - total_items (integer)
-- - products (jsonb)
-- - created_at (timestamp with time zone)
-- - updated_at (timestamp with time zone)
-- - expires_at (timestamp with time zone)


-- ============================================================================
-- 2. VIEW ALL PAGINATION CONTEXTS
-- ============================================================================
-- See all active pagination contexts
SELECT
    id,
    session_id,
    category,
    tool_name,
    query,
    current_page,
    page_size,
    total_items,
    jsonb_array_length(products) as products_count,
    created_at,
    updated_at,
    expires_at,
    CASE
        WHEN expires_at IS NULL THEN 'Never'
        WHEN expires_at > CURRENT_TIMESTAMP THEN 'Active'
        ELSE 'Expired'
    END as status
FROM test.pagination_contexts
ORDER BY created_at DESC;


-- ============================================================================
-- 3. VIEW CONTEXTS FOR SPECIFIC SESSION
-- ============================================================================
-- Replace <session_id> with actual UUID from bot logs
-- Example: 12345678-1234-5678-1234-567812345678
SELECT
    category,
    tool_name,
    query,
    current_page,
    page_size,
    total_items,
    jsonb_array_length(products) as products_count,
    created_at,
    expires_at - CURRENT_TIMESTAMP as time_until_expiration
FROM test.pagination_contexts
WHERE session_id = '<session_id>'
ORDER BY created_at DESC;


-- ============================================================================
-- 4. INSERT TEST DATA MANUALLY
-- ============================================================================
-- Create a test pagination context to verify persistence
-- This simulates what the bot does when saving search results

-- Generate a test session ID (replace with a real UUID or generate one)
-- You can generate UUID with: SELECT gen_random_uuid();

INSERT INTO test.pagination_contexts (
    session_id,
    category,
    tool_name,
    query,
    current_page,
    page_size,
    total_items,
    products,
    expires_at
) VALUES (
    '12345678-1234-5678-1234-567812345678',  -- Test session ID
    'laptops gaming baratos estudiantes',     -- Category (4 words)
    'search_products',                        -- Tool name
    'laptops gaming baratos para estudiantes', -- Original query
    0,                                        -- Current page
    4,                                        -- Page size
    12,                                       -- Total items
    '[
        {"id": "LAPTOP001", "name": "Laptop Gaming Acer Nitro 5", "price": 899.99},
        {"id": "LAPTOP002", "name": "Laptop Gaming ASUS TUF", "price": 799.99},
        {"id": "LAPTOP003", "name": "Laptop Gaming HP Pavilion", "price": 749.99},
        {"id": "LAPTOP004", "name": "Laptop Gaming Lenovo Legion", "price": 999.99},
        {"id": "LAPTOP005", "name": "Laptop Gaming MSI GF63", "price": 699.99},
        {"id": "LAPTOP006", "name": "Laptop Gaming Dell G15", "price": 849.99},
        {"id": "LAPTOP007", "name": "Laptop Gaming Acer Predator", "price": 1299.99},
        {"id": "LAPTOP008", "name": "Laptop Gaming ASUS ROG", "price": 1499.99},
        {"id": "LAPTOP009", "name": "Laptop Gaming HP OMEN", "price": 1199.99},
        {"id": "LAPTOP010", "name": "Laptop Gaming Lenovo IdeaPad", "price": 649.99},
        {"id": "LAPTOP011", "name": "Laptop Gaming MSI Katana", "price": 899.99},
        {"id": "LAPTOP012", "name": "Laptop Gaming Dell Alienware", "price": 1799.99}
    ]'::jsonb,
    CURRENT_TIMESTAMP + INTERVAL '24 hours'  -- Expires in 24 hours
)
ON CONFLICT (session_id, category)
DO UPDATE SET
    current_page = EXCLUDED.current_page,
    updated_at = CURRENT_TIMESTAMP;

-- Verify insertion
SELECT
    category,
    current_page,
    page_size,
    total_items,
    jsonb_array_length(products) as products_count,
    created_at
FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678';


-- ============================================================================
-- 5. TEST UPSERT BEHAVIOR (ON CONFLICT DO UPDATE)
-- ============================================================================
-- This tests what happens when the bot advances to the next page
-- Same session_id + category should UPDATE, not create duplicate

UPDATE test.pagination_contexts
SET
    current_page = 1,  -- Advanced to page 1
    updated_at = CURRENT_TIMESTAMP
WHERE
    session_id = '12345678-1234-5678-1234-567812345678'
    AND category = 'laptops gaming baratos estudiantes';

-- Verify update (should see updated_at changed, current_page = 1)
SELECT
    category,
    current_page,
    page_size,
    created_at,
    updated_at,
    updated_at - created_at as time_since_creation
FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678';


-- ============================================================================
-- 6. TEST TTL EXPIRATION
-- ============================================================================
-- View contexts that are about to expire
SELECT
    session_id,
    category,
    query,
    created_at,
    expires_at,
    expires_at - CURRENT_TIMESTAMP as time_remaining,
    CASE
        WHEN expires_at < CURRENT_TIMESTAMP THEN 'EXPIRED'
        WHEN expires_at - CURRENT_TIMESTAMP < INTERVAL '1 hour' THEN 'EXPIRING SOON'
        ELSE 'ACTIVE'
    END as status
FROM test.pagination_contexts
ORDER BY expires_at;

-- Manually expire a context for testing (set expires_at to past)
UPDATE test.pagination_contexts
SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 hour'
WHERE session_id = '12345678-1234-5678-1234-567812345678'
  AND category = 'laptops gaming baratos estudiantes';

-- Run cleanup function (deletes expired contexts)
SELECT test.cleanup_expired_pagination_contexts();

-- Check if expired context was deleted
SELECT COUNT(*) as remaining_contexts
FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678';


-- ============================================================================
-- 7. MONITOR PAGINATION ACTIVITY
-- ============================================================================
-- See most recently created contexts
SELECT
    session_id,
    category,
    tool_name,
    current_page,
    page_size,
    total_items,
    created_at
FROM test.pagination_contexts
ORDER BY created_at DESC
LIMIT 10;

-- See most recently updated contexts (pages advanced)
SELECT
    session_id,
    category,
    current_page,
    updated_at,
    updated_at - created_at as session_duration
FROM test.pagination_contexts
ORDER BY updated_at DESC
LIMIT 10;

-- Count contexts per session
SELECT
    session_id,
    COUNT(*) as context_count,
    MIN(created_at) as session_start,
    MAX(updated_at) as last_activity
FROM test.pagination_contexts
GROUP BY session_id
ORDER BY last_activity DESC;


-- ============================================================================
-- 8. QUERY SPECIFIC PRODUCTS FROM JSONB
-- ============================================================================
-- Extract product information from JSONB column
SELECT
    category,
    query,
    current_page,
    jsonb_array_length(products) as total_products,
    jsonb_pretty(products) as all_products
FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678'
LIMIT 1;

-- Get products for current page (simulate get_current_page())
WITH context AS (
    SELECT
        category,
        current_page,
        page_size,
        products
    FROM test.pagination_contexts
    WHERE session_id = '12345678-1234-5678-1234-567812345678'
      AND category = 'laptops gaming baratos estudiantes'
)
SELECT
    category,
    current_page,
    jsonb_array_elements(
        jsonb_path_query_array(
            products,
            ('$[' || (current_page * page_size)::text || ' to ' || ((current_page + 1) * page_size - 1)::text || ']')::jsonpath
        )
    ) as product
FROM context;


-- ============================================================================
-- 9. CLEANUP AND MAINTENANCE
-- ============================================================================
-- Delete all contexts for a specific session (simulate bot shutdown)
DELETE FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678';

-- Delete all expired contexts (manual cleanup)
DELETE FROM test.pagination_contexts
WHERE expires_at IS NOT NULL
  AND expires_at < CURRENT_TIMESTAMP;

-- View database size and row counts
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    n_tup_ins as rows_inserted,
    n_tup_upd as rows_updated,
    n_tup_del as rows_deleted
FROM pg_stat_user_tables
WHERE tablename = 'pagination_contexts';


-- ============================================================================
-- 10. REAL-WORLD TESTING WORKFLOW
-- ============================================================================
-- Step 1: Start the bot and note the session_id from logs
--         Look for: "Session: 12345678..."

-- Step 2: Perform a search in the bot
--         Example: "busca laptops gaming baratos"

-- Step 3: Check database to see saved context
SELECT
    category,
    tool_name,
    query,
    current_page,
    page_size,
    total_items,
    jsonb_array_length(products) as products_count
FROM test.pagination_contexts
WHERE session_id = '<your_session_id_here>'
ORDER BY created_at DESC;

-- Step 4: Request more results in the bot
--         Example: "muéstrame más"

-- Step 5: Verify page advancement in database
SELECT
    category,
    current_page,
    updated_at
FROM test.pagination_contexts
WHERE session_id = '<your_session_id_here>'
ORDER BY updated_at DESC;

-- Step 6: Restart the bot (kill and start again)
--         The bot should maintain the same session_id

-- Step 7: Request more results again
--         The bot should load context from DB and continue pagination

-- Step 8: Verify persistence worked
SELECT
    category,
    current_page,
    created_at,
    updated_at,
    updated_at - created_at as total_session_time
FROM test.pagination_contexts
WHERE session_id = '<your_session_id_here>';


-- ============================================================================
-- 11. TROUBLESHOOTING QUERIES
-- ============================================================================
-- Check if table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'test'
    AND table_name = 'pagination_contexts'
) as table_exists;

-- Check constraints
SELECT
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint
WHERE conrelid = 'test.pagination_contexts'::regclass;

-- Check indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'test'
  AND tablename = 'pagination_contexts';

-- Check triggers
SELECT
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'test'
  AND event_object_table = 'pagination_contexts';


-- ============================================================================
-- 12. PERFORMANCE TESTING
-- ============================================================================
-- Measure query performance for loading context
EXPLAIN ANALYZE
SELECT * FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678'
  AND category = 'laptops gaming baratos estudiantes';

-- Test index usage
SET enable_seqscan = off;  -- Force index usage
EXPLAIN ANALYZE
SELECT * FROM test.pagination_contexts
WHERE session_id = '12345678-1234-5678-1234-567812345678';
SET enable_seqscan = on;   -- Re-enable sequential scans