-- ============================================================================
-- USERS AND PERMISSIONS - Access control setup
-- ============================================================================
-- Ejecutar tercero: Configura permisos para mcp_user

-- Grant all privileges on schema test to mcp_user
GRANT ALL PRIVILEGES ON SCHEMA test TO mcp_user;

-- Grant all privileges on database
GRANT ALL PRIVILEGES ON DATABASE mcpdb TO mcp_user;

-- Allow user to create objects
ALTER DEFAULT PRIVILEGES IN SCHEMA test GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mcp_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA test GRANT USAGE, SELECT ON SEQUENCES TO mcp_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA test GRANT EXECUTE ON FUNCTIONS TO mcp_user;

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✅ Permissions configured:';
    RAISE NOTICE '   User: mcp_user';
    RAISE NOTICE '   Schema privileges: ALL';
    RAISE NOTICE '   Database privileges: ALL';
END $$;
