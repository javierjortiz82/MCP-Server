-- ============================================================================
-- MEMORY SYNC FUNCTIONS - Session to User Memory Synchronization
-- ============================================================================
-- Functions for automatic synchronization of high-priority session memory
-- blocks to persistent user memory profiles
--
-- Key Features:
-- - Auto-sync inactive sessions (>30 min) with high-priority blocks
-- - Trigger-based sync on session activity resume
-- - Session statistics and similarity thresholds
-- - User profile management on session creation/update
--
-- Created: 2025-10-19 (Extracted from production database)
-- ============================================================================

-- ============================================================================
-- 1. SYNC SESSION TO USER MEMORY
-- ============================================================================
-- Copies high-priority memory blocks from a session to user memory profile
-- Only syncs blocks with priority >= 7 and scope = 'shared'
-- Handles duplicates intelligently (merge priorities, track sources)

CREATE OR REPLACE FUNCTION test.sync_session_to_user_memory(p_session_id UUID)
RETURNS TABLE(synced_blocks INTEGER, updated_blocks INTEGER, skipped_blocks INTEGER)
LANGUAGE plpgsql
AS $function$
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
    FROM test.conversation_sessions
    WHERE id = p_session_id;

    -- If no email, skip sync
    IF v_customer_email IS NULL THEN
        RETURN QUERY SELECT 0, 0, 0;
        RETURN;
    END IF;

    -- Ensure user profile exists
    PERFORM test.get_or_create_user_profile(v_customer_email);

    -- Iterate through eligible memory blocks (priority >= 7, scope = 'shared')
    FOR v_block IN
        SELECT mb.id, mb.block_label, mb.block_value, mb.priority, mb.agent_scope, mb.ttl_days
        FROM test.agent_memory_blocks mb
        WHERE mb.session_id = p_session_id
        AND mb.priority >= 7
        AND mb.agent_scope = 'shared'
        AND (mb.expires_at IS NULL OR mb.expires_at > CURRENT_TIMESTAMP)
    LOOP
        -- Check if similar block already exists (same label + similar value)
        SELECT * INTO v_existing_block
        FROM test.user_memory_blocks
        WHERE customer_email = v_customer_email
        AND block_label = v_block.block_label
        AND block_value = v_block.block_value
        LIMIT 1;

        IF FOUND THEN
            -- Update existing block: max priority, add source session
            UPDATE test.user_memory_blocks
            SET
                priority = GREATEST(priority, v_block.priority),
                source_session_ids = source_session_ids || jsonb_build_array(p_session_id::TEXT),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = v_existing_block.id;

            v_updated := v_updated + 1;
        ELSE
            -- Insert new user memory block
            INSERT INTO test.user_memory_blocks (
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
                jsonb_build_array(p_session_id::TEXT),
                180  -- User-level TTL: 180 days
            );

            v_synced := v_synced + 1;
        END IF;
    END LOOP;

    -- Update user profile stats
    UPDATE test.user_memory_profiles
    SET
        last_seen_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE customer_email = v_customer_email;

    RETURN QUERY SELECT v_synced, v_updated, v_skipped;
END;
$function$;

-- ============================================================================
-- 2. AUTO-SYNC INACTIVE SESSIONS
-- ============================================================================
-- Automatically syncs high-priority blocks from inactive sessions to user memory
-- Triggered by scheduler (e.g., cron job every 30 minutes)
-- Processes max 100 sessions per call for performance

CREATE OR REPLACE FUNCTION test.auto_sync_inactive_sessions(p_inactivity_minutes INTEGER DEFAULT 30)
RETURNS TABLE(session_id UUID, customer_email VARCHAR, synced_blocks INTEGER, updated_blocks INTEGER)
LANGUAGE plpgsql
AS $function$
DECLARE
    v_session RECORD;
    v_sync_result RECORD;
BEGIN
    -- Find sessions that need auto-sync:
    -- 1. Inactive for >= p_inactivity_minutes
    -- 2. Have customer_email
    -- 3. Have high-priority blocks not yet synced
    FOR v_session IN
        SELECT DISTINCT cs.id, cs.session_id, cs.customer_email
        FROM test.conversation_sessions cs
        WHERE cs.customer_email IS NOT NULL
          AND cs.last_activity_at < CURRENT_TIMESTAMP - (p_inactivity_minutes || ' minutes')::INTERVAL
          AND EXISTS (
              -- Has high-priority blocks
              SELECT 1
              FROM test.agent_memory_blocks amb
              WHERE amb.session_id = cs.id
                AND amb.priority >= 7
                AND amb.agent_scope = 'shared'
                AND (amb.expires_at IS NULL OR amb.expires_at > CURRENT_TIMESTAMP)
          )
        LIMIT 100  -- Process max 100 sessions per call
    LOOP
        -- Sync this session
        BEGIN
            SELECT * INTO v_sync_result
            FROM test.sync_session_to_user_memory(v_session.id);

            -- Only return sessions that actually synced blocks
            IF v_sync_result.synced_blocks > 0 OR v_sync_result.updated_blocks > 0 THEN
                session_id := v_session.session_id;
                customer_email := v_session.customer_email;
                synced_blocks := v_sync_result.synced_blocks;
                updated_blocks := v_sync_result.updated_blocks;
                RETURN NEXT;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            -- Log error but continue with other sessions
            RAISE WARNING 'Failed to sync session %: %', v_session.session_id, SQLERRM;
        END;
    END LOOP;

    RETURN;
END;
$function$;

-- ============================================================================
-- 3. TRIGGER: AUTO-SYNC ON ACTIVITY RESUME
-- ============================================================================
-- Automatically syncs session memory when a user returns after >30 min absence
-- Attached to conversation_sessions.last_activity_at updates

CREATE OR REPLACE FUNCTION test.trigger_auto_sync_on_activity_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    v_inactivity_minutes INTEGER;
    v_sync_result RECORD;
BEGIN
    -- Only process if:
    -- 1. Session has customer_email
    -- 2. last_activity_at was updated
    -- 3. Previous activity was >30 minutes ago

    IF NEW.customer_email IS NOT NULL
       AND OLD.last_activity_at IS NOT NULL
       AND OLD.last_activity_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
       AND NEW.last_activity_at > OLD.last_activity_at THEN

        -- This session was inactive for >30 min and just became active again
        -- Sync any pending high-priority blocks from previous activity
        BEGIN
            SELECT * INTO v_sync_result
            FROM test.sync_session_to_user_memory(OLD.id);

            IF v_sync_result.synced_blocks > 0 OR v_sync_result.updated_blocks > 0 THEN
                RAISE NOTICE 'Auto-synced session % on activity resume: % new, % updated',
                    OLD.session_id,
                    v_sync_result.synced_blocks,
                    v_sync_result.updated_blocks;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            -- Don't fail the update if sync fails
            RAISE WARNING 'Auto-sync failed for session %: %', OLD.session_id, SQLERRM;
        END;
    END IF;

    RETURN NEW;
END;
$function$;

-- Attach trigger to conversation_sessions
DROP TRIGGER IF EXISTS trg_auto_sync_on_activity_update ON test.conversation_sessions;
CREATE TRIGGER trg_auto_sync_on_activity_update
    BEFORE UPDATE OF last_activity_at ON test.conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION test.trigger_auto_sync_on_activity_update();

-- ============================================================================
-- 4. UPDATE USER PROFILE ON SESSION
-- ============================================================================
-- Creates/updates user profile when a new session is created
-- Tracks first_seen, last_seen, total_sessions, preferred_agent

CREATE OR REPLACE FUNCTION test.update_user_profile_on_session()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    v_customer_email VARCHAR(255);
    v_current_agent VARCHAR(50);
BEGIN
    v_customer_email := NEW.customer_email;
    v_current_agent := NEW.current_agent;

    -- Only process if customer_email exists
    IF v_customer_email IS NOT NULL THEN
        -- Upsert user profile
        INSERT INTO test.user_memory_profiles (
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
            total_sessions = test.user_memory_profiles.total_sessions + 1,
            updated_at = CURRENT_TIMESTAMP;

        -- Update preferred_agent if specified
        IF v_current_agent IS NOT NULL THEN
            UPDATE test.user_memory_profiles
            SET preferred_agent = v_current_agent
            WHERE customer_email = v_customer_email
            AND (preferred_agent IS NULL OR preferred_agent != v_current_agent);
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

-- Attach trigger to conversation_sessions
DROP TRIGGER IF EXISTS trg_update_user_profile_on_session ON test.conversation_sessions;
CREATE TRIGGER trg_update_user_profile_on_session
    AFTER INSERT ON test.conversation_sessions
    FOR EACH ROW
    EXECUTE FUNCTION test.update_user_profile_on_session();

-- ============================================================================
-- 5. GET SESSION STATISTICS
-- ============================================================================
-- Returns comprehensive statistics for a session
-- Used for analytics, debugging, and session management

CREATE OR REPLACE FUNCTION test.get_session_statistics(p_session_id UUID)
RETURNS TABLE(
    total_messages INTEGER,
    user_messages INTEGER,
    model_messages INTEGER,
    memory_blocks INTEGER,
    context_transfers INTEGER,
    session_duration_minutes INTEGER
)
LANGUAGE plpgsql
STABLE
AS $function$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_messages,
        COUNT(*) FILTER (WHERE role = 'user')::INTEGER AS user_messages,
        COUNT(*) FILTER (WHERE role = 'model')::INTEGER AS model_messages,
        (SELECT COUNT(*)::INTEGER FROM test.agent_memory_blocks WHERE session_id = p_session_id) AS memory_blocks,
        (SELECT COUNT(*)::INTEGER FROM test.agent_context_transfers WHERE session_id = p_session_id) AS context_transfers,
        EXTRACT(EPOCH FROM (s.last_activity_at - s.started_at))::INTEGER / 60 AS session_duration_minutes
    FROM test.conversation_messages m
    JOIN test.conversation_sessions s ON s.id = p_session_id
    WHERE m.session_id = p_session_id
    GROUP BY s.last_activity_at, s.started_at;
END;
$function$;

-- ============================================================================
-- 6. GET SIMILARITY THRESHOLD
-- ============================================================================
-- Returns the similarity threshold for fuzzy matching
-- Centralized configuration point

CREATE OR REPLACE FUNCTION test.get_similarity_threshold()
RETURNS REAL
LANGUAGE plpgsql
IMMUTABLE
AS $function$
    BEGIN
        RETURN 0.3; -- 30% similarity threshold (configurable)
    END;
$function$;

-- ============================================================================
-- 7. CLEANUP EXPIRED PAGINATION CONTEXTS
-- ============================================================================
-- Removes expired pagination contexts (TTL-based cleanup)
-- Should be called periodically (e.g., daily cron job)

CREATE OR REPLACE FUNCTION test.cleanup_expired_pagination_contexts()
RETURNS INTEGER
LANGUAGE plpgsql
AS $function$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM test.pagination_contexts
    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$function$;

-- ============================================================================
-- 8. UPDATE PAGINATION TIMESTAMP
-- ============================================================================
-- Trigger function to auto-update updated_at on pagination_contexts

CREATE OR REPLACE FUNCTION test.update_pagination_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$;

-- Attach trigger to pagination_contexts
DROP TRIGGER IF EXISTS trg_update_pagination_timestamp ON test.pagination_contexts;
CREATE TRIGGER trg_update_pagination_timestamp
    BEFORE UPDATE ON test.pagination_contexts
    FOR EACH ROW
    EXECUTE FUNCTION test.update_pagination_timestamp();

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION test.sync_session_to_user_memory(UUID) TO mcp_user;
GRANT EXECUTE ON FUNCTION test.auto_sync_inactive_sessions(INTEGER) TO mcp_user;
GRANT EXECUTE ON FUNCTION test.trigger_auto_sync_on_activity_update() TO mcp_user;
GRANT EXECUTE ON FUNCTION test.update_user_profile_on_session() TO mcp_user;
GRANT EXECUTE ON FUNCTION test.get_session_statistics(UUID) TO mcp_user;
GRANT EXECUTE ON FUNCTION test.get_similarity_threshold() TO mcp_user;
GRANT EXECUTE ON FUNCTION test.cleanup_expired_pagination_contexts() TO mcp_user;
GRANT EXECUTE ON FUNCTION test.update_pagination_timestamp() TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Memory sync functions created:';
    RAISE NOTICE '   - sync_session_to_user_memory(): Copy session blocks to user memory';
    RAISE NOTICE '   - auto_sync_inactive_sessions(): Batch sync inactive sessions';
    RAISE NOTICE '   - trigger_auto_sync_on_activity_update(): Auto-sync on session resume';
    RAISE NOTICE '   - update_user_profile_on_session(): Track user sessions';
    RAISE NOTICE '   - get_session_statistics(): Session analytics';
    RAISE NOTICE '   - get_similarity_threshold(): Fuzzy match config';
    RAISE NOTICE '   - cleanup_expired_pagination_contexts(): TTL cleanup';
    RAISE NOTICE '   - update_pagination_timestamp(): Auto-update timestamps';
END $$;
