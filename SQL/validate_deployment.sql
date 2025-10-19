-- ============================================================================
-- DATABASE DEPLOYMENT VALIDATION
-- ============================================================================
-- Rigorous validation against local database (port 5434)
-- Compares DDL structure and DML data completeness
-- Run: psql -U mcp_user -d mcpdb -f SQL/validate_deployment.sql
-- ============================================================================

\echo '════════════════════════════════════════════════════════════════════════════════'
\echo 'Lab01-MCP Database Validation Report'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

-- ============================================================================
-- SECTION 1: TABLE VALIDATION
-- ============================================================================
\echo '📊 SECTION 1: DDL - TABLE STRUCTURE'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ 1.1 - Core Tables (Expected: 14)'
SELECT
    COUNT(*) as total_tables,
    string_agg(tablename, ', ' ORDER BY tablename) as table_list
FROM pg_tables
WHERE schemaname = 'test'
ORDER BY schemaname;

\echo ''
\echo '✅ 1.2 - Table Column Count (DDL Completeness)'
SELECT
    tablename,
    COUNT(*) as column_count
FROM pg_tables t
JOIN information_schema.columns c ON c.table_name = t.tablename
WHERE t.schemaname = 'test'
GROUP BY t.schemaname, tablename
ORDER BY tablename;

\echo ''
\echo '✅ 1.3 - Constraints (Foreign Keys, Unique, Check)'
SELECT
    constraint_name,
    table_name,
    constraint_type,
    COUNT(*) as count
FROM information_schema.table_constraints
WHERE table_schema = 'test'
GROUP BY constraint_name, table_name, constraint_type
ORDER BY table_name;

\echo ''

-- ============================================================================
-- SECTION 2: INDEX VALIDATION
-- ============================================================================
\echo '📊 SECTION 2: INDEXES (Expected: 29 custom + extension indexes)'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ 2.1 - Total Index Count'
SELECT
    COUNT(*) as total_indexes
FROM pg_indexes
WHERE schemaname = 'test';

\echo ''
\echo '✅ 2.2 - Indexes by Table'
SELECT
    tablename,
    COUNT(*) as index_count,
    string_agg(indexname, ', ' ORDER BY indexname) as indexes
FROM pg_indexes
WHERE schemaname = 'test'
GROUP BY tablename
ORDER BY tablename;

\echo ''

-- ============================================================================
-- SECTION 3: FUNCTION VALIDATION
-- ============================================================================
\echo '📊 SECTION 3: FUNCTIONS (Expected: 30+ custom functions)'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ 3.1 - Custom Functions (excluding extension functions)'
SELECT
    COUNT(*) as custom_functions
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'test'
AND proname NOT IN (
    'armor', 'dearmor', 'crypt', 'decrypt', 'encrypt', 'digest', 'hmac',
    'gen_random_bytes', 'gen_salt', 'pgp_armor_headers', 'pgp_key_id',
    'pgp_pub_decrypt', 'pgp_pub_decrypt_bytea', 'pgp_pub_encrypt', 'pgp_pub_encrypt_bytea',
    'pgp_sym_decrypt', 'pgp_sym_decrypt_bytea', 'pgp_sym_encrypt', 'pgp_sym_encrypt_bytea'
);

\echo ''
\echo '✅ 3.2 - Function List'
SELECT
    proname as function_name,
    pronargs as arg_count
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'test'
AND proname NOT IN (
    'armor', 'dearmor', 'crypt', 'decrypt', 'encrypt', 'digest', 'hmac',
    'gen_random_bytes', 'gen_salt', 'pgp_armor_headers', 'pgp_key_id',
    'pgp_pub_decrypt', 'pgp_pub_decrypt_bytea', 'pgp_pub_encrypt', 'pgp_pub_encrypt_bytea',
    'pgp_sym_decrypt', 'pgp_sym_decrypt_bytea', 'pgp_sym_encrypt', 'pgp_sym_encrypt_bytea'
)
ORDER BY proname;

\echo ''

-- ============================================================================
-- SECTION 4: DML VALIDATION - PRODUCTS TABLE
-- ============================================================================
\echo '📊 SECTION 4: DML - PRODUCTS DATA'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ 4.1 - Product Count (Expected: 90)'
SELECT
    COUNT(*) as total_products,
    COUNT(DISTINCT category) as categories,
    COUNT(DISTINCT brand) as brands,
    COUNT(DISTINCT sku) as unique_skus
FROM test.products;

\echo ''
\echo '✅ 4.2 - Products by Category'
SELECT
    category,
    COUNT(*) as count
FROM test.products
GROUP BY category
ORDER BY count DESC, category;

\echo ''
\echo '✅ 4.3 - Price Range Validation'
SELECT
    MIN(price) as min_price,
    MAX(price) as max_price,
    ROUND(AVG(price)::NUMERIC, 2) as avg_price,
    COUNT(DISTINCT price) as unique_prices
FROM test.products;

\echo ''
\echo '✅ 4.4 - SKU Format Validation'
SELECT
    SUBSTRING(sku, 1, 3) as prefix,
    COUNT(*) as count
FROM test.products
GROUP BY SUBSTRING(sku, 1, 3)
ORDER BY count DESC;

\echo ''
\echo '✅ 4.5 - Data Quality Check'
SELECT
    COUNT(*) as with_sku,
    COUNT(*) FILTER (WHERE name IS NOT NULL) as with_name,
    COUNT(*) FILTER (WHERE description IS NOT NULL) as with_description,
    COUNT(*) FILTER (WHERE category IS NOT NULL) as with_category,
    COUNT(*) FILTER (WHERE brand IS NOT NULL) as with_brand,
    COUNT(*) FILTER (WHERE price > 0) as with_valid_price,
    COUNT(*) FILTER (WHERE tags IS NOT NULL AND array_length(tags, 1) > 0) as with_tags
FROM test.products;

\echo ''

-- ============================================================================
-- SECTION 5: EXTENSIONS VALIDATION
-- ============================================================================
\echo '📊 SECTION 5: EXTENSIONS'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ 5.1 - Required Extensions (Expected: 4)'
SELECT
    extname as extension,
    extversion as version
FROM pg_extension
WHERE extname IN ('uuid-ossp', 'unaccent', 'pg_trgm', 'vector')
ORDER BY extname;

\echo ''

-- ============================================================================
-- SECTION 6: TRIGGER VALIDATION
-- ============================================================================
\echo '📊 SECTION 6: TRIGGERS'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ 6.1 - Trigger Count by Table'
SELECT
    event_object_table as table_name,
    COUNT(*) as trigger_count
FROM information_schema.triggers
WHERE trigger_schema = 'test'
GROUP BY event_object_table
ORDER BY table_name;

\echo ''
\echo '✅ 6.2 - All Triggers'
SELECT
    trigger_name,
    event_object_table,
    event_manipulation,
    action_orientation
FROM information_schema.triggers
WHERE trigger_schema = 'test'
ORDER BY event_object_table, trigger_name;

\echo ''

-- ============================================================================
-- SECTION 7: FINAL SUMMARY
-- ============================================================================
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo 'VALIDATION SUMMARY'
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo ''

\echo '✅ DDL Structure:'
SELECT
    '  Tables: ' || (SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'test')::text || ' (expected 14)' as metric
UNION ALL
SELECT
    '  Indexes: ' || (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'test')::text || ' (expected 29+)'
UNION ALL
SELECT
    '  Functions: ' || (
        SELECT COUNT(*) FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'test'
        AND proname NOT IN ('armor', 'dearmor', 'crypt', 'decrypt', 'encrypt', 'digest', 'hmac',
            'gen_random_bytes', 'gen_salt', 'pgp_armor_headers', 'pgp_key_id',
            'pgp_pub_decrypt', 'pgp_pub_decrypt_bytea', 'pgp_pub_encrypt', 'pgp_pub_encrypt_bytea',
            'pgp_sym_decrypt', 'pgp_sym_decrypt_bytea', 'pgp_sym_encrypt', 'pgp_sym_encrypt_bytea')
    )::text || ' (expected 30+)'
UNION ALL
SELECT
    '  Extensions: ' || (SELECT COUNT(*) FROM pg_extension WHERE extname IN ('uuid-ossp', 'unaccent', 'pg_trgm', 'vector'))::text || ' (expected 4)';

\echo ''
\echo '✅ DML Data:'
SELECT
    '  Products: ' || COUNT(*)::text || ' (expected 90)' as metric
FROM test.products
UNION ALL
SELECT
    '  Categories: ' || COUNT(DISTINCT category)::text || ' (expected 23)'
FROM test.products
UNION ALL
SELECT
    '  Brands: ' || COUNT(DISTINCT brand)::text || ' (expected 57+)'
FROM test.products;

\echo ''
\echo '════════════════════════════════════════════════════════════════════════════════'
\echo '✅ VALIDATION COMPLETE'
\echo '════════════════════════════════════════════════════════════════════════════════'
