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
\echo '[1/9] Installing PostgreSQL extensions...'
\i '00_init/01_extensions.sql'
\echo ''

\echo '[2/9] Creating schema and configuring permissions...'
\i '00_init/02_schema.sql'
\i '00_init/03_users_permissions.sql'
\echo ''

-- ============================================================================
-- Phase 2: Core Data Tables
-- ============================================================================
\echo '[3/9] Creating products table with indexes...'
\i '01_ddl/01_products.sql'
\echo ''

-- ============================================================================
-- Phase 3: Bookings System
-- ============================================================================
\echo '[4/9] Creating bookings schema (appointments, services, hours)...'
\i '01_ddl/bookings/01_appointments.sql'
\i '01_ddl/bookings/02_service_types.sql'
\i '01_ddl/bookings/03_business_hours.sql'
\i '01_ddl/bookings/04_blocked_times.sql'
\i '01_ddl/bookings/05_service_hours.sql'
\echo ''

-- ============================================================================
-- Phase 4: Email Queue System
-- ============================================================================
\echo '[5/9] Creating email queue system...'
\i '01_ddl/email/01_email_queue.sql'
\echo ''

-- ============================================================================
-- Phase 5: Memory System
-- ============================================================================
\echo '[6/9] Creating multi-agent memory system...'
\i '01_ddl/memory/01_conversation.sql'
\i '01_ddl/memory/02_agent_memory.sql'
\i '01_ddl/memory/03_user_memory.sql'
\echo ''

-- ============================================================================
-- Phase 6: Utility Tables
-- ============================================================================
\echo '[7/9] Creating utility tables (pagination)...'
\i '01_ddl/utils/01_pagination_contexts.sql'
\echo ''

-- ============================================================================
-- Phase 7: Functions and Triggers
-- ============================================================================
\echo '[8/9] Creating functions and triggers...'
\i '02_functions/01_bookings.sql'
\i '02_functions/02_email.sql'
\i '02_functions/03_memory.sql'
\i '02_functions/04_lifecycle.sql'
\echo ''

-- ============================================================================
-- Phase 8: Optional Seed Data
-- ============================================================================
\echo '[9/9] (Optional) Seeding initial data...'
-- Uncomment to enable seed data
-- \i '04_seed/service_types.sql'
-- \i '04_seed/business_hours.sql'
\echo ''

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
WHERE schemaname = 'test'
GROUP BY schemaname;

\echo ''
\echo 'Extensions installed:'
SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'unaccent', 'pg_trgm', 'vector');

\echo ''
\echo 'Ready for deployment! Test with:'
\echo '  - Query existing tables: SELECT * FROM test.products LIMIT 1;'
\echo '  - Test booking availability: SELECT test.is_slot_available(CURRENT_DATE, ''09:00''::TIME, 60);'
\echo '  - Check sessions: SELECT COUNT(*) FROM test.conversation_sessions;'
\echo ''
