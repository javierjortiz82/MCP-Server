-- ============================================================================
-- SCHEMA CREATION - Main application schema
-- ============================================================================
-- Schema name from environment variable: SCHEMA_NAME (default: test)

CREATE SCHEMA IF NOT EXISTS :SCHEMA_NAME;

-- Set default search path
ALTER DATABASE mcpdb SET search_path TO :SCHEMA_NAME, public;

-- Comment for documentation
COMMENT ON SCHEMA :SCHEMA_NAME IS 'Main schema for MCP applications - Contains all tables for products, bookings, email, and memory systems';

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✅ Schema created:';
    RAISE NOTICE '   Schema name: %', :'SCHEMA_NAME';
    RAISE NOTICE '   Search path configured: %, public', :'SCHEMA_NAME';
END $$;
