-- ============================================================================
-- Add Missing Unique Constraint to agent_memory_blocks
-- ============================================================================
-- File: SQL/01_ddl/memory/04_add_unique_constraint.sql
-- Purpose: Add unique constraint required by user authentication flow
-- Author: Lab01-MCP Team
-- Created: 2025-11-18
-- Version: 1.0.0
--
-- Issue:
--   The save_session_auth() function in mcp_server/tools/user_management.py:917
--   uses ON CONFLICT (session_id, block_label) but this constraint doesn't exist.
--
-- Fix:
--   Create unique index to enforce one memory block per (session, label) pair.
--
-- Impact:
--   - Enables UPSERT operations in user authentication flow
--   - Prevents duplicate authentication blocks per session
--   - Required for booking agent OTP workflow
--   - Fixes: save_session_auth() ON CONFLICT clause
-- ============================================================================

\echo '[Memory] Adding unique constraint to agent_memory_blocks...'

-- Create unique constraint (idempotent with IF NOT EXISTS)
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_memory_blocks_session_label_unique
ON test.agent_memory_blocks(session_id, block_label);

-- Add documentation comment
COMMENT ON INDEX test.idx_agent_memory_blocks_session_label_unique IS
'Enforces uniqueness of memory blocks per (session_id, block_label) pair. Required for UPSERT operations in user authentication flow (save_session_auth function). Prevents duplicate authentication state blocks (e.g., multiple is_authenticated blocks for same session).';

-- Verification block
DO $$
DECLARE
    constraint_exists BOOLEAN;
    constraint_valid BOOLEAN;
BEGIN
    -- Check if index exists
    SELECT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'test'
          AND tablename = 'agent_memory_blocks'
          AND indexname = 'idx_agent_memory_blocks_session_label_unique'
    ) INTO constraint_exists;

    -- Check if index is unique
    SELECT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'test'
          AND tablename = 'agent_memory_blocks'
          AND indexname = 'idx_agent_memory_blocks_session_label_unique'
          AND indexdef LIKE '%UNIQUE%'
    ) INTO constraint_valid;

    IF constraint_exists AND constraint_valid THEN
        RAISE NOTICE '✅ Unique constraint added successfully';
        RAISE NOTICE '   Schema: test';
        RAISE NOTICE '   Table: agent_memory_blocks';
        RAISE NOTICE '   Index: idx_agent_memory_blocks_session_label_unique';
        RAISE NOTICE '   Columns: (session_id, block_label)';
        RAISE NOTICE '   Purpose: UPSERT operations in save_session_auth()';
    ELSIF constraint_exists THEN
        RAISE WARNING '⚠️  Index exists but may not be unique: %', 'idx_agent_memory_blocks_session_label_unique';
    ELSE
        RAISE EXCEPTION '❌ Failed to create unique constraint on agent_memory_blocks';
    END IF;
END $$;

\echo ''
