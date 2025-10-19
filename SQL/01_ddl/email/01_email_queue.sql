-- ============================================================================
-- EMAIL_QUEUE TABLE - Asynchronous email delivery queue
-- ============================================================================
-- Sistema de cola de emails con reintentos y priorización

CREATE TABLE IF NOT EXISTS test.email_queue (
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
        REFERENCES test.appointments(id)
        ON DELETE SET NULL  -- Don't delete email if booking is deleted
);

-- ============================================================================
-- INDEXES - Optimized for worker queries
-- ============================================================================

-- Primary worker query: get pending/scheduled emails ready to send
CREATE INDEX IF NOT EXISTS idx_email_queue_worker_poll
    ON test.email_queue(status, scheduled_for, priority)
    WHERE status IN ('pending', 'scheduled');

-- Retry query: find failed emails that need retry
CREATE INDEX IF NOT EXISTS idx_email_queue_retry
    ON test.email_queue(status, next_retry_at)
    WHERE status = 'processing' AND next_retry_at IS NOT NULL;

-- Lookup by recipient (customer email history)
CREATE INDEX IF NOT EXISTS idx_email_queue_recipient
    ON test.email_queue(recipient_email, created_at DESC);

-- Lookup by booking ID
CREATE INDEX IF NOT EXISTS idx_email_queue_booking
    ON test.email_queue(booking_id)
    WHERE booking_id IS NOT NULL;

-- Lookup by type and status (analytics)
CREATE INDEX IF NOT EXISTS idx_email_queue_type_status
    ON test.email_queue(type, status);

-- Sent emails (for reporting)
CREATE INDEX IF NOT EXISTS idx_email_queue_sent
    ON test.email_queue(sent_at DESC)
    WHERE status = 'sent';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON test.email_queue TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE test.email_queue_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Email queue table created';
    RAISE NOTICE '   - Asynchronous email delivery queue';
    RAISE NOTICE '   - Automatic retry with exponential backoff';
    RAISE NOTICE '   - Priority-based processing';
    RAISE NOTICE '   - Status tracking and analytics';
END $$;
