-- ============================================================================
-- SERVICE_TYPES TABLE - Catalog of available services
-- ============================================================================
-- Catálogo de servicios disponibles con metadatos para UI

CREATE TABLE IF NOT EXISTS :'SCHEMA_NAME'.service_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    price NUMERIC(10,2),
    active BOOLEAN DEFAULT true,
    color VARCHAR(7),  -- Hex color for UI (e.g., #FF5733)
    icon VARCHAR(50),  -- Icon identifier for UI

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_service_duration CHECK (duration_minutes > 0 AND duration_minutes <= 480),
    CONSTRAINT chk_service_price CHECK (price IS NULL OR price >= 0)
);

-- Index for active services lookup
CREATE INDEX IF NOT EXISTS idx_service_types_active
    ON :'SCHEMA_NAME'.service_types(active)
    WHERE active = true;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON :'SCHEMA_NAME'.service_types TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE :'SCHEMA_NAME'.service_types_id_seq TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Service types table created';
    RAISE NOTICE '   - Service catalog with metadata';
    RAISE NOTICE '   - Pricing and duration configuration';
    RAISE NOTICE '   - UI styling (color, icon)';
END $$;
