-- ============================================================================
-- EMAIL QUEUE SCHEMA CREATION
-- ============================================================================
-- Creates email queue table for asynchronous email delivery system.
-- Works with email_service worker to send notifications for bookings.
--
-- Features:
--  - Queue-based email delivery (FIFO with priority)
--  - Automatic retry with exponential backoff
--  - Email scheduling (reminders, delayed sends)
--  - Status tracking (pending → processing → sent/failed)
--  - Integration with appointments table
--
-- Prerequisites:
--  - PostgreSQL 14+
--  - Existing schema created by init-db.py
--  - Appointments table (from create_bookings_schema.sql)
--
-- Usage:
--  - Run via Python: python3 SQL/src/init_email_queue.py
--  - Or direct: psql -d mcp_db < SQL/scripts/create_email_queue.sql
--
-- Author: Lab01-MCP Team
-- Created: 2025-10-14
-- Version: 1.0.0
-- ============================================================================

-- Note: SCHEMA_NAME will be substituted by Python script (e.g., "test")

-- ============================================================================
-- EMAIL_QUEUE TABLE - Asynchronous email delivery queue
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.email_queue (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Email classification
    type VARCHAR(50) NOT NULL,
        -- booking_created, booking_cancelled, booking_rescheduled,
        -- reminder_24h, reminder_1h, reminder_custom

    -- Recipient information
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),

    -- Email content
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,  -- Plain text fallback

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending: waiting to be processed
        -- processing: currently being sent
        -- sent: successfully delivered
        -- failed: max retries exceeded
        -- scheduled: waiting for scheduled_for time

    -- Retry logic
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    next_retry_at TIMESTAMP WITH TIME ZONE,

    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        -- When to send this email (for reminders and delayed sends)
    sent_at TIMESTAMP WITH TIME ZONE,
        -- Actual delivery timestamp

    -- Priority (for future enhancement)
    priority INTEGER DEFAULT 5,  -- 1=highest, 10=lowest

    -- Related booking (optional foreign key)
    booking_id INTEGER,

    -- Template context (JSON for template rendering)
    template_context JSONB,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_email_status CHECK (status IN ('pending', 'processing', 'sent', 'failed', 'scheduled')),
    CONSTRAINT chk_email_format CHECK (recipient_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    CONSTRAINT chk_retry_count CHECK (retry_count >= 0 AND retry_count <= max_retries),
    CONSTRAINT chk_priority CHECK (priority >= 1 AND priority <= 10),

    -- Foreign key to appointments (optional - allows orphan emails)
    CONSTRAINT fk_email_booking
        FOREIGN KEY (booking_id)
        REFERENCES {SCHEMA_NAME}.appointments(id)
        ON DELETE SET NULL  -- Don't delete email if booking is deleted
);

-- ============================================================================
-- INDEXES - Optimized for worker queries
-- ============================================================================

-- Primary worker query: get pending/scheduled emails ready to send
CREATE INDEX IF NOT EXISTS idx_email_queue_worker_poll
    ON {SCHEMA_NAME}.email_queue(status, scheduled_for, priority)
    WHERE status IN ('pending', 'scheduled');

-- Retry query: find failed emails that need retry
CREATE INDEX IF NOT EXISTS idx_email_queue_retry
    ON {SCHEMA_NAME}.email_queue(status, next_retry_at)
    WHERE status = 'processing' AND next_retry_at IS NOT NULL;

-- Lookup by recipient (customer email history)
CREATE INDEX IF NOT EXISTS idx_email_queue_recipient
    ON {SCHEMA_NAME}.email_queue(recipient_email, created_at DESC);

-- Lookup by booking ID
CREATE INDEX IF NOT EXISTS idx_email_queue_booking
    ON {SCHEMA_NAME}.email_queue(booking_id)
    WHERE booking_id IS NOT NULL;

-- Lookup by type and status (analytics)
CREATE INDEX IF NOT EXISTS idx_email_queue_type_status
    ON {SCHEMA_NAME}.email_queue(type, status);

-- Sent emails (for reporting)
CREATE INDEX IF NOT EXISTS idx_email_queue_sent
    ON {SCHEMA_NAME}.email_queue(sent_at DESC)
    WHERE status = 'sent';

-- ============================================================================
-- TRIGGERS - Auto-update timestamps
-- ============================================================================

-- Reuse existing trigger function from bookings schema
DROP TRIGGER IF EXISTS trg_update_email_queue_timestamp ON {SCHEMA_NAME}.email_queue;
CREATE TRIGGER trg_update_email_queue_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.email_queue
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_booking_timestamp();

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to enqueue a new email
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.enqueue_email(
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
    INSERT INTO {SCHEMA_NAME}.email_queue (
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

-- Function to get pending emails (for worker)
-- ✅ FIXED: Now includes template_context in both RETURNS TABLE and SELECT
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_pending_emails(
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
    FROM {SCHEMA_NAME}.email_queue eq
    WHERE eq.status IN ('pending', 'scheduled')
      AND eq.scheduled_for <= CURRENT_TIMESTAMP
      AND eq.retry_count < eq.max_retries
    ORDER BY eq.priority ASC, eq.scheduled_for ASC
    LIMIT p_limit
    FOR UPDATE SKIP LOCKED;  -- Prevent race conditions between multiple workers
END;
$$ LANGUAGE plpgsql;

-- Function to update email status
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.update_email_status(
    p_email_id INTEGER,
    p_status VARCHAR,
    p_error TEXT DEFAULT NULL,
    p_sent_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE {SCHEMA_NAME}.email_queue
    SET status = p_status,
        last_error = COALESCE(p_error, last_error),
        sent_at = COALESCE(p_sent_at, sent_at),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_email_id;
END;
$$ LANGUAGE plpgsql;

-- Function to retry failed email
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.retry_email(
    p_email_id INTEGER,
    p_error TEXT,
    p_backoff_seconds INTEGER DEFAULT 300  -- 5 minutes default
) RETURNS VOID AS $$
DECLARE
    v_retry_count INTEGER;
BEGIN
    -- Increment retry count
    UPDATE {SCHEMA_NAME}.email_queue
    SET retry_count = retry_count + 1,
        last_error = p_error,
        status = 'pending',  -- Back to pending for retry
        next_retry_at = CURRENT_TIMESTAMP + (p_backoff_seconds * POW(2, retry_count) || ' seconds')::INTERVAL,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_email_id
    RETURNING retry_count INTO v_retry_count;

    -- If max retries exceeded, mark as failed
    IF v_retry_count >= (SELECT max_retries FROM {SCHEMA_NAME}.email_queue WHERE id = p_email_id) THEN
        UPDATE {SCHEMA_NAME}.email_queue
        SET status = 'failed'
        WHERE id = p_email_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old sent/failed emails (maintenance)
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.cleanup_old_emails(
    p_days_to_keep INTEGER DEFAULT 90
) RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM {SCHEMA_NAME}.email_queue
    WHERE status IN ('sent', 'failed')
      AND sent_at < CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERMISSIONS - Grant access to mcp_user
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.email_queue TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.email_queue_id_seq TO mcp_user;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.enqueue_email(VARCHAR, VARCHAR, VARCHAR, VARCHAR, TEXT, TEXT, INTEGER, JSONB, TIMESTAMP WITH TIME ZONE, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_pending_emails(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.update_email_status(INTEGER, VARCHAR, TEXT, TIMESTAMP WITH TIME ZONE) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.retry_email(INTEGER, TEXT, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.cleanup_old_emails(INTEGER) TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Email queue schema created successfully within: %', '{SCHEMA_NAME}';
    RAISE NOTICE '📧 Table created: email_queue';
    RAISE NOTICE '📊 Indexes created for optimal worker performance';
    RAISE NOTICE '🔧 Utility functions available:';
    RAISE NOTICE '   - enqueue_email() to add emails to queue';
    RAISE NOTICE '   - get_pending_emails() for worker polling';
    RAISE NOTICE '   - update_email_status() to mark sent/failed';
    RAISE NOTICE '   - retry_email() with exponential backoff';
    RAISE NOTICE '   - cleanup_old_emails() for maintenance';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '🚀 Email queue system ready for worker integration';
    RAISE NOTICE '';
    RAISE NOTICE '💡 Next steps:';
    RAISE NOTICE '   1. Deploy email_service worker (Docker)';
    RAISE NOTICE '   2. Configure SMTP settings in .env';
    RAISE NOTICE '   3. Integrate enqueue_email() calls in bookings.py';
END $$;
