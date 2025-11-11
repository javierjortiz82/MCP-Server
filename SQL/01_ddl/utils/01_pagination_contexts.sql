-- ============================================================================
-- PAGINATION_CONTEXTS TABLE - Persistent pagination state
-- ============================================================================
-- Stores pagination cursors and context for resumable queries

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.pagination_contexts (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Context identification
    context_name VARCHAR(255) NOT NULL UNIQUE,  -- e.g., 'products_search_john', 'bookings_2024'
    context_type VARCHAR(50) NOT NULL,  -- e.g., 'product_search', 'booking_list', 'memory_blocks'

    -- Pagination state
    last_offset INTEGER DEFAULT 0,
    last_limit INTEGER DEFAULT 50,
    total_records INTEGER,

    -- Cursor state for efficient pagination
    cursor_position TEXT,  -- Encoded cursor for resuming
    has_more BOOLEAN DEFAULT TRUE,

    -- Query context (store original search parameters)
    query_params JSONB DEFAULT '{}'::JSONB,

    -- User/session reference
    customer_email VARCHAR(255),
    session_id UUID,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,  -- Auto cleanup after N days

    -- Constraints
    CONSTRAINT chk_context_type CHECK (
        context_type IN ('product_search', 'booking_list', 'memory_blocks', 'email_history', 'custom')
    )
);

-- Indexes for pagination_contexts
CREATE INDEX IF NOT EXISTS idx_pagination_contexts_name
    ON :SCHEMA_NAME.pagination_contexts(context_name);

CREATE INDEX IF NOT EXISTS idx_pagination_contexts_session
    ON :SCHEMA_NAME.pagination_contexts(session_id)
    WHERE session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pagination_contexts_customer
    ON :SCHEMA_NAME.pagination_contexts(customer_email)
    WHERE customer_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pagination_contexts_expires
    ON :SCHEMA_NAME.pagination_contexts(expires_at)
    WHERE expires_at IS NOT NULL;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.pagination_contexts TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.pagination_contexts_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Pagination contexts table created:';
    RAISE NOTICE '   - Persistent pagination state management';
    RAISE NOTICE '   - Cursor-based pagination support';
    RAISE NOTICE '   - Query parameter caching';
END $$;
