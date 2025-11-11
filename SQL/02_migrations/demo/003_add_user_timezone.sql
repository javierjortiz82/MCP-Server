-- ============================================================================
-- MIGRATION 003: Add user_timezone to demo_usage table
-- ============================================================================
-- Purpose: Store client timezone for accurate blocked_until display
--
-- Background:
-- When a user reaches 100% quota, they are blocked for DEMO_COOLDOWN_HOURS.
-- The blocked_until timestamp should be displayed in the user's local timezone
-- for better UX (e.g., "Blocked until 2025-11-09 15:30 America/Costa_Rica").
--
-- This follows best practices from:
-- - Stripe API rate limits (shows reset time in user's timezone)
-- - GitHub API quota (displays X-RateLimit-Reset in user's local time)
-- - Twitter API (shows rate limit reset with timezone awareness)
--
-- Author: Lab01-MCP Team
-- Created: 2025-11-08
-- Version: 1.0.0
-- ============================================================================

-- Add user_timezone column
ALTER TABLE :SCHEMA_NAME.demo_usage
ADD COLUMN IF NOT EXISTS user_timezone VARCHAR(64) DEFAULT 'UTC';

-- Add comment explaining the column
COMMENT ON COLUMN :SCHEMA_NAME.demo_usage.user_timezone IS
'IANA timezone identifier (e.g., America/Costa_Rica, Europe/London, Asia/Tokyo).
Used to calculate and display blocked_until in user''s local timezone.
Detected from client browser via Intl.DateTimeFormat().resolvedOptions().timeZone';

-- Update existing records to UTC (safe default)
UPDATE :SCHEMA_NAME.demo_usage
SET user_timezone = 'UTC'
WHERE user_timezone IS NULL;

-- Make column NOT NULL after backfill
ALTER TABLE :SCHEMA_NAME.demo_usage
ALTER COLUMN user_timezone SET NOT NULL;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration 003 completed';
    RAISE NOTICE '   - Added user_timezone column (VARCHAR(64), NOT NULL)';
    RAISE NOTICE '   - Default: UTC';
    RAISE NOTICE '   - Backfilled existing records with UTC';
    RAISE NOTICE '   - Frontend will send timezone on first request';
    RAISE NOTICE '   - Backend will calculate blocked_until using client timezone + DEMO_COOLDOWN_HOURS';
END $$;
