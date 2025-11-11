-- ============================================================================
-- EMAIL QUEUE FUNCTIONS - Asynchronous email processing
-- ============================================================================

-- Trigger for updated_at timestamps
DROP TRIGGER IF EXISTS trg_update_email_queue_timestamp ON :SCHEMA_NAME.email_queue;
CREATE TRIGGER trg_update_email_queue_timestamp
    BEFORE UPDATE ON :SCHEMA_NAME.email_queue
    FOR EACH ROW
    EXECUTE FUNCTION :SCHEMA_NAME.update_booking_timestamp();

-- ============================================================================
-- Function: enqueue_email() - Add new email to queue
-- ============================================================================
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.enqueue_email(
    p_type VARCHAR,
    p_recipient_email VARCHAR,
    p_recipient_name VARCHAR,
    p_subject VARCHAR,
    p_body_html TEXT,
    p_body_text TEXT DEFAULT NULL,
    p_booking_id INTEGER DEFAULT NULL,
    p_template_context JSONB DEFAULT NULL,
    p_scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    p_priority INTEGER DEFAULT 5
) RETURNS INTEGER AS $$
DECLARE
    v_email_id INTEGER;
BEGIN
    INSERT INTO :SCHEMA_NAME.email_queue (
        type, recipient_email, recipient_name, subject, body_html, body_text,
        booking_id, template_context, scheduled_for, priority, status
    ) VALUES (
        p_type, p_recipient_email, p_recipient_name, p_subject, p_body_html, p_body_text,
        p_booking_id, p_template_context, p_scheduled_for, p_priority,
        CASE WHEN p_scheduled_for > CURRENT_TIMESTAMP THEN 'scheduled' ELSE 'pending' END
    ) RETURNING id INTO v_email_id;

    RETURN v_email_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: get_pending_emails() - Worker polling function
-- ============================================================================
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.get_pending_emails(
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE (
    id INTEGER,
    type VARCHAR,
    recipient_email VARCHAR,
    recipient_name VARCHAR,
    subject VARCHAR,
    body_html TEXT,
    body_text TEXT,
    retry_count INTEGER,
    max_retries INTEGER,
    booking_id INTEGER,
    template_context JSONB,
    status VARCHAR,
    scheduled_for TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        eq.id, eq.type, eq.recipient_email, eq.recipient_name,
        eq.subject, eq.body_html, eq.body_text,
        eq.retry_count, eq.max_retries, eq.booking_id,
        eq.template_context, eq.status, eq.scheduled_for
    FROM :SCHEMA_NAME.email_queue eq
    WHERE eq.status IN ('pending', 'scheduled')
      AND eq.scheduled_for <= CURRENT_TIMESTAMP
      AND eq.retry_count < eq.max_retries
    ORDER BY eq.priority ASC, eq.scheduled_for ASC
    LIMIT p_limit
    FOR UPDATE SKIP LOCKED;  -- Prevent race conditions between multiple workers
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: update_email_status() - Update email processing status
-- ============================================================================
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.update_email_status(
    p_email_id INTEGER,
    p_status VARCHAR,
    p_error TEXT DEFAULT NULL,
    p_sent_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE :SCHEMA_NAME.email_queue
    SET status = p_status,
        last_error = COALESCE(p_error, last_error),
        sent_at = COALESCE(p_sent_at, sent_at),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_email_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: retry_email() - Retry failed email with exponential backoff
-- ============================================================================
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.retry_email(
    p_email_id INTEGER,
    p_error TEXT,
    p_backoff_seconds INTEGER DEFAULT 300  -- 5 minutes default
) RETURNS VOID AS $$
DECLARE
    v_retry_count INTEGER;
BEGIN
    -- Increment retry count
    UPDATE :SCHEMA_NAME.email_queue
    SET retry_count = retry_count + 1,
        last_error = p_error,
        status = 'pending',  -- Back to pending for retry
        next_retry_at = CURRENT_TIMESTAMP + (p_backoff_seconds * POW(2, retry_count) || ' seconds')::INTERVAL,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_email_id
    RETURNING retry_count INTO v_retry_count;

    -- If max retries exceeded, mark as failed
    IF v_retry_count >= (SELECT max_retries FROM :SCHEMA_NAME.email_queue WHERE id = p_email_id) THEN
        UPDATE :SCHEMA_NAME.email_queue
        SET status = 'failed'
        WHERE id = p_email_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function: cleanup_old_emails() - Maintenance function
-- ============================================================================
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.cleanup_old_emails(
    p_days_to_keep INTEGER DEFAULT 90
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM :SCHEMA_NAME.email_queue
    WHERE status IN ('sent', 'failed')
      AND sent_at < CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION :SCHEMA_NAME.enqueue_email(VARCHAR, VARCHAR, VARCHAR, VARCHAR, TEXT, TEXT, INTEGER, JSONB, TIMESTAMP WITH TIME ZONE, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :SCHEMA_NAME.get_pending_emails(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :SCHEMA_NAME.update_email_status(INTEGER, VARCHAR, TEXT, TIMESTAMP WITH TIME ZONE) TO mcp_user;
GRANT EXECUTE ON FUNCTION :SCHEMA_NAME.retry_email(INTEGER, TEXT, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :SCHEMA_NAME.cleanup_old_emails(INTEGER) TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Email queue functions created:';
    RAISE NOTICE '   - enqueue_email() to add emails';
    RAISE NOTICE '   - get_pending_emails() for worker polling';
    RAISE NOTICE '   - update_email_status() for status tracking';
    RAISE NOTICE '   - retry_email() with exponential backoff';
    RAISE NOTICE '   - cleanup_old_emails() maintenance';
END $$;
