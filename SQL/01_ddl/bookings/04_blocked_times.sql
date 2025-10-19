-- ============================================================================
-- BLOCKED_TIMES TABLE - Holidays, breaks, and unavailable slots
-- ============================================================================
-- Registro de tiempos no disponibles: vacaciones, descansos, etc

CREATE TABLE IF NOT EXISTS :SCHEMA_NAME.blocked_times (
    id SERIAL PRIMARY KEY,
    block_date DATE NOT NULL,
    start_time TIME,  -- NULL if full day block
    end_time TIME,    -- NULL if full day block
    reason VARCHAR(255),
    is_full_day BOOLEAN DEFAULT false,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_time_order CHECK (
        is_full_day = true OR
        (start_time IS NOT NULL AND end_time IS NOT NULL AND start_time < end_time)
    ),
    CONSTRAINT chk_time_consistency CHECK (
        (is_full_day = true AND start_time IS NULL AND end_time IS NULL) OR
        (is_full_day = false AND start_time IS NOT NULL AND end_time IS NOT NULL)
    )
);

-- Index for availability checks
CREATE INDEX IF NOT EXISTS idx_blocked_times_date
    ON :SCHEMA_NAME.blocked_times(block_date);

-- Composite index for time-specific blocks
CREATE INDEX IF NOT EXISTS idx_blocked_times_date_time
    ON :SCHEMA_NAME.blocked_times(block_date, start_time, end_time)
    WHERE is_full_day = false;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :SCHEMA_NAME.blocked_times TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :SCHEMA_NAME.blocked_times_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Blocked times table created';
    RAISE NOTICE '   - Holiday and break management';
    RAISE NOTICE '   - Full-day and time-slot blocking';
END $$;
