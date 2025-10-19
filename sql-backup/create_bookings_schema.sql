-- ============================================================================
-- BOOKINGS SCHEMA CREATION
-- ============================================================================
-- Creates tables for booking/reservation management system within existing schema.
-- Uses the same SCHEMA_NAME pattern as products tables for consistency.
--
-- Prerequisites:
--  - PostgreSQL 14+ with required extensions
--  - Existing schema created by init-db.py
--  - Variables in .env: DATABASE_URL, SCHEMA_NAME
--
-- Usage:
--  - Run via Python: python3 SQL/src/init_bookings.py
--  - Or direct: psql < SQL/scripts/create_bookings_schema.sql
--
-- Author: Lab01-MCP Team
-- Created: 2025-10-11
-- Version: 1.0.0
-- ============================================================================

-- Note: SCHEMA_NAME will be substituted by Python script (e.g., "test")
-- This file is meant to be used with f-strings in Python, not executed directly

-- ============================================================================
-- APPOINTMENTS TABLE - Main booking/reservation records
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.appointments (
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
    ON {SCHEMA_NAME}.appointments(booking_date);

CREATE INDEX IF NOT EXISTS idx_appointments_email
    ON {SCHEMA_NAME}.appointments(customer_email);

CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON {SCHEMA_NAME}.appointments(status);

CREATE INDEX IF NOT EXISTS idx_appointments_calendar_id
    ON {SCHEMA_NAME}.appointments(google_calendar_event_id)
    WHERE google_calendar_event_id IS NOT NULL;

-- Composite index for availability queries (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_appointments_date_time_status
    ON {SCHEMA_NAME}.appointments(booking_date, booking_time, status)
    WHERE status IN ('confirmed', 'rescheduled');

-- Index for customer booking history
CREATE INDEX IF NOT EXISTS idx_appointments_customer_date
    ON {SCHEMA_NAME}.appointments(customer_email, booking_date DESC);

-- ============================================================================
-- SERVICE_TYPES TABLE - Catalog of available services
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.service_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    price NUMERIC(10,2),
    active BOOLEAN DEFAULT true,
    color VARCHAR(7),  -- Hex color for UI (e.g., #FF5733)
    icon VARCHAR(50),  -- Icon identifier for UI

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_service_duration CHECK (duration_minutes > 0 AND duration_minutes <= 480),
    CONSTRAINT chk_service_price CHECK (price IS NULL OR price >= 0)
);

-- Index for active services lookup
CREATE INDEX IF NOT EXISTS idx_service_types_active
    ON {SCHEMA_NAME}.service_types(active)
    WHERE active = true;

-- ============================================================================
-- BUSINESS_HOURS TABLE - Operating hours configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.business_hours (
    id SERIAL PRIMARY KEY,
    day_of_week INTEGER NOT NULL,  -- 0=Monday, 1=Tuesday, ..., 6=Sunday
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_day_of_week CHECK (day_of_week >= 0 AND day_of_week <= 6),
    CONSTRAINT chk_time_order CHECK (open_time < close_time),
    CONSTRAINT uq_day_of_week UNIQUE (day_of_week)
);

-- ============================================================================
-- BLOCKED_TIMES TABLE - Holidays, breaks, and unavailable slots
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.blocked_times (
    id SERIAL PRIMARY KEY,
    block_date DATE NOT NULL,
    start_time TIME,  -- NULL if full day block
    end_time TIME,    -- NULL if full day block
    reason VARCHAR(255),
    is_full_day BOOLEAN DEFAULT false,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_time_order CHECK (
        is_full_day = true OR
        (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time)
    ),
    CONSTRAINT chk_time_consistency CHECK (
        (is_full_day = true AND start_time IS NULL AND end_time IS NULL) OR
        (is_full_day = false AND start_time IS NOT NULL AND end_time IS NOT NULL)
    )
);

-- Index for availability checks
CREATE INDEX IF NOT EXISTS idx_blocked_times_date
    ON {SCHEMA_NAME}.blocked_times(block_date);

-- Composite index for time-specific blocks
CREATE INDEX IF NOT EXISTS idx_blocked_times_date_time
    ON {SCHEMA_NAME}.blocked_times(block_date, start_time, end_time)
    WHERE is_full_day = false;

-- ============================================================================
-- TRIGGERS - Auto-update timestamps
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.update_booking_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for appointments
DROP TRIGGER IF EXISTS trg_update_appointments_timestamp ON {SCHEMA_NAME}.appointments;
CREATE TRIGGER trg_update_appointments_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.appointments
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_booking_timestamp();

-- Trigger for service_types
DROP TRIGGER IF EXISTS trg_update_service_types_timestamp ON {SCHEMA_NAME}.service_types;
CREATE TRIGGER trg_update_service_types_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.service_types
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_booking_timestamp();

-- Trigger for business_hours
DROP TRIGGER IF EXISTS trg_update_business_hours_timestamp ON {SCHEMA_NAME}.business_hours;
CREATE TRIGGER trg_update_business_hours_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.business_hours
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_booking_timestamp();

-- Trigger for blocked_times
DROP TRIGGER IF EXISTS trg_update_blocked_times_timestamp ON {SCHEMA_NAME}.blocked_times;
CREATE TRIGGER trg_update_blocked_times_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.blocked_times
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_booking_timestamp();

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to check if a time slot is available
-- ✅ HYBRID SCHEDULING: Supports service-specific hours with fallback to business_hours
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.is_slot_available(
    p_booking_date DATE,
    p_booking_time TIME,
    p_duration_minutes INTEGER,
    p_service_type VARCHAR DEFAULT NULL  -- ✅ NEW: Optional service-specific scheduling
) RETURNS BOOLEAN AS $$
DECLARE
    v_end_time TIME;
    v_day_of_week INTEGER;
    v_open_time TIME;
    v_close_time TIME;
    v_hours_exist BOOLEAN;
BEGIN
    -- Calculate end time
    v_end_time := p_booking_time + (p_duration_minutes || ' minutes')::INTERVAL;

    -- Get day of week (0=Monday, 6=Sunday)
    v_day_of_week := EXTRACT(DOW FROM p_booking_date)::INTEGER;
    -- Adjust: PostgreSQL DOW is 0=Sunday, we need 0=Monday
    v_day_of_week := CASE WHEN v_day_of_week = 0 THEN 6 ELSE v_day_of_week - 1 END;

    -- ✅ HYBRID SCHEDULING LOGIC:
    -- Step 1: Try to get service-specific hours if service_type provided
    v_hours_exist := false;
    IF p_service_type IS NOT NULL THEN
        SELECT INTO v_open_time, v_close_time, v_hours_exist
            sh.open_time, sh.close_time, true
        FROM {SCHEMA_NAME}.service_hours sh
        JOIN {SCHEMA_NAME}.service_types st ON sh.service_type_id = st.id
        WHERE st.name = p_service_type
        AND sh.day_of_week = v_day_of_week
        AND sh.active = true
        ORDER BY sh.priority ASC
        LIMIT 1;
    END IF;

    -- Step 2: If no service-specific hours, fall back to business_hours
    IF NOT v_hours_exist THEN
        SELECT INTO v_open_time, v_close_time
            open_time, close_time
        FROM {SCHEMA_NAME}.business_hours
        WHERE day_of_week = v_day_of_week
        AND active = true;
    END IF;

    -- Check if we found valid hours
    IF v_open_time IS NULL OR v_close_time IS NULL THEN
        RETURN false;  -- Business closed this day
    END IF;

    -- Check if booking fits within operating hours
    IF NOT (v_open_time <= p_booking_time AND v_close_time >= v_end_time) THEN
        RETURN false;
    END IF;

    -- Check blocked times (full day)
    IF EXISTS (
        SELECT 1 FROM {SCHEMA_NAME}.blocked_times
        WHERE block_date = p_booking_date
        AND is_full_day = true
    ) THEN
        RETURN false;
    END IF;

    -- Check blocked times (specific time range)
    IF EXISTS (
        SELECT 1 FROM {SCHEMA_NAME}.blocked_times
        WHERE block_date = p_booking_date
        AND is_full_day = false
        AND (
            (p_booking_time >= start_time AND p_booking_time < end_time) OR
            (v_end_time > start_time AND v_end_time <= end_time) OR
            (p_booking_time <= start_time AND v_end_time >= end_time)
        )
    ) THEN
        RETURN false;
    END IF;

    -- Check existing appointments
    IF EXISTS (
        SELECT 1 FROM {SCHEMA_NAME}.appointments
        WHERE booking_date = p_booking_date
        AND status IN ('confirmed', 'rescheduled')
        AND (
            (booking_time >= p_booking_time AND booking_time < v_end_time) OR
            ((booking_time + (duration_minutes || ' minutes')::INTERVAL) > p_booking_time
             AND (booking_time + (duration_minutes || ' minutes')::INTERVAL) <= v_end_time) OR
            (booking_time <= p_booking_time AND
             (booking_time + (duration_minutes || ' minutes')::INTERVAL) >= v_end_time)
        )
    ) THEN
        RETURN false;
    END IF;

    RETURN true;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to cleanup old completed/cancelled appointments
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.cleanup_old_appointments(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM {SCHEMA_NAME}.appointments
    WHERE status IN ('completed', 'cancelled', 'no_show')
    AND (
        (completed_at IS NOT NULL AND completed_at < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL) OR
        (cancelled_at IS NOT NULL AND cancelled_at < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL)
    );

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERMISSIONS - Grant access to mcp_user
-- ============================================================================

-- Appointments table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.appointments TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.appointments_id_seq TO mcp_user;

-- Service types table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.service_types TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.service_types_id_seq TO mcp_user;

-- Business hours table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.business_hours TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.business_hours_id_seq TO mcp_user;

-- Blocked times table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.blocked_times TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.blocked_times_id_seq TO mcp_user;

-- Grant execute on functions
-- ✅ UPDATED: is_slot_available now supports hybrid scheduling with optional service_type parameter
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.is_slot_available(DATE, TIME, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.is_slot_available(DATE, TIME, INTEGER, VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.cleanup_old_appointments(INTEGER) TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Bookings schema created successfully within: %', '{SCHEMA_NAME}';
    RAISE NOTICE '📅 Tables created:';
    RAISE NOTICE '   - appointments (with Google Calendar integration)';
    RAISE NOTICE '   - service_types (booking service catalog)';
    RAISE NOTICE '   - business_hours (operating hours configuration)';
    RAISE NOTICE '   - blocked_times (holidays and unavailable slots)';
    RAISE NOTICE '📊 Indexes created for optimal query performance';
    RAISE NOTICE '🔧 Utility functions available:';
    RAISE NOTICE '   - is_slot_available() - HYBRID SCHEDULING (with fallback)';
    RAISE NOTICE '     * Optional service_type parameter for service-specific hours';
    RAISE NOTICE '     * Falls back to business_hours if service_hours not configured';
    RAISE NOTICE '   - cleanup_old_appointments() for maintenance';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '✨ NEXT: Create service_hours table (SQL/src/init_service_hours.py)';
    RAISE NOTICE '🚀 Bookings system ready for MCP tools integration';
END $$;
