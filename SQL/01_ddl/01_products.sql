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
-- INDEXES - Optimized for search operations
-- ============================================================================

-- SKU lookup (exact match)
CREATE INDEX IF NOT EXISTS idx_products_sku
    ON test.products(sku);

-- Full-text search
CREATE INDEX IF NOT EXISTS idx_products_search
    ON test.products USING gin(to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')));

-- Tags search
CREATE INDEX IF NOT EXISTS idx_products_tags
    ON test.products USING gin(tags);

-- Trigram indexes for fuzzy matching (normalized)
CREATE INDEX IF NOT EXISTS idx_products_name_normalized_trgm
    ON test.products USING gin(test.normalize_text(name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_name_trgm_compat
    ON test.products USING gin(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_name_word_trgm
    ON test.products USING gist(name gist_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_desc_normalized_trgm
    ON test.products USING gin(test.normalize_text(description) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_desc_trgm_compat
    ON test.products USING gin(description gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_products_desc_word_trgm
    ON test.products USING gist(description gist_trgm_ops);

-- Brand + Category combined search
CREATE INDEX IF NOT EXISTS idx_products_brand_cat_normalized_trgm
    ON test.products USING gin(test.normalize_text(brand || ' ' || category) gin_trgm_ops);

-- Vector similarity (cosine distance)
CREATE INDEX IF NOT EXISTS idx_products_embedding_ivf
    ON test.products USING ivfflat(embedding) WITH (lists = 100);

-- ============================================================================
-- PERMISSIONS
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
