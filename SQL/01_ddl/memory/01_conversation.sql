-- ============================================================================
-- CONVERSATION SESSIONS TABLE - User conversation session tracking
-- ============================================================================
-- Tracks user conversation sessions with metadata for multi-agent system

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.conversation_sessions (
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

    -- Session lifecycle management
    archived BOOLEAN DEFAULT FALSE NOT NULL,

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
    ON :SCHEMA_NAME.conversation_sessions(customer_email)
    WHERE customer_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conv_sessions_session_id
    ON :SCHEMA_NAME.conversation_sessions(session_id);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_last_activity
    ON :SCHEMA_NAME.conversation_sessions(last_activity_at DESC);

CREATE INDEX IF NOT EXISTS idx_conv_sessions_current_agent
    ON :SCHEMA_NAME.conversation_sessions(current_agent)
    WHERE current_agent IS NOT NULL;

-- Index for session lifecycle (archived flag)
CREATE INDEX IF NOT EXISTS idx_sessions_archived
    ON :SCHEMA_NAME.conversation_sessions(archived)
    WHERE archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_sessions_last_activity_archived
    ON :SCHEMA_NAME.conversation_sessions(last_activity_at, archived);

-- Index for anonymous session cleanup
CREATE INDEX IF NOT EXISTS idx_sessions_email_null
    ON :SCHEMA_NAME.conversation_sessions(customer_email)
    WHERE customer_email IS NULL;

-- ============================================================================
-- CONVERSATION_MESSAGES TABLE - Individual messages with full context
-- ============================================================================
CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.conversation_messages (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Session reference
    session_id UUID NOT NULL REFERENCES :SCHEMA_NAME.conversation_sessions(id) ON DELETE CASCADE,

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
    ON :SCHEMA_NAME.conversation_messages(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conv_messages_intent
    ON :SCHEMA_NAME.conversation_messages(intent)
    WHERE intent IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conv_messages_agent
    ON :SCHEMA_NAME.conversation_messages(agent_name)
    WHERE agent_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conv_messages_role
    ON :SCHEMA_NAME.conversation_messages(role);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.conversation_sessions TO mcp_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.conversation_messages TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.conversation_messages_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Conversation tables created:';
    RAISE NOTICE '   - conversation_sessions (session tracking)';
    RAISE NOTICE '   - conversation_messages (message history)';
    RAISE NOTICE '   - Session lifecycle management (archived flag)';
END $$;
