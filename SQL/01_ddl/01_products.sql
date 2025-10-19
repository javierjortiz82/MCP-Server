-- ============================================================================
-- PRODUCTS TABLE - Product catalog with vector embeddings
-- ============================================================================
-- Tabla base para catálogo de productos con soporte para búsqueda por embeddings
-- Incluye soporte para búsqueda fuzzy (trigram) y búsqueda semántica (vector)

-- Text normalization function (unaccent + lowercase)
CREATE OR REPLACE FUNCTION test.normalize_text(p_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(unaccent(p_text));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Main products table
CREATE TABLE IF NOT EXISTS test.products (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Product identification
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,

    -- Classification
    category TEXT,
    brand TEXT,
    tags TEXT[],

    -- Physical attributes
    color TEXT,
    size TEXT,

    -- Pricing
    price NUMERIC(12, 2),

    -- AI embeddings (for semantic search)
    embedding vector(1536),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION test.update_product_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_products_timestamp ON test.products;
CREATE TRIGGER trg_update_products_timestamp
    BEFORE UPDATE ON test.products
    FOR EACH ROW
    EXECUTE FUNCTION test.update_product_timestamp();

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
-- NOTE: All indexes for this table are consolidated in 03_indexes/01_indexes.sql
--       to maintain a single source of truth and avoid duplication
-- ============================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON test.products TO mcp_user;
GRANT USAGE, SELECT ON SEQUENCE test.products_id_seq TO mcp_user;
GRANT EXECUTE ON FUNCTION test.normalize_text(TEXT) TO mcp_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Products table created:';
    RAISE NOTICE '   - Main product catalog with metadata';
    RAISE NOTICE '   - Vector embeddings for AI search (1536-dim)';
    RAISE NOTICE '   - Trigram indexes for fuzzy matching';
    RAISE NOTICE '   - Full-text search support';
    RAISE NOTICE '   - Tag-based filtering';
END $$;
