-- ============================================================================
-- AGENT MEMORY BLOCKS TABLE - Semantic memory extracted by LLM
-- ============================================================================
-- Follows Memory Blocks pattern (Letta) for structured context management
-- Stores "facts about user" extracted from conversations

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.agent_memory_blocks (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Session reference
    session_id UUID NOT NULL REFERENCES :SCHEMA_NAME.conversation_sessions(id) ON DELETE CASCADE,

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
    ON :SCHEMA_NAME.agent_memory_blocks(session_id);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_priority
    ON :SCHEMA_NAME.agent_memory_blocks(priority DESC, extracted_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_expires
    ON :SCHEMA_NAME.agent_memory_blocks(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_memory_blocks_scope
    ON :SCHEMA_NAME.agent_memory_blocks(agent_scope);

CREATE INDEX IF NOT EXISTS idx_memory_blocks_label
    ON :SCHEMA_NAME.agent_memory_blocks(block_label);

-- ============================================================================
-- AGENT CONTEXT TRANSFERS TABLE - Tracks handoffs between agents
-- ============================================================================
CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.agent_context_transfers (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Session reference
    session_id UUID NOT NULL REFERENCES :SCHEMA_NAME.conversation_sessions(id) ON DELETE CASCADE,

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
    ON :SCHEMA_NAME.agent_context_transfers(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_context_transfers_from_to
    ON :SCHEMA_NAME.agent_context_transfers(from_agent, to_agent);

CREATE INDEX IF NOT EXISTS idx_context_transfers_success
    ON :SCHEMA_NAME.agent_context_transfers(success);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.agent_memory_blocks TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.agent_memory_blocks_id_seq TO mcp_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.agent_context_transfers TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.agent_context_transfers_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Agent memory tables created:';
    RAISE NOTICE '   - agent_memory_blocks (semantic memory extraction)';
    RAISE NOTICE '   - agent_context_transfers (multi-agent handoff tracking)';
    RAISE NOTICE '   - TTL management for memory lifecycle';
    RAISE NOTICE '   - Priority-based memory retention';
END $$;
