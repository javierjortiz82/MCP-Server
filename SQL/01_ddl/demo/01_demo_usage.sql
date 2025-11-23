-- ============================================================================
-- DEMO_USAGE TABLE - Token bucket and rate limiting per user
-- ============================================================================
-- Token-bucket algorithm para controlar consumo de tokens en demostraciones
-- Almacena contadores diarios, bloqueos y resets de cuota

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.demo_usage (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- User identification (token bucket key)
    user_key VARCHAR(255) NOT NULL UNIQUE,
        -- Format: user_id | session_id | fingerprint
        -- Examples:
        --   "user_123"           (authenticated user)
        --   "sess_abc456"        (anonymous session)
        --   "fp_sha256hash"      (client fingerprint for VPN detection)

    -- Token consumption tracking
    tokens_consumed INTEGER NOT NULL DEFAULT 0,
        -- Cumulative tokens used by this user in current day
        -- Range: 0 to DEMO_MAX_TOKENS (typically 5000)

    -- Request count tracking (for IP-based rate limits)
    requests_count INTEGER NOT NULL DEFAULT 0,
        -- Number of API requests made in current day

    -- Reset timing
    last_reset TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- When the daily quota was last reset (UTC midnight)
        -- Used to determine if reset is needed

    -- Blocking state
    is_blocked BOOLEAN NOT NULL DEFAULT false,
        -- true: User has exceeded quota and is blocked
        -- false: User can still use demo

    blocked_until TIMESTAMP WITH TIME ZONE,
        -- When the block expires (usually 24h from quota exhaustion)
        -- NULL if not blocked

    -- User timezone for accurate blocked_until display
    user_timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
        -- IANA timezone identifier (e.g., America/Costa_Rica, Europe/London)
        -- Used to calculate and display blocked_until in user's local timezone
        -- Detected from client browser via Intl.DateTimeFormat()

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- When this user key was first seen

    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- Last time this record was updated

    -- Constraints
    CONSTRAINT chk_demo_tokens_range CHECK (
        tokens_consumed >= 0 AND tokens_consumed <= 100000
    ),
    CONSTRAINT chk_demo_requests_range CHECK (
        requests_count >= 0
    ),
    CONSTRAINT chk_demo_blocked_consistency CHECK (
        (is_blocked = false AND blocked_until IS NULL) OR
        (is_blocked = true AND blocked_until IS NOT NULL)
    )
);

-- ============================================================================
-- INDEXES - Optimized for token-bucket operations
-- ============================================================================

-- Primary lookup: get user's current quota state
CREATE INDEX IF NOT EXISTS idx_demo_usage_user_key
    ON :SCHEMA_NAME.demo_usage(user_key);

-- Background job: find users with expired blocks
CREATE INDEX IF NOT EXISTS idx_demo_usage_blocked_until
    ON :SCHEMA_NAME.demo_usage(blocked_until)
    WHERE is_blocked = true;

-- Analytics: quota consumption patterns
CREATE INDEX IF NOT EXISTS idx_demo_usage_reset_tokens
    ON :SCHEMA_NAME.demo_usage(last_reset, tokens_consumed DESC);

-- Cleanup: find stale records (no activity for 90 days)
CREATE INDEX IF NOT EXISTS idx_demo_usage_updated_at
    ON :SCHEMA_NAME.demo_usage(updated_at)
    WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '90 days';

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.demo_usage TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.demo_usage_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Demo usage table created';
    RAISE NOTICE '   - Token-bucket per user (5K tokens/day default)';
    RAISE NOTICE '   - 24-hour cooldown after quota exhaustion';
    RAISE NOTICE '   - Request count tracking for IP rate limits';
    RAISE NOTICE '   - Automatic daily quota reset (UTC midnight)';
END $$;
