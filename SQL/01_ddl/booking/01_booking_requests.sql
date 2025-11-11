-- ============================================================================
-- Booking Requests Table
-- ============================================================================
-- Purpose: Store demo booking requests from website
-- Created: 2025-11-09
-- Author: Odiseo AI Team
--
-- Security:
-- - IP address logging for abuse detection
-- - reCAPTCHA score validation
-- - Rate limiting via application layer
--
-- Usage:
-- - Demo booking from landing page
-- - Sales team demo scheduling
-- - Follow-up tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.booking_requests (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Contact information
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    country_code VARCHAR(10),
    company VARCHAR(255),

    -- Booking preferences
    preferred_date DATE NOT NULL,
    preferred_time TIME NOT NULL,
    message TEXT,

    -- Security & anti-spam
    ip_address INET,
    user_agent TEXT,
    recaptcha_score FLOAT CHECK (recaptcha_score >= 0 AND recaptcha_score <= 1),

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled', 'no_show')),
    assigned_to INTEGER,
    confirmed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Notes for internal team
    internal_notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Email lookup for duplicate detection
CREATE INDEX idx_booking_email ON :SCHEMA_NAME.booking_requests(email);

-- Status filtering for admin dashboard
CREATE INDEX idx_booking_status ON :SCHEMA_NAME.booking_requests(status) WHERE status = 'pending';

-- Date range queries (most common query)
CREATE INDEX idx_booking_date ON :SCHEMA_NAME.booking_requests(preferred_date, preferred_time);

-- Recent bookings
CREATE INDEX idx_booking_created ON :SCHEMA_NAME.booking_requests(created_at DESC);

-- IP address for rate limiting and abuse detection
CREATE INDEX idx_booking_ip ON :SCHEMA_NAME.booking_requests(ip_address, created_at DESC);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE TRIGGER update_booking_requests_updated_at
    BEFORE UPDATE ON :SCHEMA_NAME.booking_requests
    FOR EACH ROW
    EXECUTE FUNCTION :SCHEMA_NAME.update_updated_at_column();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE :SCHEMA_NAME.booking_requests IS 'Demo booking requests from website with spam protection';
COMMENT ON COLUMN :SCHEMA_NAME.booking_requests.recaptcha_score IS 'Google reCAPTCHA v3 score (0.0-1.0, higher is more human)';
COMMENT ON COLUMN :SCHEMA_NAME.booking_requests.status IS 'Current status: pending, confirmed, completed, cancelled, no_show';
COMMENT ON COLUMN :SCHEMA_NAME.booking_requests.ip_address IS 'Client IP address for rate limiting and abuse detection';
COMMENT ON COLUMN :SCHEMA_NAME.booking_requests.preferred_date IS 'Customer preferred demo date';
COMMENT ON COLUMN :SCHEMA_NAME.booking_requests.preferred_time IS 'Customer preferred demo time';
