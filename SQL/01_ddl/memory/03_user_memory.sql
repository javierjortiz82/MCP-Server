-- ============================================================================
-- USER MEMORY PROFILE SYSTEM - Cross-session context management
-- ============================================================================
-- Adds user-level memory that persists across multiple sessions
-- Enables personalization and context retention when users return days/weeks later

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.user_memory_profiles (
    -- Primary key
    customer_email VARCHAR(255) PRIMARY KEY,

    -- User activity tracking
    first_seen_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_seen_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    total_sessions INTEGER DEFAULT 0,

    -- Agent preferences (most used agent)
    preferred_agent VARCHAR(50),  -- 'sales', 'booking', 'general'

    -- Flexible metadata storage
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Audit timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_user_preferred_agent CHECK (
        preferred_agent IS NULL OR
        preferred_agent IN ('sales', 'booking', 'general')
    )
);

-- Indexes for user_memory_profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_last_seen
    ON :SCHEMA_NAME.user_memory_profiles(last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_profiles_preferred_agent
    ON :SCHEMA_NAME.user_memory_profiles(preferred_agent)
    WHERE preferred_agent IS NOT NULL;

-- ============================================================================
-- USER MEMORY BLOCKS TABLE - Cross-session memory aggregation
-- ============================================================================
-- Similar to agent_memory_blocks but at user level
CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.user_memory_blocks (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- User reference
    customer_email VARCHAR(255) NOT NULL REFERENCES :SCHEMA_NAME.user_memory_profiles(customer_email) ON DELETE CASCADE,

    -- Memory block structure (same as agent_memory_blocks)
    block_label VARCHAR(100) NOT NULL,  -- 'user_preferences', 'product_interest', etc
    block_value TEXT NOT NULL,  -- The memory content

    -- Priority and scope
    priority INTEGER DEFAULT 7 CHECK (priority >= 0 AND priority <= 10),
    agent_scope VARCHAR(50) DEFAULT 'shared',  -- Only 'shared' blocks sync to user-level

    -- Source tracking (which sessions contributed this memory)
    source_session_ids JSONB DEFAULT '[]'::JSONB,  -- Array of session UUIDs

    -- TTL management (longer than session-level: 180 days vs 90)
    ttl_days INTEGER DEFAULT 180 CHECK (ttl_days > 0),
    extracted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,  -- Auto-calculated on insert/update

    -- Audit timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_user_memory_agent_scope CHECK (
        agent_scope IN ('shared', 'sales', 'booking', 'general')
    )
);

-- Indexes for user_memory_blocks
CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_email
    ON :SCHEMA_NAME.user_memory_blocks(customer_email);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_priority
    ON :SCHEMA_NAME.user_memory_blocks(priority DESC, extracted_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_expires
    ON :SCHEMA_NAME.user_memory_blocks(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_label
    ON :SCHEMA_NAME.user_memory_blocks(block_label);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_email_label
    ON :SCHEMA_NAME.user_memory_blocks(customer_email, block_label);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.user_memory_profiles TO mcp_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.user_memory_blocks TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.user_memory_blocks_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ User memory tables created:';
    RAISE NOTICE '   - user_memory_profiles (cross-session user metadata)';
    RAISE NOTICE '   - user_memory_blocks (persistent user-level memory)';
    RAISE NOTICE '   - Extended TTL for user-level retention (180 days)';
    RAISE NOTICE '   - Source session tracking and memory deduplication';
END $$;
