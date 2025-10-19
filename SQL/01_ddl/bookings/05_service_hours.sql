-- ============================================================================
-- SERVICE_HOURS TABLE - Hybrid scheduling system
-- ============================================================================
-- Horarios específicos por servicio (override opcional de business_hours)

CREATE TABLE IF NOT EXISTS :'SCHEMA_NAME'.service_hours (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Foreign key to service_types
    -- ON DELETE CASCADE: Remove hours if service is deleted
    service_type_id INTEGER NOT NULL,
    CONSTRAINT fk_service_hours_service_type
        FOREIGN KEY (service_type_id)
        REFERENCES :'SCHEMA_NAME'.service_types(id)
        ON DELETE CASCADE,

    -- Scheduling information
    day_of_week INTEGER NOT NULL,  -- 0=Monday, 1=Tuesday, ..., 6=Sunday
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,

    -- Priority for overlapping time ranges on same day
    -- Allows: Early shift (priority 1) + Late shift (priority 2) on same day
    priority INTEGER DEFAULT 0,

    -- Active flag for soft delete / temporary disable
    active BOOLEAN DEFAULT true,

    -- Metadata timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_day_of_week CHECK (day_of_week >= 0 AND day_of_week <= 6),
    CONSTRAINT chk_time_order CHECK (open_time < close_time),
    CONSTRAINT chk_priority CHECK (priority >= 0 AND priority <= 10),

    -- Unique constraint: One active schedule per service/day/priority
    CONSTRAINT uq_service_hours_schedule
        UNIQUE(service_type_id, day_of_week, priority)
);

-- ============================================================================
-- INDEXES - Optimized for scheduler queries
-- ============================================================================

-- Primary query: Get hours for specific service on specific day
CREATE INDEX IF NOT EXISTS idx_service_hours_lookup
    ON :'SCHEMA_NAME'.service_hours(service_type_id, day_of_week, active)
    WHERE active = true;

-- Query: Find all services with custom hours for a day
CREATE INDEX IF NOT EXISTS idx_service_hours_by_day
    ON :'SCHEMA_NAME'.service_hours(day_of_week, active)
    WHERE active = true;

-- Query: Find services with multiple ranges (shifts)
CREATE INDEX IF NOT EXISTS idx_service_hours_multi_range
    ON :'SCHEMA_NAME'.service_hours(service_type_id, priority)
    WHERE active = true;

-- Lookup by service for admin dashboard
CREATE INDEX IF NOT EXISTS idx_service_hours_service
    ON :'SCHEMA_NAME'.service_hours(service_type_id, active)
    WHERE active = true;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :'SCHEMA_NAME'.service_hours TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :'SCHEMA_NAME'.service_hours_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Service hours table created';
    RAISE NOTICE '   - Service-specific operating hours';
    RAISE NOTICE '   - Support for multiple shifts per day';
    RAISE NOTICE '   - Hybrid scheduling (with fallback to business_hours)';
END $$;
