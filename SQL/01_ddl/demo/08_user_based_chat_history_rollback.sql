-- ============================================================================
-- Rollback: User-Based Chat History Migration
-- File: SQL/01_ddl/demo/08_user_based_chat_history_rollback.sql
-- Author: Claude Code (Anthropic AI)
-- Date: 2025-11-09
-- Version: 1.0.0
--
-- Description:
--   Rolls back the user-based chat history migration.
--   Restores session-based architecture.
--
-- WARNING:
--   This will remove user_id from conversation_messages.
--   Chat history will revert to session-based (per-device).
--
-- Usage:
--   psql -U mcp_user -d mcpdb -v SCHEMA_NAME=test \
--     -f SQL/01_ddl/demo/08_user_based_chat_history_rollback.sql
-- ============================================================================

\echo '========================================================================'
\echo 'ROLLBACK: User-Based Chat History Migration'
\echo '========================================================================'

-- Set schema
SET search_path TO :SCHEMA_NAME;

-- ============================================================================
-- STEP 1: Drop index
-- ============================================================================

\echo ''
\echo '[1/3] Dropping user_id index...'

DROP INDEX IF EXISTS idx_conv_messages_user_created;

\echo '✓ Index dropped'

-- ============================================================================
-- STEP 2: Remove user_id column
-- ============================================================================

\echo '[2/3] Removing user_id column from conversation_messages...'

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'conversation_messages'
          AND column_name = 'user_id'
    ) THEN
        ALTER TABLE conversation_messages DROP COLUMN user_id;
        RAISE NOTICE '✓ Removed user_id column';
    ELSE
        RAISE NOTICE '⚠ user_id column does not exist (already rolled back)';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Revert language defaults to Spanish
-- ============================================================================

\echo '[3/3] Reverting language defaults to Spanish (es)...'

-- Revert demo_users default
ALTER TABLE demo_users
ALTER COLUMN preferred_language SET DEFAULT 'es';

-- Revert demo_sessions default
ALTER TABLE demo_sessions
ALTER COLUMN language SET DEFAULT 'es';

\echo '✓ Language defaults reverted to ''es'''

\echo ''
\echo '========================================================================'
\echo '✓ Rollback completed successfully'
\echo '========================================================================'
\echo ''
\echo 'WARNING: Chat history is now session-based (per-device).'
\echo 'Users will not see chat history across devices.'
\echo ''
