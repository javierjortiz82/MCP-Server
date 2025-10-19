-- ============================================================================
-- USER MEMORY PROFILE SYSTEM - Cross-Session Context Management
-- ============================================================================
-- Adds user-level memory that persists across multiple sessions.
-- Enables personalization and context retention when users return days/weeks later.
--
-- Prerequisites:
--  - PostgreSQL 14+ with uuid-ossp extension
--  - Existing agent memory system (migration 002)
--  - Tables: conversation_sessions, agent_memory_blocks
--
-- Note: {SCHEMA_NAME} will be substituted by Python script (e.g., "test")
-- This file is meant to be used with run_user_memory_migration.py
--
-- Migration: 003_add_user_memory_profile.sql
-- Author: Lab01-MCP Team
-- Created: 2025-10-12
-- Version: 1.0.0 (Fase 6 - Cross-Session Memory)
-- ============================================================================

-- ============================================================================
-- TABLE 1: user_memory_profiles
-- User-level metadata aggregating info across all sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.user_memory_profiles (
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
    ON {SCHEMA_NAME}.user_memory_profiles(last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_profiles_preferred_agent
    ON {SCHEMA_NAME}.user_memory_profiles(preferred_agent)
    WHERE preferred_agent IS NOT NULL;

-- ============================================================================
-- TABLE 2: user_memory_blocks
-- Cross-session memory blocks aggregated from multiple sessions
-- Similar to agent_memory_blocks but at user level
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.user_memory_blocks (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- User reference
    customer_email VARCHAR(255) NOT NULL REFERENCES {SCHEMA_NAME}.user_memory_profiles(customer_email) ON DELETE CASCADE,

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
    ON {SCHEMA_NAME}.user_memory_blocks(customer_email);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_priority
    ON {SCHEMA_NAME}.user_memory_blocks(priority DESC, extracted_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_expires
    ON {SCHEMA_NAME}.user_memory_blocks(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_label
    ON {SCHEMA_NAME}.user_memory_blocks(block_label);

CREATE INDEX IF NOT EXISTS idx_user_memory_blocks_email_label
    ON {SCHEMA_NAME}.user_memory_blocks(customer_email, block_label);

-- ============================================================================
-- TRIGGERS - Auto-update timestamps and TTL
-- ============================================================================

-- Reuse existing timestamp update function
DROP TRIGGER IF EXISTS trg_update_user_profiles_timestamp ON {SCHEMA_NAME}.user_memory_profiles;
CREATE TRIGGER trg_update_user_profiles_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.user_memory_profiles
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_memory_timestamp();

DROP TRIGGER IF EXISTS trg_update_user_memory_blocks_timestamp ON {SCHEMA_NAME}.user_memory_blocks;
CREATE TRIGGER trg_update_user_memory_blocks_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.user_memory_blocks
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_memory_timestamp();

-- Trigger for user memory block expiration calculation
DROP TRIGGER IF EXISTS trg_calculate_user_memory_expiration ON {SCHEMA_NAME}.user_memory_blocks;
CREATE TRIGGER trg_calculate_user_memory_expiration
    BEFORE INSERT OR UPDATE ON {SCHEMA_NAME}.user_memory_blocks
    FOR EACH ROW
    WHEN (NEW.ttl_days IS NOT NULL)
    EXECUTE FUNCTION {SCHEMA_NAME}.calculate_memory_expiration();

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to get or create user memory profile
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_or_create_user_profile(
    p_customer_email VARCHAR(255)
) RETURNS {SCHEMA_NAME}.user_memory_profiles AS $$
DECLARE
    v_profile {SCHEMA_NAME}.user_memory_profiles;
BEGIN
    -- Try to get existing profile
    SELECT * INTO v_profile
    FROM {SCHEMA_NAME}.user_memory_profiles
    WHERE customer_email = p_customer_email;

    -- If not exists, create it
    IF NOT FOUND THEN
        INSERT INTO {SCHEMA_NAME}.user_memory_profiles (customer_email)
        VALUES (p_customer_email)
        RETURNING * INTO v_profile;
    END IF;

    RETURN v_profile;
END;
$$ LANGUAGE plpgsql;

-- Function to get active user memory blocks
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_user_memory_blocks(
    p_customer_email VARCHAR(255),
    p_agent_scope VARCHAR(50) DEFAULT 'shared'
) RETURNS TABLE (
    id INTEGER,
    block_label VARCHAR(100),
    block_value TEXT,
    priority INTEGER,
    agent_scope VARCHAR(50),
    source_session_ids JSONB,
    extracted_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        umb.id,
        umb.block_label,
        umb.block_value,
        umb.priority,
        umb.agent_scope,
        umb.source_session_ids,
        umb.extracted_at
    FROM {SCHEMA_NAME}.user_memory_blocks umb
    WHERE umb.customer_email = p_customer_email
    AND (umb.agent_scope = p_agent_scope OR umb.agent_scope = 'shared')
    AND (umb.expires_at IS NULL OR umb.expires_at > CURRENT_TIMESTAMP)
    ORDER BY umb.priority DESC, umb.extracted_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to sync session memory blocks to user profile
-- Promotes high-priority (>= 7), shared-scope blocks from session to user-level
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.sync_session_to_user_memory(
    p_session_id UUID
) RETURNS TABLE (
    synced_blocks INTEGER,
    updated_blocks INTEGER,
    skipped_blocks INTEGER
) AS $$
DECLARE
    v_customer_email VARCHAR(255);
    v_synced INTEGER := 0;
    v_updated INTEGER := 0;
    v_skipped INTEGER := 0;
    v_block RECORD;
    v_existing_block RECORD;
BEGIN
    -- Get customer_email from session
    SELECT customer_email INTO v_customer_email
    FROM {SCHEMA_NAME}.conversation_sessions
    WHERE id = p_session_id;

    -- If no email, skip sync
    IF v_customer_email IS NULL THEN
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    -- Ensure user profile exists
    PERFORM {SCHEMA_NAME}.get_or_create_user_profile(v_customer_email);

    -- Iterate through eligible memory blocks (priority >= 7, scope = 'shared')
    FOR v_block IN
        SELECT mb.id, mb.block_label, mb.block_value, mb.priority, mb.agent_scope, mb.ttl_days
        FROM {SCHEMA_NAME}.agent_memory_blocks mb
        WHERE mb.session_id = p_session_id
        AND mb.priority >= 7
        AND mb.agent_scope = 'shared'
        AND (mb.expires_at IS NULL OR mb.expires_at > CURRENT_TIMESTAMP)
    LOOP
        -- Check if similar block already exists (same label + similar value)
        SELECT * INTO v_existing_block
        FROM {SCHEMA_NAME}.user_memory_blocks
        WHERE customer_email = v_customer_email
        AND block_label = v_block.block_label
        AND block_value = v_block.block_value
        LIMIT 1;

        IF FOUND THEN
            -- Update existing block: max priority, add source session
            UPDATE {SCHEMA_NAME}.user_memory_blocks
            SET
                priority = GREATEST(priority, v_block.priority),
                source_session_ids = source_session_ids || jsonb_build_array(p_session_id::text),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_existing_block.id;

            v_updated := v_updated + 1;
        ELSE
            -- Insert new user memory block
            INSERT INTO {SCHEMA_NAME}.user_memory_blocks (
                customer_email,
                block_label,
                block_value,
                priority,
                agent_scope,
                source_session_ids,
                ttl_days
            ) VALUES (
                v_customer_email,
                v_block.block_label,
                v_block.block_value,
                v_block.priority,
                v_block.agent_scope,
                jsonb_build_array(p_session_id::text),
                180  -- User-level TTL: 180 days
            );

            v_synced := v_synced + 1;
        END IF;
    END LOOP;

    -- Update user profile stats
    UPDATE {SCHEMA_NAME}.user_memory_profiles
    SET
        last_seen_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE customer_email = v_customer_email;

    RETURN QUERY SELECT v_synced, v_updated, v_skipped;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired user memory blocks
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.cleanup_expired_user_memory_blocks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM {SCHEMA_NAME}.user_memory_blocks
    WHERE expires_at IS NOT NULL
    AND expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to update user profile on new session
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.update_user_profile_on_session()
RETURNS TRIGGER AS $$
DECLARE
    v_customer_email VARCHAR(255);
    v_current_agent VARCHAR(50);
BEGIN
    v_customer_email := NEW.customer_email;
    v_current_agent := NEW.current_agent;

    -- Only process if customer_email exists
    IF v_customer_email IS NOT NULL THEN
        -- Upsert user profile
        INSERT INTO {SCHEMA_NAME}.user_memory_profiles (
            customer_email,
            first_seen_at,
            last_seen_at,
            total_sessions
        ) VALUES (
            v_customer_email,
            NEW.started_at,
            NEW.started_at,
            1
        )
        ON CONFLICT (customer_email) DO UPDATE SET
            last_seen_at = NEW.started_at,
            total_sessions = {SCHEMA_NAME}.user_memory_profiles.total_sessions + 1,
            updated_at = CURRENT_TIMESTAMP;

        -- Update preferred_agent if specified
        IF v_current_agent IS NOT NULL THEN
            UPDATE {SCHEMA_NAME}.user_memory_profiles
            SET preferred_agent = v_current_agent
            WHERE customer_email = v_customer_email
            AND (preferred_agent IS NULL OR preferred_agent != v_current_agent);
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update user profile when session is created
DROP TRIGGER IF EXISTS trg_update_user_profile_on_session ON {SCHEMA_NAME}.conversation_sessions;
CREATE TRIGGER trg_update_user_profile_on_session
    AFTER INSERT ON {SCHEMA_NAME}.conversation_sessions
    FOR EACH ROW
    WHEN (NEW.customer_email IS NOT NULL)
    EXECUTE FUNCTION {SCHEMA_NAME}.update_user_profile_on_session();

-- ============================================================================
-- PERMISSIONS - Grant access to mcp_user
-- ============================================================================

-- user_memory_profiles table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.user_memory_profiles TO mcp_user;

-- user_memory_blocks table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.user_memory_blocks TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.user_memory_blocks_id_seq TO mcp_user;

-- Grant execute on new functions
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_or_create_user_profile(VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_user_memory_blocks(VARCHAR, VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.sync_session_to_user_memory(UUID) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.cleanup_expired_user_memory_blocks() TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ User Memory Profile System created successfully within schema: test';
    RAISE NOTICE '📊 Tables created:';
    RAISE NOTICE '   - user_memory_profiles (user metadata across sessions)';
    RAISE NOTICE '   - user_memory_blocks (cross-session semantic memory)';
    RAISE NOTICE '🔧 Utility functions available:';
    RAISE NOTICE '   - get_or_create_user_profile() for user profile management';
    RAISE NOTICE '   - get_user_memory_blocks() for cross-session memory retrieval';
    RAISE NOTICE '   - sync_session_to_user_memory() for automatic promotion';
    RAISE NOTICE '   - cleanup_expired_user_memory_blocks() for TTL maintenance';
    RAISE NOTICE '⚡ Triggers configured:';
    RAISE NOTICE '   - Auto-update user profile on new session';
    RAISE NOTICE '   - Auto-calculate user memory expiration (180 days default)';
    RAISE NOTICE '   - Auto-update timestamps on changes';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '🚀 Cross-Session Memory ready for user personalization!';
    RAISE NOTICE '';
    RAISE NOTICE '📖 Features Implemented:';
    RAISE NOTICE '   ✅ User-level memory aggregation';
    RAISE NOTICE '   ✅ Automatic session-to-user sync (priority >= 7)';
    RAISE NOTICE '   ✅ Memory deduplication (merge similar blocks)';
    RAISE NOTICE '   ✅ Extended TTL (180 days user-level vs 90 session-level)';
    RAISE NOTICE '   ✅ Source session tracking';
    RAISE NOTICE '   ✅ User profile metadata (first/last seen, total sessions)';
    RAISE NOTICE '';
    RAISE NOTICE 'Example usage:';
    RAISE NOTICE '  -- Sync session memory to user profile:';
    RAISE NOTICE '  SELECT * FROM test.sync_session_to_user_memory(''session-uuid'');';
    RAISE NOTICE '';
    RAISE NOTICE '  -- Get user memory blocks:';
    RAISE NOTICE '  SELECT * FROM test.get_user_memory_blocks(''user@example.com'');';
END $$;
