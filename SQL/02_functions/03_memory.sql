-- ============================================================================
-- MEMORY SYSTEM FUNCTIONS - Agent and user memory management
-- ============================================================================

-- Function to update memory timestamps
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.update_memory_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate expires_at based on ttl_days
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.calculate_memory_expiration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ttl_days IS NOT NULL THEN
        NEW.expires_at = NEW.extracted_at + (NEW.ttl_days || ' days')::INTERVAL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to update last_activity_at on new message
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE :'SCHEMA_NAME'.conversation_sessions
    SET last_activity_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS - Memory system lifecycle
-- ============================================================================

-- Conversation sessions timestamp
DROP TRIGGER IF EXISTS trg_update_conv_sessions_timestamp ON :'SCHEMA_NAME'.conversation_sessions;
CREATE TRIGGER trg_update_conv_sessions_timestamp
    BEFORE UPDATE ON :'SCHEMA_NAME'.conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION :'SCHEMA_NAME'.update_memory_timestamp();

-- Agent memory blocks timestamp
DROP TRIGGER IF EXISTS trg_update_memory_blocks_timestamp ON :'SCHEMA_NAME'.agent_memory_blocks;
CREATE TRIGGER trg_update_memory_blocks_timestamp
    BEFORE UPDATE ON :'SCHEMA_NAME'.agent_memory_blocks
    FOR EACH ROW
    EXECUTE FUNCTION :'SCHEMA_NAME'.update_memory_timestamp();

-- Memory expiration calculation
DROP TRIGGER IF EXISTS trg_calculate_memory_expiration ON :'SCHEMA_NAME'.agent_memory_blocks;
CREATE TRIGGER trg_calculate_memory_expiration
    BEFORE INSERT OR UPDATE ON :'SCHEMA_NAME'.agent_memory_blocks
    FOR EACH ROW
    WHEN (NEW.ttl_days IS NOT NULL)
    EXECUTE FUNCTION :'SCHEMA_NAME'.calculate_memory_expiration();

-- Update session activity on new message
DROP TRIGGER IF EXISTS trg_update_session_activity ON :'SCHEMA_NAME'.conversation_messages;
CREATE TRIGGER trg_update_session_activity
    AFTER INSERT ON :'SCHEMA_NAME'.conversation_messages
    FOR EACH ROW
    EXECUTE FUNCTION :'SCHEMA_NAME'.update_session_activity();

-- User memory blocks timestamp
DROP TRIGGER IF EXISTS trg_update_user_memory_blocks_timestamp ON :'SCHEMA_NAME'.user_memory_blocks;
CREATE TRIGGER trg_update_user_memory_blocks_timestamp
    BEFORE UPDATE ON :'SCHEMA_NAME'.user_memory_blocks
    FOR EACH ROW
    EXECUTE FUNCTION :'SCHEMA_NAME'.update_memory_timestamp();

-- User memory expiration calculation
DROP TRIGGER IF EXISTS trg_calculate_user_memory_expiration ON :'SCHEMA_NAME'.user_memory_blocks;
CREATE TRIGGER trg_calculate_user_memory_expiration
    BEFORE INSERT OR UPDATE ON :'SCHEMA_NAME'.user_memory_blocks
    FOR EACH ROW
    WHEN (NEW.ttl_days IS NOT NULL)
    EXECUTE FUNCTION :'SCHEMA_NAME'.calculate_memory_expiration();

-- User profiles timestamp
DROP TRIGGER IF EXISTS trg_update_user_profiles_timestamp ON :'SCHEMA_NAME'.user_memory_profiles;
CREATE TRIGGER trg_update_user_profiles_timestamp
    BEFORE UPDATE ON :'SCHEMA_NAME'.user_memory_profiles
    FOR EACH ROW
    EXECUTE FUNCTION :'SCHEMA_NAME'.update_memory_timestamp();

-- ============================================================================
-- FUNCTION: get_recent_messages() - Retrieve conversation history
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.get_recent_messages(
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
    FROM :'SCHEMA_NAME'.conversation_messages m
    WHERE m.session_id = p_session_id
    ORDER BY m.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: get_active_memory_blocks() - Retrieve session memory
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.get_active_memory_blocks(
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
    FROM :'SCHEMA_NAME'.agent_memory_blocks mb
    WHERE mb.session_id = p_session_id
    AND (mb.agent_scope = p_agent_scope OR mb.agent_scope = 'shared')
    AND (mb.expires_at IS NULL OR mb.expires_at > CURRENT_TIMESTAMP)
    ORDER BY mb.priority DESC, mb.extracted_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: get_or_create_user_profile() - User profile management
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.get_or_create_user_profile(
    p_customer_email VARCHAR(255)
) RETURNS :'SCHEMA_NAME'.user_memory_profiles AS $$
DECLARE
    v_profile :'SCHEMA_NAME'.user_memory_profiles;
BEGIN
    -- Try to get existing profile
    SELECT * INTO v_profile
    FROM :'SCHEMA_NAME'.user_memory_profiles
    WHERE customer_email = p_customer_email;

    -- If not exists, create it
    IF NOT FOUND THEN
        INSERT INTO :'SCHEMA_NAME'.user_memory_profiles (customer_email)
        VALUES (p_customer_email)
        RETURNING * INTO v_profile;
    END IF;

    RETURN v_profile;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: get_user_memory_blocks() - Retrieve user-level memory
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.get_user_memory_blocks(
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
    FROM :'SCHEMA_NAME'.user_memory_blocks umb
    WHERE umb.customer_email = p_customer_email
    AND (umb.agent_scope = p_agent_scope OR umb.agent_scope = 'shared')
    AND (umb.expires_at IS NULL OR umb.expires_at > CURRENT_TIMESTAMP)
    ORDER BY umb.priority DESC, umb.extracted_at DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- FUNCTION: cleanup_expired_memory_blocks() - Maintenance
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.cleanup_expired_memory_blocks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM :'SCHEMA_NAME'.agent_memory_blocks
    WHERE expires_at IS NOT NULL
    AND expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: cleanup_expired_user_memory_blocks() - Maintenance
-- ============================================================================
CREATE OR REPLACE FUNCTION :'SCHEMA_NAME'.cleanup_expired_user_memory_blocks()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM :'SCHEMA_NAME'.user_memory_blocks
    WHERE expires_at IS NOT NULL
    AND expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.get_recent_messages(UUID, INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.get_active_memory_blocks(UUID, VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.get_or_create_user_profile(VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.get_user_memory_blocks(VARCHAR, VARCHAR) TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.cleanup_expired_memory_blocks() TO mcp_user;
GRANT EXECUTE ON FUNCTION :'SCHEMA_NAME'.cleanup_expired_user_memory_blocks() TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Memory system functions created:';
    RAISE NOTICE '   - get_recent_messages() for conversation history';
    RAISE NOTICE '   - get_active_memory_blocks() for session memory';
    RAISE NOTICE '   - get_user_memory_blocks() for user-level memory';
    RAISE NOTICE '   - get_or_create_user_profile() for profile management';
    RAISE NOTICE '   - Cleanup functions for memory lifecycle';
    RAISE NOTICE '   - Memory expiration and timestamp triggers';
END $$;
