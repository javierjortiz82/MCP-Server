-- ============================================================================
-- Contact Requests Table
-- ============================================================================
-- Purpose: Store contact form submissions from website
-- Created: 2025-11-09
-- Author: Odiseo AI Team
--
-- Security:
-- - IP address logging for abuse detection
-- - reCAPTCHA score validation
-- - Rate limiting via application layer
--
-- Usage:
-- - General inquiries from landing page
-- - Sales team contact requests
-- - Support ticket creation
-- ============================================================================

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.contact_requests (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Contact information
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    country_code VARCHAR(10),
    company VARCHAR(255),
    message TEXT NOT NULL CHECK (char_length(message) >= 10),

    -- Categorization
    contact_type VARCHAR(50) DEFAULT 'general' CHECK (contact_type IN ('general', 'sales', 'support')),

    -- Security & anti-spam
    ip_address INET,
    user_agent TEXT,
    recaptcha_score FLOAT CHECK (recaptcha_score >= 0 AND recaptcha_score <= 1),

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'spam')),
    assigned_to INTEGER,
    resolved_at TIMESTAMPTZ,

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
CREATE INDEX idx_contact_email ON :SCHEMA_NAME.contact_requests(email);

-- Status filtering for admin dashboard
CREATE INDEX idx_contact_status ON :SCHEMA_NAME.contact_requests(status) WHERE status = 'pending';

-- Recent contacts (most common query)
CREATE INDEX idx_contact_created ON :SCHEMA_NAME.contact_requests(created_at DESC);

-- IP address for rate limiting and abuse detection
CREATE INDEX idx_contact_ip ON :SCHEMA_NAME.contact_requests(ip_address, created_at DESC);

-- Type filtering (sales vs general)
CREATE INDEX idx_contact_type ON :SCHEMA_NAME.contact_requests(contact_type, status);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE TRIGGER update_contact_requests_updated_at
    BEFORE UPDATE ON :SCHEMA_NAME.contact_requests
    FOR EACH ROW
    EXECUTE FUNCTION :SCHEMA_NAME.update_updated_at_column();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE :SCHEMA_NAME.contact_requests IS 'Contact form submissions from website with spam protection';
COMMENT ON COLUMN :SCHEMA_NAME.contact_requests.recaptcha_score IS 'Google reCAPTCHA v3 score (0.0-1.0, higher is more human)';
COMMENT ON COLUMN :SCHEMA_NAME.contact_requests.contact_type IS 'Type of contact: general inquiry, sales, or support';
COMMENT ON COLUMN :SCHEMA_NAME.contact_requests.status IS 'Current status: pending, in_progress, resolved, spam';
COMMENT ON COLUMN :SCHEMA_NAME.contact_requests.ip_address IS 'Client IP address for rate limiting and abuse detection';
