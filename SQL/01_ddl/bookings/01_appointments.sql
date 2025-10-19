-- ============================================================================
-- APPOINTMENTS TABLE - Main booking/reservation records
-- ============================================================================
-- Tabla principal para registro de citas y reservas

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.appointments (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Customer information
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50),

    -- Booking details
    service_type VARCHAR(100) NOT NULL,
    booking_date DATE NOT NULL,
    booking_time TIME NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 60,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'confirmed',
        -- Possible values: confirmed, cancelled, completed, no_show, rescheduled

    -- Google Calendar integration
    google_calendar_event_id VARCHAR(255) UNIQUE,
    google_calendar_link TEXT,

    -- Additional information
    notes TEXT,
    cancellation_reason TEXT,

    -- Metadata timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_duration CHECK (duration_minutes > 0 AND duration_minutes <= 480),
    CONSTRAINT chk_status CHECK (status IN ('confirmed', 'cancelled', 'completed', 'no_show', 'rescheduled')),
    CONSTRAINT chk_email_format CHECK (customer_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- Performance indexes for appointments
CREATE INDEX IF NOT EXISTS idx_appointments_date
    ON :SCHEMA_NAME.appointments(booking_date);

CREATE INDEX IF NOT EXISTS idx_appointments_email
    ON :SCHEMA_NAME.appointments(customer_email);

CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON :SCHEMA_NAME.appointments(status);

CREATE INDEX IF NOT EXISTS idx_appointments_calendar_id
    ON :SCHEMA_NAME.appointments(google_calendar_event_id)
    WHERE google_calendar_event_id IS NOT NULL;

-- Composite index for availability queries (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_appointments_date_time_status
    ON :SCHEMA_NAME.appointments(booking_date, booking_time, status)
    WHERE status IN ('confirmed', 'rescheduled');

-- Index for customer booking history
CREATE INDEX IF NOT EXISTS idx_appointments_customer_date
    ON :SCHEMA_NAME.appointments(customer_email, booking_date DESC);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.appointments TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.appointments_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Appointments table created';
    RAISE NOTICE '   - Customer booking records';
    RAISE NOTICE '   - Status tracking (confirmed, cancelled, completed, etc)';
    RAISE NOTICE '   - Google Calendar integration';
    RAISE NOTICE '   - Performance indexes for queries';
END $$;
