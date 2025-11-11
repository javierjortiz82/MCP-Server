-- ============================================================================
-- Demo OTP Codes Table - One-Time Password Verification
-- ============================================================================
-- Purpose: Store and validate OTP codes for email verification
-- Author: Lab01-MCP Team
-- Created: 2025-10-31
-- Version: 1.0.0
--
-- Features:
-- - Secure OTP generation and storage
-- - Expiration tracking (24 hours default)
-- - Rate limiting (max 3 attempts per OTP)
-- - Multiple OTP purposes (email_verification, password_reset, etc.)
-- - Auto-cleanup of expired codes
-- - Resend throttling (1 minute between sends)
--
-- Security Best Practices (2025):
-- - OTP length: 6 digits (balance security vs UX)
-- - Expiration: 24 hours (as per requirements)
-- - Max attempts: 3 (prevent brute force)
-- - Rate limiting: 1 OTP per minute per email
-- - Codes are hashed before storage (SHA-256)
-- ============================================================================

-- Drop table if exists (for migrations)
DROP TABLE IF EXISTS :SCHEMA_NAME.demo_otp_codes CASCADE;

-- Create demo_otp_codes table
CREATE TABLE :SCHEMA_NAME.demo_otp_codes (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- User Reference
    user_id INTEGER NOT NULL REFERENCES :SCHEMA_NAME.demo_users(id) ON DELETE CASCADE,
    email CITEXT NOT NULL,  -- Denormalized for quick lookup

    -- OTP Details
    code_hash TEXT NOT NULL,  -- SHA-256 hash of 6-digit code
    purpose VARCHAR(50) NOT NULL DEFAULT 'email_verification',

    -- Expiration & Attempts
    expires_at TIMESTAMPTZ NOT NULL,
    attempts_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,

    -- Status
    is_used BOOLEAN NOT NULL DEFAULT false,
    used_at TIMESTAMPTZ,

    -- Metadata
    ip_address INET,              -- IP that requested OTP
    user_agent TEXT,              -- Browser/client info

    -- Audit Fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_otp_purpose CHECK (
        purpose IN ('email_verification', 'password_reset', 'account_recovery', 'login_2fa')
    ),
    CONSTRAINT chk_otp_attempts CHECK (attempts_count <= max_attempts),
    CONSTRAINT chk_expires_future CHECK (expires_at > created_at)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Lookup by user_id and purpose (most common query)
CREATE INDEX idx_demo_otp_user_purpose ON :SCHEMA_NAME.demo_otp_codes(user_id, purpose, expires_at)
WHERE is_used = false;

-- Email lookup for rate limiting
CREATE INDEX idx_demo_otp_email ON :SCHEMA_NAME.demo_otp_codes(email, created_at)
WHERE is_used = false;

-- Cleanup expired codes (background job)
CREATE INDEX idx_demo_otp_expired ON :SCHEMA_NAME.demo_otp_codes(expires_at, is_used)
WHERE is_used = false;

-- Active codes (not used) - expiration checked in queries, not in index predicate
CREATE INDEX idx_demo_otp_active ON :SCHEMA_NAME.demo_otp_codes(user_id, is_used, expires_at)
WHERE is_used = false;

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

-- Create trigger function if not exists
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.update_demo_otp_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_demo_otp_updated_at ON :SCHEMA_NAME.demo_otp_codes;
CREATE TRIGGER trg_demo_otp_updated_at
    BEFORE UPDATE ON :SCHEMA_NAME.demo_otp_codes
    FOR EACH ROW
    EXECUTE FUNCTION :SCHEMA_NAME.update_demo_otp_updated_at();

-- ============================================================================
-- Cleanup Function for Expired OTPs
-- ============================================================================

-- Function to delete expired OTP codes (older than 48 hours)
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.cleanup_expired_otp_codes()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    EXECUTE format('DELETE FROM %I.demo_otp_codes WHERE expires_at < NOW() - INTERVAL ''48 hours''', current_schema());
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Rate Limiting Function
-- ============================================================================

-- Function to check if user can request new OTP (rate limiting)
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.can_request_otp(
    p_email CITEXT,
    p_purpose VARCHAR(50),
    p_cooldown_seconds INTEGER DEFAULT 60  -- 1 minute default
)
RETURNS BOOLEAN AS $$
DECLARE
    last_request_time TIMESTAMPTZ;
    query_text TEXT;
BEGIN
    -- Build dynamic query with current schema
    query_text := format(
        'SELECT MAX(created_at) FROM %I.demo_otp_codes WHERE email = $1 AND purpose = $2 AND created_at > NOW() - INTERVAL ''1 second'' * $3',
        current_schema()
    );

    -- Execute query
    EXECUTE query_text INTO last_request_time USING p_email, p_purpose, p_cooldown_seconds;

    -- If no recent request or cooldown passed, allow new OTP
    RETURN (last_request_time IS NULL OR last_request_time < NOW() - INTERVAL '1 second' * p_cooldown_seconds);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE :SCHEMA_NAME.demo_otp_codes IS
'One-time password codes for email verification and account recovery. Codes expire after 24 hours and allow max 3 verification attempts.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_otp_codes.code_hash IS
'SHA-256 hash of the 6-digit OTP code. Never store plain-text OTPs.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_otp_codes.purpose IS
'Purpose of OTP: email_verification (default), password_reset, account_recovery, login_2fa.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_otp_codes.expires_at IS
'Expiration timestamp. Default is 24 hours from creation as per requirements.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_otp_codes.attempts_count IS
'Number of failed verification attempts. Max 3 attempts allowed to prevent brute force.';

-- ============================================================================
-- Sample Query Examples
-- ============================================================================

-- Check if user can request new OTP (rate limiting)
-- SELECT :SCHEMA_NAME.can_request_otp('user@example.com', 'email_verification', 60);

-- Find active OTP for user
-- SELECT * FROM :SCHEMA_NAME.demo_otp_codes
-- WHERE user_id = 123
--   AND purpose = 'email_verification'
--   AND is_used = false
--   AND expires_at > NOW()
-- ORDER BY created_at DESC
-- LIMIT 1;

-- Cleanup expired OTPs (run daily)
-- SELECT :SCHEMA_NAME.cleanup_expired_otp_codes();

-- Count pending verifications in last 24h
-- SELECT COUNT(DISTINCT user_id)
-- FROM :SCHEMA_NAME.demo_otp_codes
-- WHERE purpose = 'email_verification'
--   AND is_used = false
--   AND created_at > NOW() - INTERVAL '24 hours';
