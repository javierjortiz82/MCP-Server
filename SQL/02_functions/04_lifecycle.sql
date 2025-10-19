-- ============================================================================
-- SESSION LIFECYCLE FUNCTIONS - Archiving and GDPR compliance
-- ============================================================================

-- ============================================================================
-- FUNCTION: archive_inactive_sessions() - Soft delete
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.archive_inactive_sessions(
    p_inactivity_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    session_id UUID,
    customer_email VARCHAR(255),
    last_activity_at TIMESTAMPTZ,
    days_inactive INTEGER
) AS $$
BEGIN
    RETURN QUERY
    UPDATE :'SCHEMA_NAME'.conversation_sessions cs
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

-- ============================================================================
-- FUNCTION: cleanup_archived_sessions() - Hard delete
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.cleanup_archived_sessions(
    p_archived_days INTEGER DEFAULT 365
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM :'SCHEMA_NAME'.conversation_sessions
        WHERE archived = TRUE
          AND updated_at < CURRENT_TIMESTAMP - (p_archived_days || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: cleanup_anonymous_sessions() - Anonymous session cleanup
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.cleanup_anonymous_sessions(
    p_inactive_days INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM :'SCHEMA_NAME'.conversation_sessions
        WHERE customer_email IS NULL
          AND last_activity_at < CURRENT_TIMESTAMP - (p_inactive_days || ' days')::INTERVAL
        RETURNING id
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;

    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: get_session_retention_stats() - Analytics
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.get_session_retention_stats()
RETURNS TABLE (
    metric VARCHAR(50),
    count BIGINT,
    percentage NUMERIC(5,2)
) AS $$
DECLARE
    v_total_sessions BIGINT;
BEGIN
    -- Get total sessions for percentage calculation
    SELECT COUNT(*) INTO v_total_sessions FROM :'SCHEMA_NAME'.conversation_sessions;

    IF v_total_sessions = 0 THEN
        v_total_sessions := 1;  -- Avoid division by zero
    END IF;

    -- Active sessions (not archived)
    RETURN QUERY
    SELECT
        'active_sessions'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE archived = FALSE;

    -- Archived sessions
    RETURN QUERY
    SELECT
        'archived_sessions'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE archived = TRUE;

    -- Sessions with email (valuable)
    RETURN QUERY
    SELECT
        'with_email'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE customer_email IS NOT NULL;

    -- Anonymous sessions
    RETURN QUERY
    SELECT
        'anonymous'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE customer_email IS NULL;

    -- Active last 7 days
    RETURN QUERY
    SELECT
        'active_7d'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE last_activity_at >= CURRENT_TIMESTAMP - INTERVAL '7 days';

    -- Active last 30 days
    RETURN QUERY
    SELECT
        'active_30d'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE last_activity_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- Inactive > 90 days (eligible for archiving)
    RETURN QUERY
    SELECT
        'eligible_archive'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE archived = FALSE
      AND last_activity_at < CURRENT_TIMESTAMP - INTERVAL '90 days';

    -- Archived > 365 days (eligible for deletion)
    RETURN QUERY
    SELECT
        'eligible_delete'::VARCHAR(50),
        COUNT(*),
        ROUND((COUNT(*) * 100.0 / v_total_sessions), 2)
    FROM :'SCHEMA_NAME'.conversation_sessions
    WHERE archived = TRUE
      AND updated_at < CURRENT_TIMESTAMP - INTERVAL '365 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.archive_inactive_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.cleanup_archived_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.cleanup_anonymous_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.get_session_retention_stats() TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Session lifecycle functions created:';
    RAISE NOTICE '   - archive_inactive_sessions() for soft delete';
    RAISE NOTICE '   - cleanup_archived_sessions() for hard delete';
    RAISE NOTICE '   - cleanup_anonymous_sessions() for quick cleanup';
    RAISE NOTICE '   - get_session_retention_stats() for analytics';
END $$;
