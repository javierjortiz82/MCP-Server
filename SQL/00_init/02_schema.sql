-- ============================================================================
-- SCHEMA CREATION - Main application schema
-- ============================================================================
-- Ejecutar segundo: Crea el esquema principal y configura search_path

CREATE SCHEMA IF NOT EXISTS test;

-- Set default search path
ALTER DATABASE mcpdb SET search_path TO test, public;

-- Comment for documentation
COMMENT ON SCHEMA test IS 'Schema principal para aplicaciones MCP - Contiene todas las tablas de productos, bookings, email y memory';

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✅ Schema created:';
    RAISE NOTICE '   Schema name: test';
    RAISE NOTICE '   Search path configured: test, public';
END $$;
