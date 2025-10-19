-- ============================================================================
-- AGENT MEMORY SYSTEM - Persistent Context Management
-- ============================================================================
-- Creates tables for multi-agent memory persistence and context sharing.
-- Follows 2025 best practices: Memory Blocks (Letta), Hybrid Memory, Context Transfer.
--
-- Prerequisites:
--  - PostgreSQL 14+ with uuid-ossp extension
--  - Existing schema with products and appointments tables
--  - Extension: CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
--
-- Note: {SCHEMA_NAME} will be substituted by Python script (e.g., "test")
-- This file is meant to be used with run_memory_migration.py, not executed directly
--
-- Migration: 002_add_agent_memory.sql
-- Author: Lab01-MCP Team
-- Created: 2025-10-12
-- Version: 1.0.0
-- ============================================================================

-- Ensure uuid-ossp extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE 1: conversation_sessions
-- Tracks user conversation sessions with metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.conversation_sessions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User identification
    customer_email VARCHAR(255),
    session_id VARCHAR(255) UNIQUE NOT NULL,

    -- Session metadata
    started_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    last_activity_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    current_agent VARCHAR(50),  -- 'sales', 'booking', 'general', NULL

    -- Flexible metadata storage (device, source, campaign, etc)
    metadata JSONB DEFAULT '{}'::JSONB,

    -- Audit timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_current_agent CHECK (
        current_agent IS NULL OR
        current_agent IN ('sales', 'booking', 'general')
    )
);

-- Indexes for conversation_sessions
CREATE INDEX IF NOT EXISTS idx_conv_sessions_customer_email
    ON {SCHEMA_NAME}.conversation_sessions(customer_email)
    WHERE customer_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conv_sessions_session_id
    ON {SCHEMA_NAME}.conversation_sessions(session_id);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_last_activity
    ON {SCHEMA_NAME}.conversation_sessions(last_activity_at DESC);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_current_agent
    ON {SCHEMA_NAME}.conversation_sessions(current_agent)
    WHERE current_agent IS NOT NULL;

-- ============================================================================
-- TABLE 2: conversation_messages
-- Individual messages with full context and metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.conversation_messages (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Session reference
    session_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.conversation_sessions(id) ON DELETE CASCADE,

    -- Message metadata
    role VARCHAR(20) NOT NULL,  -- 'user' | 'model'
    agent_name VARCHAR(50),  -- Which agent generated response (NULL for user messages)
    intent VARCHAR(50),  -- Classified intent: 'sales' | 'booking' | 'general'

    -- Message content
    message_text TEXT NOT NULL,

    -- Function calling metadata (MCP tools used)
    tool_calls JSONB,  -- [{tool_name, args, result, execution_time_ms}]

    -- Performance metrics
    response_time_ms INTEGER,
    token_count INTEGER,

    -- Audit timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_message_role CHECK (role IN ('user', 'model')),
    CONSTRAINT chk_message_intent CHECK (
        intent IS NULL OR
        intent IN ('sales', 'booking', 'general')
    )
);

-- Indexes for conversation_messages
CREATE INDEX IF NOT EXISTS idx_conv_messages_session_id
    ON {SCHEMA_NAME}.conversation_messages(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conv_messages_intent
    ON {SCHEMA_NAME}.conversation_messages(intent)
    WHERE intent IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conv_messages_agent
    ON {SCHEMA_NAME}.conversation_messages(agent_name)
    WHERE agent_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conv_messages_role
    ON {SCHEMA_NAME}.conversation_messages(role);

-- ============================================================================
-- TABLE 3: agent_memory_blocks
-- Semantic memory extracted by LLM - "facts about user"
-- Follows Memory Blocks pattern (Letta) for structured context management
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.agent_memory_blocks (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Session reference
    session_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.conversation_sessions(id) ON DELETE CASCADE,

    -- Memory block structure (Letta pattern)
    block_label VARCHAR(100) NOT NULL,  -- 'user_preferences', 'purchase_history', 'product_interest', etc
    block_value TEXT NOT NULL,  -- The actual memory content (LLM-extracted)

    -- Priority and scope management
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 10),  -- 0-10 priority scoring
    agent_scope VARCHAR(50) DEFAULT 'shared',  -- 'shared', 'sales', 'booking', 'general'

    -- TTL (Time To Live) management
    ttl_days INTEGER DEFAULT 90 CHECK (ttl_days > 0),
    extracted_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    expires_at TIMESTAMPTZ,  -- Auto-calculated on insert/update

    -- Audit timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_memory_agent_scope CHECK (
        agent_scope IN ('shared', 'sales', 'booking', 'general')
    )
);

-- Indexes for agent_memory_blocks
CREATE INDEX IF NOT EXISTS idx_memory_blocks_session
    ON {SCHEMA_NAME}.agent_memory_blocks(session_id);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_priority
    ON {SCHEMA_NAME}.agent_memory_blocks(priority DESC, extracted_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_expires
    ON {SCHEMA_NAME}.agent_memory_blocks(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_memory_blocks_scope
    ON {SCHEMA_NAME}.agent_memory_blocks(agent_scope);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_label
    ON {SCHEMA_NAME}.agent_memory_blocks(block_label);

-- ============================================================================
-- TABLE 4: agent_context_transfers
-- Tracks handoffs between agents with context preservation
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.agent_context_transfers (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Session reference
    session_id UUID NOT NULL REFERENCES {SCHEMA_NAME}.conversation_sessions(id) ON DELETE CASCADE,

    -- Transfer metadata
    from_agent VARCHAR(50) NOT NULL,
    to_agent VARCHAR(50) NOT NULL,
    transfer_reason VARCHAR(255),

    -- Context preservation
    context_summary TEXT,  -- LLM-generated summary of what to preserve
    memory_blocks_transferred INTEGER DEFAULT 0,

    -- Success tracking
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Audit timestamp
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT chk_transfer_agents CHECK (
        from_agent IN ('sales', 'booking', 'general') AND
        to_agent IN ('sales', 'booking', 'general') AND
        from_agent != to_agent
    )
);

-- Indexes for agent_context_transfers
CREATE INDEX IF NOT EXISTS idx_context_transfers_session
    ON {SCHEMA_NAME}.agent_context_transfers(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_context_transfers_from_to
    ON {SCHEMA_NAME}.agent_context_transfers(from_agent, to_agent);

CREATE INDEX IF NOT EXISTS idx_context_transfers_success
    ON {SCHEMA_NAME}.agent_context_transfers(success);

-- ============================================================================
-- TRIGGERS - Auto-update timestamps and TTL calculation
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.update_memory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate expires_at based on ttl_days
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.calculate_memory_expiration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ttl_days IS NOT NULL THEN
        NEW.expires_at = NEW.extracted_at + (NEW.ttl_days || ' days')::INTERVAL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to update last_activity_at on new message
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE {SCHEMA_NAME}.conversation_sessions
    SET last_activity_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for conversation_sessions timestamp
DROP TRIGGER IF EXISTS trg_update_conv_sessions_timestamp ON {SCHEMA_NAME}.conversation_sessions;
CREATE TRIGGER trg_update_conv_sessions_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_memory_timestamp();

-- Trigger for agent_memory_blocks timestamp
DROP TRIGGER IF EXISTS trg_update_memory_blocks_timestamp ON {SCHEMA_NAME}.agent_memory_blocks;
CREATE TRIGGER trg_update_memory_blocks_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.agent_memory_blocks
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_memory_timestamp();

-- Trigger for memory expiration calculation
DROP TRIGGER IF EXISTS trg_calculate_memory_expiration ON {SCHEMA_NAME}.agent_memory_blocks;
CREATE TRIGGER trg_calculate_memory_expiration
    BEFORE INSERT OR UPDATE ON {SCHEMA_NAME}.agent_memory_blocks
    FOR EACH ROW
    WHEN (NEW.ttl_days IS NOT NULL)
    EXECUTE FUNCTION {SCHEMA_NAME}.calculate_memory_expiration();

-- Trigger to update session activity on new message
DROP TRIGGER IF EXISTS trg_update_session_activity ON {SCHEMA_NAME}.conversation_messages;
CREATE TRIGGER trg_update_session_activity
    AFTER INSERT ON {SCHEMA_NAME}.conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_session_activity();

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to get recent messages for a session
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_recent_messages(
    p_session_id UUID,
    p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
    id INTEGER,
    role VARCHAR(20),
    agent_name VARCHAR(50),
    message_text TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.role,
        m.agent_name,
        m.message_text,
        m.created_at
    FROM {SCHEMA_NAME}.conversation_messages m
    WHERE m.session_id = p_session_id
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to get active memory blocks for a session
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_active_memory_blocks(
    p_session_id UUID,
    p_agent_scope VARCHAR(50) DEFAULT 'shared'
) RETURNS TABLE (
    id INTEGER,
    block_label VARCHAR(100),
    block_value TEXT,
    priority INTEGER,
    agent_scope VARCHAR(50),
    extracted_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mb.id,
        mb.block_label,
        mb.block_value,
        mb.priority,
        mb.agent_scope,
        mb.extracted_at
    FROM {SCHEMA_NAME}.agent_memory_blocks mb
    WHERE mb.session_id = p_session_id
    AND (mb.agent_scope = p_agent_scope OR mb.agent_scope = 'shared')
    AND (mb.expires_at IS NULL OR mb.expires_at > CURRENT_TIMESTAMP)
    ORDER BY mb.priority DESC, mb.extracted_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to cleanup expired memory blocks
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.cleanup_expired_memory_blocks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM {SCHEMA_NAME}.agent_memory_blocks
    WHERE expires_at IS NOT NULL
    AND expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get session statistics
CREATE OR REPLACE FUNCTION {SCHEMA_NAME}.get_session_statistics(p_session_id UUID)
RETURNS TABLE (
    total_messages INTEGER,
    user_messages INTEGER,
    model_messages INTEGER,
    memory_blocks INTEGER,
    context_transfers INTEGER,
    session_duration_minutes INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER as total_messages,
        COUNT(*) FILTER (WHERE role = 'user')::INTEGER as user_messages,
        COUNT(*) FILTER (WHERE role = 'model')::INTEGER as model_messages,
        (SELECT COUNT(*)::INTEGER FROM {SCHEMA_NAME}.agent_memory_blocks WHERE session_id = p_session_id) as memory_blocks,
        (SELECT COUNT(*)::INTEGER FROM {SCHEMA_NAME}.agent_context_transfers WHERE session_id = p_session_id) as context_transfers,
        EXTRACT(EPOCH FROM (s.last_activity_at - s.started_at))::INTEGER / 60 as session_duration_minutes
    FROM {SCHEMA_NAME}.conversation_messages m
    JOIN {SCHEMA_NAME}.conversation_sessions s ON s.id = p_session_id
    WHERE m.session_id = p_session_id
    GROUP BY s.last_activity_at, s.started_at;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- PERMISSIONS - Grant access to mcp_user
-- ============================================================================

-- conversation_sessions table (UUID primary key, no sequence)
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.conversation_sessions TO mcp_user;

-- conversation_messages table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.conversation_messages TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.conversation_messages_id_seq TO mcp_user;

-- agent_memory_blocks table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.agent_memory_blocks TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.agent_memory_blocks_id_seq TO mcp_user;

-- agent_context_transfers table
GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.agent_context_transfers TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.agent_context_transfers_id_seq TO mcp_user;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_recent_messages(UUID, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_active_memory_blocks(UUID, VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.cleanup_expired_memory_blocks() TO mcp_user;
GRANT EXECUTE ON FUNCTION {SCHEMA_NAME}.get_session_statistics(UUID) TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Agent Memory System created successfully within schema: test';
    RAISE NOTICE '📊 Tables created:';
    RAISE NOTICE '   - conversation_sessions (user session tracking)';
    RAISE NOTICE '   - conversation_messages (individual messages with metadata)';
    RAISE NOTICE '   - agent_memory_blocks (semantic memory - Memory Blocks pattern)';
    RAISE NOTICE '   - agent_context_transfers (agent handoff tracking)';
    RAISE NOTICE '🔧 Utility functions available:';
    RAISE NOTICE '   - get_recent_messages() for history retrieval';
    RAISE NOTICE '   - get_active_memory_blocks() for semantic memory';
    RAISE NOTICE '   - cleanup_expired_memory_blocks() for TTL maintenance';
    RAISE NOTICE '   - get_session_statistics() for analytics';
    RAISE NOTICE '⚡ Triggers configured:';
    RAISE NOTICE '   - Auto-update timestamps';
    RAISE NOTICE '   - Auto-calculate memory expiration (TTL)';
    RAISE NOTICE '   - Auto-update session activity on new messages';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '🚀 Agent Memory System ready for multi-agent context management!';
    RAISE NOTICE '';
    RAISE NOTICE '📖 Best Practices Implemented:';
    RAISE NOTICE '   ✅ Memory Blocks Pattern (Letta)';
    RAISE NOTICE '   ✅ Hybrid Memory (Short-term + Long-term)';
    RAISE NOTICE '   ✅ Context Transfer Tracking';
    RAISE NOTICE '   ✅ Priority Scoring';
    RAISE NOTICE '   ✅ TTL Management';
    RAISE NOTICE '   ✅ Multi-Agent Scope Support';
END $$;