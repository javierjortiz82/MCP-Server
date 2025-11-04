-- ============================================================================
-- MASTER DEPLOYMENT SCRIPT - Lab01-MCP Database Schema
-- ============================================================================
-- Ejecutar: psql -U mcp_user -d mcpdb -f deploy.sql
--
-- Este script ejecuta en orden todas las migraciones DDL/DML
-- asegurando coherencia y dependencias entre tablas
--
-- Order of execution:
-- 1. Extensions and initialization
-- 2. Schema creation and permissions
-- 3. Products table (base catalog)
-- 4. Bookings system (appointments, services, hours)
-- 5. Email queue system
-- 6. Memory system (conversations, agents, users)
-- 7. Utility tables (pagination)
-- 8. All functions (bookings, email, memory, lifecycle)
-- 9. Seed data (optional)
-- ============================================================================

\echo '======================================================================'
\echo 'Lab01-MCP Database Deployment'
\echo '======================================================================'
\echo ''

-- ============================================================================
-- Phase 1: Initialize Database
-- ============================================================================
\echo '[1/11] Installing PostgreSQL extensions...'
\i '../00_init/01_extensions.sql'
\echo ''

\echo '[2/11] Creating schema and configuring permissions...'
\i '../00_init/02_schema.sql'
\i '../00_init/03_users_permissions.sql'
\echo ''

-- ============================================================================
-- Phase 2: Core Data Tables
-- ============================================================================
\echo '[3/11] Creating products table with indexes...'
\i '../01_ddl/01_products.sql'
\echo ''

-- ============================================================================
-- Phase 3: Bookings System
-- ============================================================================
\echo '[4/11] Creating bookings schema (appointments, services, hours)...'
\i '../01_ddl/bookings/01_appointments.sql'
\i '../01_ddl/bookings/02_service_types.sql'
\i '../01_ddl/bookings/03_business_hours.sql'
\i '../01_ddl/bookings/04_blocked_times.sql'
\i '../01_ddl/bookings/05_service_hours.sql'
\echo ''

-- ============================================================================
-- Phase 4: Email Queue System
-- ============================================================================
\echo '[5/11] Creating email queue system...'
\i '../01_ddl/email/01_email_queue.sql'
\echo ''

-- ============================================================================
-- Phase 5: Memory System
-- ============================================================================
\echo '[6/11] Creating multi-agent memory system...'
\i '../01_ddl/memory/01_conversation.sql'
\i '../01_ddl/memory/02_agent_memory.sql'
\i '../01_ddl/memory/03_user_memory.sql'
\echo ''

-- ============================================================================
-- Phase 6: Utility Tables
-- ============================================================================
\echo '[7/10] Creating utility tables (pagination)...'
\i '../01_ddl/utils/01_pagination_contexts.sql'
\echo ''

-- ============================================================================
-- Phase 7: Demo System (Token-Bucket Rate Limiting)
-- ============================================================================
\echo '[8/10] Creating demo system tables (token-bucket, audit, sessions, users, otp)...'
\i '../01_ddl/demo/01_demo_usage.sql'
\i '../01_ddl/demo/02_demo_audit_log.sql'
\i '../01_ddl/demo/03_demo_sessions.sql'
\i '../01_ddl/demo/04_demo_users.sql'
\i '../01_ddl/demo/05_demo_otp_codes.sql'
\echo ''

-- ============================================================================
-- Phase 8: Indexes (Consolidated for maintainability)
-- ============================================================================
\echo '[9/11] Creating consolidated indexes...'
\i '../03_indexes/01_indexes.sql'
\echo ''

-- ============================================================================
-- Phase 9: Functions and Triggers
-- ============================================================================
\echo '[10/10] Creating functions and triggers...'
\i '../02_functions/01_bookings.sql'
\i '../02_functions/02_email.sql'
\i '../02_functions/03_memory.sql'
\i '../02_functions/04_lifecycle.sql'
\i '../02_functions/05_memory_sync.sql'
\echo ''

-- ============================================================================
-- Phase 10: Seed Data (DML - Complete data loading)
-- ============================================================================
-- NOTE: Data loading is now handled by Python (populate.py --db --embeddings)
--       This ensures embeddings are generated on-the-fly during insertion
--       The following SQL files are kept for reference but not executed
-- ============================================================================
\echo '[11/11] Data loading phase...'
\echo 'NOTE: Seed data will be loaded via populate.py (bash script handles this)'
\echo ''
-- \i '../04_seed/01_products_data.sql'
-- \i '../04_seed/02_service_types_data.sql'
-- \i '../04_seed/03_business_hours_data.sql'
-- \i '../04_seed/04_blocked_times_data.sql'

-- ============================================================================
-- Final Summary
-- ============================================================================
\echo '======================================================================'
\echo '✅ Database deployment completed successfully!'
\echo '======================================================================'
\echo ''

-- Verification query
\echo 'Deployment Summary:'
\echo '---'
SELECT
    schemaname,
    COUNT(*) as table_count,
    string_agg(tablename, ', ' ORDER BY tablename) as tables
FROM pg_tables
WHERE schemaname = :'SCHEMA_NAME'
GROUP BY schemaname;

\echo ''
\echo 'Extensions installed:'
SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'unaccent', 'pg_trgm', 'vector');

\echo ''
\echo 'Deployment complete! Next steps:'
\echo '  - Run verification: ./scripts/verify.sh'
\echo '  - Query data: SELECT * FROM 'test'.products LIMIT 1;'
\echo '  - Check functions: SELECT 'test'.is_slot_available(CURRENT_DATE, ''09:00''::TIME, 60);'
\echo ''
