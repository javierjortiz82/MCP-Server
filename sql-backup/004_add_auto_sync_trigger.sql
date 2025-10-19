-- ============================================================================
-- AUTO-SYNC TRIGGER - Automatic Session-to-User Memory Sync
-- ============================================================================
-- Adds automatic synchronization of high-priority session memory blocks
-- to user-level memory when sessions become inactive.
--
-- This eliminates the need to manually call sync_session_to_user_memory().
-- Sessions are auto-synced after 30 minutes of inactivity.
--
-- Prerequisites:
--  - Migration 003 (user memory tables and functions)
--
-- Note: {SCHEMA_NAME} will be substituted by Python script (e.g., "test")
--
-- Migration: 004_add_auto_sync_trigger.sql
-- Author: Lab01-MCP Team
-- Created: 2025-10-13
-- Version: 1.0.0 (Fase 6.1 - Auto-Sync Enhancement)
-- ============================================================================

-- ============================================================================
-- FUNCTION: auto_sync_inactive_sessions()
-- Automatically sync sessions that have been inactive for >30 minutes
-- ============================================================================
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.auto_sync_inactive_sessions(
    p_inactivity_minutes INTEGER DEFAULT 30
)
RETURNS TABLE (
    session_id UUID,
    customer_email VARCHAR(255),
    synced_blocks INTEGER,
    updated_blocks INTEGER
) AS $$
DECLARE
    v_session RECORD;
    v_sync_result RECORD;
BEGIN
    -- Find sessions that need auto-sync:
    -- 1. Inactive for >= p_inactivity_minutes
    -- 2. Have customer_email
    -- 3. Have high-priority blocks not yet synced
    FOR v_session IN
        SELECT DISTINCT cs.id, cs.session_id, cs.customer_email
        FROM {SCHEMA_NAME}.conversation_sessions cs
        WHERE cs.customer_email IS NOT NULL
          AND cs.last_activity_at < CURRENT_TIMESTAMP - (p_inactivity_minutes || ' minutes')::INTERVAL
          AND EXISTS (
              -- Has high-priority blocks
              SELECT 1
              FROM {SCHEMA_NAME}.agent_memory_blocks amb
              WHERE amb.session_id = cs.id
                AND amb.priority >= 7
                AND amb.agent_scope = 'shared'
                AND (amb.expires_at IS NULL OR amb.expires_at > CURRENT_TIMESTAMP)
          )
        LIMIT 100  -- Process max 100 sessions per call
    LOOP
        -- Sync this session
        BEGIN
            SELECT * INTO v_sync_result
            FROM {SCHEMA_NAME}.sync_session_to_user_memory(v_session.id);

            -- Only return sessions that actually synced blocks
            IF v_sync_result.synced_blocks > 0 OR v_sync_result.updated_blocks > 0 THEN
                session_id := v_session.session_id;
                customer_email := v_session.customer_email;
                synced_blocks := v_sync_result.synced_blocks;
                updated_blocks := v_sync_result.updated_blocks;
                RETURN NEXT;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            -- Log error but continue with other sessions
            RAISE WARNING 'Failed to sync session %: %', v_session.session_id, SQLERRM;
        END;
    END LOOP;

    RETURN;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: trigger_auto_sync_on_activity_update()
-- Trigger function that checks if session needs auto-sync when updated
-- ============================================================================
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.trigger_auto_sync_on_activity_update()
RETURNS TRIGGER AS $$
DECLARE
    v_inactivity_minutes INTEGER;
    v_sync_result RECORD;
BEGIN
    -- Only process if:
    -- 1. Session has customer_email
    -- 2. last_activity_at was updated
    -- 3. Previous activity was >30 minutes ago

    IF NEW.customer_email IS NOT NULL
       AND OLD.last_activity_at IS NOT NULL
       AND OLD.last_activity_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
       AND NEW.last_activity_at > OLD.last_activity_at THEN

        -- This session was inactive for >30 min and just became active again
        -- Sync any pending high-priority blocks from previous activity
        BEGIN
            SELECT * INTO v_sync_result
            FROM {SCHEMA_NAME}.sync_session_to_user_memory(OLD.id);

            IF v_sync_result.synced_blocks > 0 OR v_sync_result.updated_blocks > 0 THEN
                RAISE NOTICE 'Auto-synced session % on activity resume: % new, % updated',
                    OLD.session_id,
                    v_sync_result.synced_blocks,
                    v_sync_result.updated_blocks;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            -- Don't fail the update if sync fails
            RAISE WARNING 'Auto-sync failed for session %: %', OLD.session_id, SQLERRM;
        END;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER: Auto-sync on session activity resume
-- ============================================================================
DROP TRIGGER IF EXISTS trg_auto_sync_on_activity_resume ON {SCHEMA_NAME}.conversation_sessions;
CREATE TRIGGER trg_auto_sync_on_activity_resume
    BEFORE UPDATE OF last_activity_at ON {SCHEMA_NAME}.conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.trigger_auto_sync_on_activity_update();

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.auto_sync_inactive_sessions(INTEGER) TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Auto-Sync Trigger System created successfully';
    RAISE NOTICE '';
    RAISE NOTICE '🔧 Functions available:';
    RAISE NOTICE '   - auto_sync_inactive_sessions() - Batch sync inactive sessions';
    RAISE NOTICE '   - trigger_auto_sync_on_activity_update() - Trigger on activity resume';
    RAISE NOTICE '';
    RAISE NOTICE '⚡ Trigger configured:';
    RAISE NOTICE '   - trg_auto_sync_on_activity_resume - Auto-sync when session resumes after 30min';
    RAISE NOTICE '';
    RAISE NOTICE '📖 Usage:';
    RAISE NOTICE '   -- Manual batch sync (for cron job):';
    RAISE NOTICE '   SELECT * FROM {SCHEMA_NAME}.auto_sync_inactive_sessions(30);';
    RAISE NOTICE '';
    RAISE NOTICE '   -- Automatic trigger:';
    RAISE NOTICE '   Trigger fires automatically when session resumes after inactivity';
    RAISE NOTICE '';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '🚀 Auto-Sync ready for production!';
END $$;
