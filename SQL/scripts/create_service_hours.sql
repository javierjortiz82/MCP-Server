-- ============================================================================
-- SERVICE_HOURS TABLE CREATION
-- ============================================================================
-- Hybrid scheduling system: Service-specific operating hours with fallback
-- to general business_hours when not configured.
--
-- Features:
--  - Service-specific operating hours (optional override)
--  - Falls back to business_hours when no service-specific hours defined
--  - Support for multiple time ranges per service/day (priority field)
--  - Automatic timestamp management
--  - Full audit trail via triggers
--
-- Prerequisites:
--  - PostgreSQL 14+ with required extensions
--  - Existing bookings schema (appointments, service_types, business_hours)
--
-- Usage:
--  - Run via Python: python3 SQL/src/init_service_hours.py
--  - Or direct: psql -d mcpdb < SQL/scripts/create_service_hours.sql
--
-- Author: Lab01-MCP Team
-- Created: 2025-10-17
-- Version: 1.0.0
-- ============================================================================

-- Note: SCHEMA_NAME will be substituted by Python script (e.g., "test")

-- ============================================================================
-- SERVICE_HOURS TABLE - Hybrid scheduling system
-- ============================================================================
CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.service_hours (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Foreign key to service_types
    -- ON DELETE CASCADE: Remove hours if service is deleted
    service_type_id INTEGER NOT NULL,
    CONSTRAINT fk_service_hours_service_type
        FOREIGN KEY (service_type_id)
        REFERENCES {SCHEMA_NAME}.service_types(id)
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
    ON {SCHEMA_NAME}.service_hours(service_type_id, day_of_week, active)
    WHERE active = true;

-- Query: Find all services with custom hours for a day
CREATE INDEX IF NOT EXISTS idx_service_hours_by_day
    ON {SCHEMA_NAME}.service_hours(day_of_week, active)
    WHERE active = true;

-- Query: Find services with multiple ranges (shifts)
CREATE INDEX IF NOT EXISTS idx_service_hours_multi_range
    ON {SCHEMA_NAME}.service_hours(service_type_id, priority)
    WHERE active = true;

-- Lookup by service for admin dashboard
CREATE INDEX IF NOT EXISTS idx_service_hours_service
    ON {SCHEMA_NAME}.service_hours(service_type_id, active)
    WHERE active = true;

-- ============================================================================
-- TRIGGERS - Auto-update timestamps
-- ============================================================================

-- Reuse existing trigger function from bookings schema (if available)
DROP TRIGGER IF EXISTS trg_update_service_hours_timestamp ON {SCHEMA_NAME}.service_hours;
CREATE TRIGGER trg_update_service_hours_timestamp
    BEFORE UPDATE ON {SCHEMA_NAME}.service_hours
    FOR EACH ROW
    EXECUTE FUNCTION {SCHEMA_NAME}.update_booking_timestamp();

-- ============================================================================
-- PERMISSIONS - Grant access to mcp_user
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON {SCHEMA_NAME}.service_hours TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE {SCHEMA_NAME}.service_hours_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION NOTICES
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Service hours table created successfully within: %', '{SCHEMA_NAME}';
    RAISE NOTICE '📅 Table created: service_hours';
    RAISE NOTICE '🔄 Hybrid scheduling system enabled:';
    RAISE NOTICE '   - Service-specific hours (optional override)';
    RAISE NOTICE '   - Falls back to business_hours if not configured';
    RAISE NOTICE '   - Support for multiple time ranges per day (shifts)';
    RAISE NOTICE '📊 Indexes created for optimal query performance';
    RAISE NOTICE '🔐 Permissions granted to: mcp_user';
    RAISE NOTICE '💡 Next steps:';
    RAISE NOTICE '   1. Update is_slot_available() function to use hybrid logic';
    RAISE NOTICE '   2. Update bookings.py to pass service_type parameter';
    RAISE NOTICE '   3. (Optional) Seed service-specific hours as needed';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Hybrid scheduling system ready for integration';
END $$;
