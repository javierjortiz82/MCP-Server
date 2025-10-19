-- Inicialización básica de la base de datos para MCP
-- Este script se ejecuta automáticamente al crear el contenedor

-- Crear extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "unaccent" SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "pg_trgm" SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "vector" SCHEMA public;

-- Crear esquema para MCP
CREATE SCHEMA IF NOT EXISTS test;

-- Dar permisos al usuario MCP
GRANT ALL PRIVILEGES ON SCHEMA test TO mcp_user;
GRANT ALL PRIVILEGES ON DATABASE mcpdb TO mcp_user;

-- Configurar búsqueda por defecto
ALTER DATABASE mcpdb SET search_path TO test, public;

-- Comentarios
COMMENT ON SCHEMA test IS 'Esquema principal para aplicaciones MCP';
COMMENT ON DATABASE mcpdb IS 'Base de datos para servidor MCP';