-- ============================================================================
-- Demo Users Table - User Registration and Authentication
-- ============================================================================
-- Purpose: Store user registration data for Demo Chat access control
-- Author: Lab01-MCP Team
-- Created: 2025-10-31
-- Version: 1.0.0
--
-- Features:
-- - OAuth provider support (Google, Apple, Email/Password)
-- - Email verification status tracking
-- - Account status management (active, suspended, deleted)
-- - Timezone and locale preferences
-- - Registration source tracking (web, mobile, api)
-- - Soft delete support
--
-- Security:
-- - email is UNIQUE and case-insensitive (CITEXT)
-- - Passwords are hashed (never store plain text)
-- - OAuth tokens stored securely with encryption at application level
-- - Audit trail with created_at/updated_at
-- ============================================================================

-- Create CITEXT extension for case-insensitive email comparison
CREATE EXTENSION IF NOT EXISTS citext;

-- Drop table if exists (for migrations)
DROP TABLE IF EXISTS :SCHEMA_NAME.demo_users CASCADE;

-- Create demo_users table
CREATE TABLE :SCHEMA_NAME.demo_users (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- User Identity
    email CITEXT NOT NULL UNIQUE,  -- Case-insensitive email
    full_name TEXT NOT NULL,
    display_name TEXT,             -- Optional display name for chat

    -- Authentication
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'email',  -- 'email', 'google', 'apple'
    oauth_provider_id TEXT,        -- Provider's user ID (for OAuth)
    password_hash TEXT,            -- BCrypt hash (only for email auth)

    -- Email Verification Status
    is_email_verified BOOLEAN NOT NULL DEFAULT false,
    email_verified_at TIMESTAMPTZ,

    -- Account Status
    is_active BOOLEAN NOT NULL DEFAULT false,  -- Activated after OTP verification
    is_suspended BOOLEAN NOT NULL DEFAULT false,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    suspended_at TIMESTAMPTZ,
    suspended_reason TEXT,
    deleted_at TIMESTAMPTZ,

    -- User Preferences
    preferred_language VARCHAR(10) DEFAULT 'es',  -- ISO 639-1 code
    timezone VARCHAR(100) DEFAULT 'UTC',           -- IANA timezone

    -- Registration Metadata
    registration_source VARCHAR(50) DEFAULT 'web',  -- 'web', 'mobile', 'api'
    registration_ip INET,
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,

    -- Audit Fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_auth_provider CHECK (
        auth_provider IN ('email', 'google', 'apple', 'facebook', 'github')
    ),
    CONSTRAINT chk_email_format CHECK (
        email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    ),
    CONSTRAINT chk_preferred_language CHECK (
        preferred_language IN ('es', 'en', 'fr', 'de', 'it', 'pt')
    ),
    CONSTRAINT chk_oauth_consistency CHECK (
        (auth_provider = 'email' AND password_hash IS NOT NULL) OR
        (auth_provider != 'email' AND oauth_provider_id IS NOT NULL)
    )
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Email lookup (most common query)
CREATE UNIQUE INDEX idx_demo_users_email ON :SCHEMA_NAME.demo_users(LOWER(email));

-- OAuth provider lookup
CREATE INDEX idx_demo_users_oauth ON :SCHEMA_NAME.demo_users(auth_provider, oauth_provider_id)
WHERE oauth_provider_id IS NOT NULL;

-- Active users filter
CREATE INDEX idx_demo_users_active ON :SCHEMA_NAME.demo_users(is_active, is_deleted)
WHERE is_active = true AND is_deleted = false;

-- Email verification pending
CREATE INDEX idx_demo_users_unverified ON :SCHEMA_NAME.demo_users(is_email_verified, created_at)
WHERE is_email_verified = false;

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

-- Create trigger function if not exists
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.update_demo_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_demo_users_updated_at ON :SCHEMA_NAME.demo_users;
CREATE TRIGGER trg_demo_users_updated_at
    BEFORE UPDATE ON :SCHEMA_NAME.demo_users
    FOR EACH ROW
    EXECUTE FUNCTION :SCHEMA_NAME.update_demo_users_updated_at();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE :SCHEMA_NAME.demo_users IS
'User registration and authentication data for Demo Chat access control. Supports email/password and OAuth providers (Google, Apple).';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.email IS
'User email address (CITEXT for case-insensitive matching). UNIQUE constraint enforced.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.is_active IS
'User account is active after successful OTP verification. False until email is verified.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.is_email_verified IS
'Email address has been verified via OTP. Required before is_active can be true.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.password_hash IS
'BCrypt password hash. Only used for email authentication (null for OAuth providers).';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.oauth_provider_id IS
'Provider-specific user ID (e.g., Google sub claim). Only used for OAuth authentication.';

-- ============================================================================
-- Sample Query Examples
-- ============================================================================

-- Find user by email (case-insensitive)
-- SELECT * FROM :SCHEMA_NAME.demo_users WHERE email = 'user@example.com';

-- Find active, verified users
-- SELECT * FROM :SCHEMA_NAME.demo_users WHERE is_active = true AND is_email_verified = true AND is_deleted = false;

-- Find OAuth user by provider
-- SELECT * FROM :SCHEMA_NAME.demo_users WHERE auth_provider = 'google' AND oauth_provider_id = '1234567890';

-- Count pending email verifications
-- SELECT COUNT(*) FROM :SCHEMA_NAME.demo_users WHERE is_email_verified = false AND created_at > NOW() - INTERVAL '24 hours';
