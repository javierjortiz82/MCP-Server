-- ============================================================================
-- DEMO_AUDIT_LOG TABLE - Security and abuse detection logging
-- ============================================================================
-- Registro detallado de acceso a demo para auditoría, análisis de abuso
-- y debugging de problemas de rate-limiting

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.demo_audit_log (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- User identification
    user_key VARCHAR(255),
        -- Same format as demo_usage.user_key (user_id | session_id | fingerprint)
        -- Nullable for requests from unauthenticated sources

    -- Network information
    ip_address INET,
        -- Client IP address (IPv4 or IPv6)
        -- Used for IP-based rate limiting and geo-blocking

    -- Client fingerprinting (for VPN/proxy detection)
    client_fingerprint VARCHAR(255),
        -- Hash of client characteristics (UA, TLS JA3, canvas, timezone, etc.)
        -- Used to detect rotated IPs from same machine

    -- Request details
    request_input TEXT,
        -- User's query/input (first 1000 chars for audit trail)
        -- Truncated to avoid storage explosion

    -- Response metrics
    response_length INTEGER,
        -- Length of response in characters (for tracking payload size)

    tokens_used INTEGER,
        -- Tokens consumed by this request
        -- Used to validate token-bucket accounting

    -- Rate limit and security state
    is_blocked BOOLEAN NOT NULL DEFAULT false,
        -- true: Request was rejected due to quota/limits
        -- false: Request was processed

    block_reason VARCHAR(255),
        -- Why request was blocked (if is_blocked = true):
        -- - "quota_exceeded": Daily token limit reached
        -- - "rate_limit_ip": IP rate limit exceeded
        -- - "rate_limit_user": User rate limit exceeded
        -- - "suspicious_behavior": Abuse detection triggered
        -- - "captcha_required": Waiting for CAPTCHA verification
        -- NULL if not blocked

    -- Abuse detection scoring
    abuse_score FLOAT DEFAULT 0.0,
        -- Machine learning abuse likelihood (0.0-1.0)
        -- 0.0 = legitimate, 1.0 = certain attack
        -- Computed from:
        --   - Request rate (requests/min)
        --   - IP reputation
        --   - Fingerprint consistency
        --   - User behavior patterns

    -- Action taken by system
    action_taken VARCHAR(50) NOT NULL DEFAULT 'allowed',
        -- - "allowed": Request granted normally
        -- - "captcha_required": User must solve CAPTCHA
        -- - "rate_limited": Request delayed (backoff)
        -- - "blocked": Request rejected immediately
        -- - "logged_only": Request allowed but flagged for review

    -- Client info for fingerprinting
    user_agent TEXT,
        -- HTTP User-Agent header (for device fingerprinting)

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        -- When this request was logged (UTC)

    -- Constraints
    CONSTRAINT chk_demo_audit_tokens CHECK (tokens_used >= 0),
    CONSTRAINT chk_demo_audit_response_length CHECK (response_length >= 0),
    CONSTRAINT chk_demo_audit_abuse_score CHECK (
        abuse_score >= 0.0 AND abuse_score <= 1.0
    ),
    CONSTRAINT chk_demo_audit_action CHECK (
        action_taken IN ('allowed', 'captcha_required', 'rate_limited', 'blocked', 'logged_only')
    ),
    CONSTRAINT chk_demo_audit_block_reason CHECK (
        (is_blocked = false AND block_reason IS NULL) OR
        (is_blocked = true AND block_reason IS NOT NULL)
    )
);

-- ============================================================================
-- INDEXES - Optimized for security queries and analysis
-- ============================================================================

-- Security: Find all requests from suspicious IP
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_ip_abuse
    ON :SCHEMA_NAME.demo_audit_log(ip_address, created_at DESC)
    WHERE abuse_score > 0.7;

-- Security: Find all requests from suspicious fingerprint
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_fingerprint_abuse
    ON :SCHEMA_NAME.demo_audit_log(client_fingerprint, created_at DESC)
    WHERE abuse_score > 0.7;

-- Analytics: Requests blocked by reason
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_block_reason
    ON :SCHEMA_NAME.demo_audit_log(block_reason, created_at DESC)
    WHERE is_blocked = true;

-- User analysis: Track single user's activity
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_user_key
    ON :SCHEMA_NAME.demo_audit_log(user_key, created_at DESC)
    WHERE user_key IS NOT NULL;

-- Time-series: Recent activity (e.g., last 24h)
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_timestamp
    ON :SCHEMA_NAME.demo_audit_log(created_at DESC);

-- Abuse detection: Find high-abuse-score requests
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_abuse_score
    ON :SCHEMA_NAME.demo_audit_log(abuse_score DESC, created_at DESC)
    WHERE abuse_score > 0.5;

-- Token tracking: Monitor token consumption patterns
CREATE INDEX IF NOT EXISTS idx_demo_audit_log_tokens
    ON :SCHEMA_NAME.demo_audit_log(created_at DESC)
    WHERE tokens_used > 0;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT ON :SCHEMA_NAME.demo_audit_log TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.demo_audit_log_id_seq TO mcp_user;

-- Restrict DELETE/UPDATE to admin only (audit trail immutability)
-- GRANT DELETE, UPDATE are NOT granted to mcp_user

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Demo audit log table created';
    RAISE NOTICE '   - Request-level audit trail for security analysis';
    RAISE NOTICE '   - IP address, fingerprint, and abuse scoring';
    RAISE NOTICE '   - Token consumption tracking per request';
    RAISE NOTICE '   - Block reason and action tracking';
    RAISE NOTICE '   - Immutable audit trail (inserts only)';
END $$;
