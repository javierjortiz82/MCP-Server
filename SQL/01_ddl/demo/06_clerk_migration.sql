-- ============================================================================
-- Clerk Authentication Migration - Add Clerk Support to demo_users
-- ============================================================================
-- Purpose: Extend demo_users table with Clerk Identity Provider support
-- Author: Lab01-MCP Team
-- Created: 2025-11-03
-- Version: 1.0.0
--
-- Features Added:
-- - Clerk user ID for federated identity mapping
-- - Clerk session tracking
-- - Clerk metadata storage (JSONB for custom fields)
-- - Migration status tracking for legacy users
-- - Last sync timestamp for webhook updates
--
-- Migration Strategy:
-- - Maintains backward compatibility with existing auth system
-- - Allows dual authentication: legacy (email/OAuth) + Clerk
-- - Forces migration for legacy users via force_clerk_migration flag
-- - Tracks migration status: 'pending', 'in_progress', 'completed', 'failed'
--
-- Security:
-- - clerk_user_id is UNIQUE to prevent duplicate accounts
-- - clerk_metadata stored as encrypted JSONB at application level
-- - Indexes for efficient Clerk user lookups
-- ============================================================================

-- ============================================================================
-- Step 1: Add New Columns for Clerk Integration
-- ============================================================================

-- Add Clerk-specific columns to demo_users table
ALTER TABLE :SCHEMA_NAME.demo_users
    ADD COLUMN IF NOT EXISTS clerk_user_id VARCHAR(255) UNIQUE,
    ADD COLUMN IF NOT EXISTS clerk_session_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS clerk_metadata JSONB,
    ADD COLUMN IF NOT EXISTS last_clerk_sync_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS migration_status VARCHAR(50) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS force_clerk_migration BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS migration_completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS migration_error TEXT;

-- ============================================================================
-- Step 2: Update Constraints for Clerk Compatibility
-- ============================================================================

-- Drop existing OAuth consistency constraint (too restrictive for Clerk)
ALTER TABLE :SCHEMA_NAME.demo_users
    DROP CONSTRAINT IF EXISTS chk_oauth_consistency;

-- Create new flexible authentication constraint
-- Allows: email+password, OAuth (legacy), Clerk (with or without password)
ALTER TABLE :SCHEMA_NAME.demo_users
    ADD CONSTRAINT chk_auth_consistency CHECK (
        -- Email auth: must have password
        (auth_provider = 'email' AND password_hash IS NOT NULL) OR
        -- Legacy OAuth: must have provider ID
        (auth_provider IN ('google', 'apple', 'facebook', 'github') AND oauth_provider_id IS NOT NULL) OR
        -- Clerk auth: must have clerk_user_id (may or may not have password/oauth_provider_id)
        (auth_provider = 'clerk' AND clerk_user_id IS NOT NULL)
    );

-- Add constraint for migration status values
ALTER TABLE :SCHEMA_NAME.demo_users
    ADD CONSTRAINT chk_migration_status CHECK (
        migration_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')
    );

-- Update auth_provider constraint to include 'clerk'
ALTER TABLE :SCHEMA_NAME.demo_users
    DROP CONSTRAINT IF EXISTS chk_auth_provider;

ALTER TABLE :SCHEMA_NAME.demo_users
    ADD CONSTRAINT chk_auth_provider CHECK (
        auth_provider IN ('email', 'google', 'apple', 'facebook', 'github', 'clerk')
    );

-- ============================================================================
-- Step 3: Create Indexes for Clerk Performance
-- ============================================================================

-- Clerk user ID lookup (primary Clerk query)
CREATE UNIQUE INDEX IF NOT EXISTS idx_demo_users_clerk_id
    ON :SCHEMA_NAME.demo_users(clerk_user_id)
    WHERE clerk_user_id IS NOT NULL;

-- Clerk session lookup (for session validation)
CREATE INDEX IF NOT EXISTS idx_demo_users_clerk_session
    ON :SCHEMA_NAME.demo_users(clerk_session_id)
    WHERE clerk_session_id IS NOT NULL;

-- Migration status tracking (find users pending migration)
CREATE INDEX IF NOT EXISTS idx_demo_users_migration_status
    ON :SCHEMA_NAME.demo_users(migration_status, force_clerk_migration)
    WHERE force_clerk_migration = true AND migration_status = 'pending';

-- Clerk auth provider lookup
CREATE INDEX IF NOT EXISTS idx_demo_users_clerk_provider
    ON :SCHEMA_NAME.demo_users(auth_provider)
    WHERE auth_provider = 'clerk';

-- Last sync timestamp (for webhook updates)
CREATE INDEX IF NOT EXISTS idx_demo_users_clerk_sync
    ON :SCHEMA_NAME.demo_users(last_clerk_sync_at)
    WHERE clerk_user_id IS NOT NULL;

-- ============================================================================
-- Step 4: Update Existing Users for Migration
-- ============================================================================

-- Mark all existing users for Clerk migration
-- (force_clerk_migration = true is already the default)
UPDATE :SCHEMA_NAME.demo_users
SET
    migration_status = 'pending',
    updated_at = NOW()
WHERE
    clerk_user_id IS NULL
    AND is_deleted = false;

-- ============================================================================
-- Step 5: Add Comments for Documentation
-- ============================================================================

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.clerk_user_id IS
'Clerk Identity Provider user ID (unique). Format: user_XXXXXXXXXXXXXXXXXXXXXXXXX. Used for all Clerk-authenticated users.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.clerk_session_id IS
'Current Clerk session ID. Updated via webhooks on session.created events. Used for session validation.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.clerk_metadata IS
'JSONB field storing Clerk user metadata: {company, role, phone, industry, custom_fields}. Synced via webhooks.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.last_clerk_sync_at IS
'Timestamp of last successful sync from Clerk webhooks (user.updated event). Used to detect stale data.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.migration_status IS
'Migration status for legacy users: pending (not started), in_progress (initiated), completed (success), failed (error), skipped (opted out).';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.force_clerk_migration IS
'Flag to force legacy users to migrate to Clerk on next login. Set to true for all existing users after Clerk rollout.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.migration_completed_at IS
'Timestamp when user successfully completed Clerk migration. Null if not migrated yet.';

COMMENT ON COLUMN :SCHEMA_NAME.demo_users.migration_error IS
'Error message if migration failed. Used for debugging and retry logic.';

-- ============================================================================
-- Step 6: Create Helper Functions for Clerk Operations
-- ============================================================================

-- Function: Get or create user from Clerk data
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.upsert_clerk_user(
    p_clerk_user_id VARCHAR(255),
    p_email CITEXT,
    p_full_name TEXT,
    p_clerk_metadata JSONB,
    p_clerk_session_id VARCHAR(255) DEFAULT NULL
)
RETURNS TABLE(
    user_id INTEGER,
    is_new_user BOOLEAN,
    user_email CITEXT
) AS $$
DECLARE
    v_user_id INTEGER;
    v_is_new BOOLEAN;
BEGIN
    -- Try to find existing user by Clerk ID
    SELECT id INTO v_user_id
    FROM :SCHEMA_NAME.demo_users
    WHERE clerk_user_id = p_clerk_user_id;

    IF v_user_id IS NOT NULL THEN
        -- Update existing Clerk user
        UPDATE :SCHEMA_NAME.demo_users
        SET
            full_name = p_full_name,
            clerk_metadata = p_clerk_metadata,
            clerk_session_id = COALESCE(p_clerk_session_id, clerk_session_id),
            last_clerk_sync_at = NOW(),
            last_login_at = NOW(),
            updated_at = NOW()
        WHERE id = v_user_id;

        v_is_new := false;
    ELSE
        -- Check if user exists by email (legacy user migrating)
        SELECT id INTO v_user_id
        FROM :SCHEMA_NAME.demo_users
        WHERE email = p_email;

        IF v_user_id IS NOT NULL THEN
            -- Link Clerk ID to existing user (migration)
            UPDATE :SCHEMA_NAME.demo_users
            SET
                clerk_user_id = p_clerk_user_id,
                clerk_metadata = p_clerk_metadata,
                clerk_session_id = p_clerk_session_id,
                auth_provider = 'clerk',
                is_email_verified = true,  -- Clerk handles email verification
                is_active = true,
                migration_status = 'completed',
                migration_completed_at = NOW(),
                last_clerk_sync_at = NOW(),
                last_login_at = NOW(),
                updated_at = NOW()
            WHERE id = v_user_id;

            v_is_new := false;
        ELSE
            -- Create new Clerk user
            INSERT INTO :SCHEMA_NAME.demo_users (
                email,
                full_name,
                auth_provider,
                clerk_user_id,
                clerk_metadata,
                clerk_session_id,
                is_email_verified,
                is_active,
                migration_status,
                migration_completed_at,
                last_clerk_sync_at,
                last_login_at,
                registration_source,
                created_at,
                updated_at
            ) VALUES (
                p_email,
                p_full_name,
                'clerk',
                p_clerk_user_id,
                p_clerk_metadata,
                p_clerk_session_id,
                true,  -- Clerk users are pre-verified
                true,  -- Clerk users are immediately active
                'completed',
                NOW(),
                NOW(),
                NOW(),
                'clerk_oauth',
                NOW(),
                NOW()
            )
            RETURNING id INTO v_user_id;

            v_is_new := true;
        END IF;
    END IF;

    -- Return user info
    RETURN QUERY
    SELECT v_user_id, v_is_new, p_email;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION :SCHEMA_NAME.upsert_clerk_user IS
'Get or create user from Clerk webhook data. Handles both new users and migration of existing users. Returns user_id, is_new_user flag, and email.';

-- Function: Check if user requires Clerk migration
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.check_clerk_migration_required(
    p_email CITEXT
)
RETURNS TABLE(
    requires_migration BOOLEAN,
    user_id INTEGER,
    auth_provider VARCHAR(50),
    migration_status VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (clerk_user_id IS NULL AND force_clerk_migration = true) AS requires_migration,
        id AS user_id,
        demo_users.auth_provider,
        demo_users.migration_status
    FROM :SCHEMA_NAME.demo_users
    WHERE email = p_email
        AND is_deleted = false;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION :SCHEMA_NAME.check_clerk_migration_required IS
'Check if a user (by email) needs to migrate to Clerk. Used by legacy auth endpoints to redirect users to Clerk.';

-- Function: Soft delete user when Clerk deletes account (IDEMPOTENT)
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.soft_delete_clerk_user(
    p_clerk_user_id VARCHAR(255)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_user_exists BOOLEAN;
BEGIN
    -- Check if user exists
    SELECT EXISTS(
        SELECT 1 FROM :SCHEMA_NAME.demo_users
        WHERE clerk_user_id = p_clerk_user_id
    ) INTO v_user_exists;

    -- Return false if user doesn't exist
    IF NOT v_user_exists THEN
        RETURN false;
    END IF;

    -- Update user to soft delete (idempotent: only updates if not already deleted)
    UPDATE :SCHEMA_NAME.demo_users
    SET
        is_deleted = true,
        is_active = false,
        deleted_at = COALESCE(deleted_at, NOW()),  -- Keep original deletion timestamp if already deleted
        updated_at = NOW()
    WHERE clerk_user_id = p_clerk_user_id
    AND is_deleted = false;  -- Only update if not already deleted

    -- Return true if user exists (regardless of whether update happened)
    RETURN true;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION :SCHEMA_NAME.soft_delete_clerk_user IS
'Soft delete user when Clerk sends user.deleted webhook. Sets is_deleted=true and is_active=false. IDEMPOTENT: Returns true if user exists (even if already deleted), false only if user not found.';

-- Function: Update user session from Clerk webhook
CREATE OR REPLACE FUNCTION :SCHEMA_NAME.update_clerk_session(
    p_clerk_user_id VARCHAR(255),
    p_session_id VARCHAR(255)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE :SCHEMA_NAME.demo_users
    SET
        clerk_session_id = p_session_id,
        last_login_at = NOW(),
        updated_at = NOW()
    WHERE clerk_user_id = p_clerk_user_id;

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    RETURN (v_updated > 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION :SCHEMA_NAME.update_clerk_session IS
'Update user session ID and last_login_at when Clerk sends session.created webhook.';

-- ============================================================================
-- Step 7: Migration Statistics View (Optional - for monitoring)
-- ============================================================================

CREATE OR REPLACE VIEW :SCHEMA_NAME.vw_clerk_migration_stats AS
SELECT
    COUNT(*) FILTER (WHERE clerk_user_id IS NOT NULL) AS clerk_users_total,
    COUNT(*) FILTER (WHERE clerk_user_id IS NULL) AS legacy_users_total,
    COUNT(*) FILTER (WHERE migration_status = 'pending') AS pending_migration,
    COUNT(*) FILTER (WHERE migration_status = 'in_progress') AS in_progress_migration,
    COUNT(*) FILTER (WHERE migration_status = 'completed') AS completed_migration,
    COUNT(*) FILTER (WHERE migration_status = 'failed') AS failed_migration,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE migration_status = 'completed') /
        NULLIF(COUNT(*), 0),
        2
    ) AS migration_completion_percentage
FROM :SCHEMA_NAME.demo_users
WHERE is_deleted = false;

COMMENT ON VIEW :SCHEMA_NAME.vw_clerk_migration_stats IS
'Real-time statistics on Clerk migration progress. Use for monitoring rollout.';

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Display migration summary
DO $$
DECLARE
    v_total_users INTEGER;
    v_pending_migration INTEGER;
    v_clerk_users INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total_users FROM :SCHEMA_NAME.demo_users WHERE is_deleted = false;
    SELECT COUNT(*) INTO v_pending_migration FROM :SCHEMA_NAME.demo_users WHERE migration_status = 'pending';
    SELECT COUNT(*) INTO v_clerk_users FROM :SCHEMA_NAME.demo_users WHERE clerk_user_id IS NOT NULL;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Clerk Migration Script Completed';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total Users: %', v_total_users;
    RAISE NOTICE 'Clerk Users: %', v_clerk_users;
    RAISE NOTICE 'Pending Migration: %', v_pending_migration;
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- Sample Queries for Testing
-- ============================================================================

-- Find all Clerk users
-- SELECT id, email, full_name, clerk_user_id, clerk_metadata FROM :SCHEMA_NAME.demo_users WHERE auth_provider = 'clerk';

-- Find users pending Clerk migration
-- SELECT id, email, full_name, auth_provider, migration_status FROM :SCHEMA_NAME.demo_users WHERE migration_status = 'pending' AND force_clerk_migration = true;

-- Test upsert_clerk_user function (new user)
-- SELECT * FROM :SCHEMA_NAME.upsert_clerk_user('user_2abcdefghijklmnop', 'test@odiseo.com', 'Test User', '{"company": "Odiseo", "role": "Admin"}'::jsonb, 'sess_xyz123');

-- Test check_clerk_migration_required function
-- SELECT * FROM :SCHEMA_NAME.check_clerk_migration_required('existing.user@odiseo.com');

-- View migration statistics
-- SELECT * FROM :SCHEMA_NAME.vw_clerk_migration_stats;
