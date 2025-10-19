-- ============================================================================
-- BUSINESS_HOURS TABLE - Operating hours configuration
-- ============================================================================
-- Configuración de horarios de atención generales por día de semana

CREATE TABLE IF NOT EXISTS test.business_hours (
    id SERIAL PRIMARY KEY,
    day_of_week INTEGER NOT NULL,  -- 0=Monday, 1=Tuesday, ..., 6=Sunday
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_day_of_week CHECK (day_of_week >= 0 AND day_of_week <= 6),
    CONSTRAINT chk_time_order CHECK (open_time < close_time),
    CONSTRAINT uq_day_of_week UNIQUE (day_of_week)
);

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON test.business_hours TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE test.business_hours_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Business hours table created';
    RAISE NOTICE '   - Operating hours by day of week';
    RAISE NOTICE '   - Fallback schedule for all services';
END $$;
