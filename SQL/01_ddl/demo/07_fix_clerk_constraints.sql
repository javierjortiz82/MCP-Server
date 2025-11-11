-- ============================================================================
-- Fix Clerk Constraints - Add Missing Constraint Updates
-- ============================================================================
-- Purpose: Add 'clerk' to auth_provider constraint and fix authentication logic
-- Author: Lab01-MCP Team
-- Created: 2025-11-04
-- ============================================================================

BEGIN;

-- ============================================================================
-- Step 1: Update auth_provider constraint to include 'clerk'
-- ============================================================================

ALTER TABLE :SCHEMA_NAME.demo_users
    DROP CONSTRAINT IF EXISTS chk_auth_provider;

ALTER TABLE :SCHEMA_NAME.demo_users
    ADD CONSTRAINT chk_auth_provider CHECK (
        auth_provider IN ('email', 'google', 'apple', 'facebook', 'github', 'clerk')
    );

-- ============================================================================
-- Step 2: Update OAuth consistency constraint for Clerk compatibility
-- ============================================================================

-- Drop old restrictive constraint
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

-- ============================================================================
-- Step 3: Add constraint for migration status values
-- ============================================================================

ALTER TABLE :SCHEMA_NAME.demo_users
    ADD CONSTRAINT chk_migration_status CHECK (
        migration_status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')
    );

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
    v_constraints_fixed INTEGER;
    v_schema_name TEXT := :'SCHEMA_NAME';
BEGIN
    SELECT COUNT(*)
    INTO v_constraints_fixed
    FROM pg_constraint c
    JOIN pg_class cl ON c.conrelid = cl.oid
    JOIN pg_namespace n ON cl.relnamespace = n.oid
    WHERE n.nspname = v_schema_name
    AND cl.relname = 'demo_users'
    AND c.conname IN ('chk_auth_provider', 'chk_auth_consistency', 'chk_migration_status');

    RAISE NOTICE '✅ Clerk Constraints Fixed';
    RAISE NOTICE '   - Constraints updated: %', v_constraints_fixed;
    RAISE NOTICE '   - auth_provider now allows: email, google, apple, facebook, github, clerk';
END;
$$;

COMMIT;
