-- ============================================================================
-- SESSION LIFECYCLE MANAGEMENT - Archiving and Deletion
-- ============================================================================
-- Implements GDPR-compliant session retention policy with soft delete (archive)
-- and hard delete capabilities for session lifecycle management.
--
-- Features:
--  - Soft archive: Mark inactive sessions as archived (exclude from queries)
--  - Hard delete: Permanently remove old archived sessions
--  - Anonymous cleanup: Fast deletion of sessions without customer_email
--  - Retention stats: Analytics for monitoring
--
-- Prerequisites:
--  - Migration 002 (conversation_sessions table)
--
-- Note: {SCHEMA_NAME} will be substituted by Python script (e.g., "test")
--
-- Migration: 005_add_session_lifecycle.sql
-- Author: Lab01-MCP Team
-- Created: 2025-10-13
-- Version: 1.0.0 (Session Lifecycle Management)
-- ============================================================================

-- ============================================================================
-- SCHEMA CHANGES: Add archived column
-- ============================================================================
ALTER TABLE {SCHEMA_NAME}.conversation_sessions
ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE NOT NULL;

COMMENT ON COLUMN {SCHEMA_NAME}.conversation_sessions.archived IS
'Soft delete flag: TRUE when session is archived (inactive for extended period)';

-- ============================================================================
-- INDEXES: Optimize queries for archived sessions
-- ============================================================================

-- Index for filtering archived sessions (used in most queries)
CREATE INDEX IF NOT EXISTS idx_sessions_archived
ON {SCHEMA_NAME}.conversation_sessions(archived)
WHERE archived = FALSE;

-- Composite index for archiving logic (last_activity_at + archived)
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity_archived
ON {SCHEMA_NAME}.conversation_sessions(last_activity_at, archived);

-- Index for anonymous session cleanup (customer_email NULL)
CREATE INDEX IF NOT EXISTS idx_sessions_email_null
ON {SCHEMA_NAME}.conversation_sessions(customer_email)
WHERE customer_email IS NULL;

-- ============================================================================
-- FUNCTION: archive_inactive_sessions()
-- Soft delete: Mark sessions as archived after N days of inactivity
-- ============================================================================
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.archive_inactive_sessions(
    p_inactivity_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    session_id UUID,
    customer_email VARCHAR(255),
    last_activity_at TIMESTAMPTZ,
    days_inactive INTEGER
) AS $$
BEGIN
    -- Mark sessions as archived if:
    -- 1. Not already archived
    -- 2. Inactive for >= p_inactivity_days
    -- 3. Return affected sessions for logging

    RETURN QUERY
    UPDATE {SCHEMA_NAME}.conversation_sessions cs
    SET
        archived = TRUE,
        updated_at = CURRENT_TIMESTAMP
    WHERE cs.archived = FALSE
      AND cs.last_activity_at < CURRENT_TIMESTAMP - (p_inactivity_days || ' days')::INTERVAL
    RETURNING
        cs.id,
        cs.customer_email,
        cs.last_activity_at,
        EXTRACT(DAY FROM CURRENT_TIMESTAMP - cs.last_activity_at)::INTEGER;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION {SCHEMA_NAME}.archive_inactive_sessions(INTEGER) IS
'Soft delete: Mark inactive sessions as archived. Default: 90 days inactivity.';

-- ============================================================================
-- FUNCTION: cleanup_archived_sessions()
-- Hard delete: Permanently remove archived sessions after N days
-- ============================================================================
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.cleanup_archived_sessions(
    p_archived_days INTEGER DEFAULT 365
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    -- Delete archived sessions that have been archived for >= p_archived_days
    -- Uses CASCADE to delete related data (messages, memory blocks, transfers)

    WITH deleted AS (
        DELETE FROM {SCHEMA_NAME}.conversation_sessions
        WHERE archived = TRUE
          AND updated_at < CURRENT_TIMESTAMP - (p_archived_days || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION {SCHEMA_NAME}.cleanup_archived_sessions(INTEGER) IS
'Hard delete: Permanently remove sessions archived for N days. Default: 365 days.';

-- ============================================================================
-- FUNCTION: cleanup_anonymous_sessions()
-- Fast deletion of sessions without customer_email
-- ============================================================================
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.cleanup_anonymous_sessions(
    p_inactive_days INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    -- Delete anonymous sessions (no customer_email) that are inactive
    -- These have low business value and can be deleted faster

    WITH deleted AS (
        DELETE FROM {SCHEMA_NAME}.conversation_sessions
        WHERE customer_email IS NULL
          AND last_activity_at < CURRENT_TIMESTAMP - (p_inactive_days || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION {SCHEMA_NAME}.cleanup_anonymous_sessions(INTEGER) IS
'Delete anonymous sessions (no email) after N days inactivity. Default: 30 days.';

-- ============================================================================
-- FUNCTION: get_session_retention_stats()
-- Analytics: Get statistics about session retention
-- ============================================================================
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_session_retention_stats()
RETURNS TABLE (
    metric VARCHAR(50),
    count BIGINT,
    percentage NUMERIC(5,2)
) AS $$
DECLARE
    v_total_sessions BIGINT;
BEGIN
    -- Get total sessions for percentage calculation
    SELECT COUNT(*) INTO v_total_sessions FROM {SCHEMA_NAME}.conversation_sessions;

    IF v_total_sessions = 0 THEN
        v_total_sessions := 1;  -- Avoid division by zero
    END IF;

    -- Active sessions (not archived)
    RETURN QUERY
    SELECT
        'active_sessions'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE archived = FALSE;

    -- Archived sessions
    RETURN QUERY
    SELECT
        'archived_sessions'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE archived = TRUE;

    -- Sessions with email (valuable)
    RETURN QUERY
    SELECT
        'with_email'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE customer_email IS NOT NULL;

    -- Anonymous sessions
    RETURN QUERY
    SELECT
        'anonymous'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE customer_email IS NULL;

    -- Active last 7 days
    RETURN QUERY
    SELECT
        'active_7d'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE last_activity_at >= CURRENT_TIMESTAMP - INTERVAL '7 days';

    -- Active last 30 days
    RETURN QUERY
    SELECT
        'active_30d'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE last_activity_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- Inactive > 90 days (eligible for archiving)
    RETURN QUERY
    SELECT
        'eligible_archive'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE archived = FALSE
      AND last_activity_at < CURRENT_TIMESTAMP - INTERVAL '90 days';

    -- Archived > 365 days (eligible for deletion)
    RETURN QUERY
    SELECT
        'eligible_delete'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE archived = TRUE
      AND updated_at < CURRENT_TIMESTAMP - INTERVAL '365 days';

END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION {SCHEMA_NAME}.get_session_retention_stats() IS
'Get retention statistics: active, archived, eligible for archive/delete.';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.archive_inactive_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.cleanup_archived_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.cleanup_anonymous_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_session_retention_stats() TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================
DO $$
DECLARE
    v_total_sessions BIGINT;
    v_active_sessions BIGINT;
    v_archived_sessions BIGINT;
    v_anonymous_sessions BIGINT;
BEGIN
    -- Get current statistics
    SELECT COUNT(*) INTO v_total_sessions FROM {SCHEMA_NAME}.conversation_sessions;
    SELECT COUNT(*) INTO v_active_sessions FROM {SCHEMA_NAME}.conversation_sessions WHERE archived = FALSE;
    SELECT COUNT(*) INTO v_archived_sessions FROM {SCHEMA_NAME}.conversation_sessions WHERE archived = TRUE;
    SELECT COUNT(*) INTO v_anonymous_sessions FROM {SCHEMA_NAME}.conversation_sessions WHERE customer_email IS NULL;

    RAISE NOTICE '✅ Session Lifecycle Management created successfully';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Current Statistics:';
    RAISE NOTICE '   Total sessions: %', v_total_sessions;
    RAISE NOTICE '   Active sessions: %', v_active_sessions;
    RAISE NOTICE '   Archived sessions: %', v_archived_sessions;
    RAISE NOTICE '   Anonymous sessions: %', v_anonymous_sessions;
    RAISE NOTICE '';
    RAISE NOTICE '🔧 Functions available:';
    RAISE NOTICE '   - archive_inactive_sessions(days) - Soft delete inactive sessions';
    RAISE NOTICE '   - cleanup_archived_sessions(days) - Hard delete archived sessions';
    RAISE NOTICE '   - cleanup_anonymous_sessions(days) - Delete anonymous sessions';
    RAISE NOTICE '   - get_session_retention_stats() - Retention analytics';
    RAISE NOTICE '';
    RAISE NOTICE '📖 Usage Examples:';
    RAISE NOTICE '   -- Archive sessions inactive for 90+ days:';
    RAISE NOTICE '   SELECT * FROM {SCHEMA_NAME}.archive_inactive_sessions(90);';
    RAISE NOTICE '';
    RAISE NOTICE '   -- Delete archived sessions older than 365 days:';
    RAISE NOTICE '   SELECT {SCHEMA_NAME}.cleanup_archived_sessions(365);';
    RAISE NOTICE '';
    RAISE NOTICE '   -- Delete anonymous sessions inactive 30+ days:';
    RAISE NOTICE '   SELECT {SCHEMA_NAME}.cleanup_anonymous_sessions(30);';
    RAISE NOTICE '';
    RAISE NOTICE '   -- View retention statistics:';
    RAISE NOTICE '   SELECT * FROM {SCHEMA_NAME}.get_session_retention_stats();';
    RAISE NOTICE '';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '📋 Indexes created:';
    RAISE NOTICE '   - idx_sessions_archived';
    RAISE NOTICE '   - idx_sessions_last_activity_archived';
    RAISE NOTICE '   - idx_sessions_email_null';
    RAISE NOTICE '';
    RAISE NOTICE '⚡ Session Lifecycle ready for production!';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT: Update your cron job to include:';
    RAISE NOTICE '   1. archive_inactive_sessions(90)';
    RAISE NOTICE '   2. cleanup_archived_sessions(365)';
    RAISE NOTICE '   3. cleanup_anonymous_sessions(30)';
END $$;
