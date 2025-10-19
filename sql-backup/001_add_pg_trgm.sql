-- Migration 001: Add pg_trgm extension and trigram indexes
-- Purpose: Enable fuzzy text search capabilities for product searches
-- Author: MCP System
-- Date: 2024

-- Enable pg_trgm extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create trigram indexes on searchable text fields
-- These indexes enable fast fuzzy matching with similarity scores

-- Index for product names - most commonly searched field
CREATE INDEX IF NOT EXISTS idx_products_name_trgm
ON test.products USING gin (name gin_trgm_ops);

-- Index for product descriptions - secondary search field
CREATE INDEX IF NOT EXISTS idx_products_desc_trgm
ON test.products USING gin (description gin_trgm_ops);

-- Combined index for brand + category searches
CREATE INDEX IF NOT EXISTS idx_products_brand_cat_trgm
ON test.products USING gin ((brand || ' ' || category) gin_trgm_ops);

-- Function to get similarity threshold (configurable)
CREATE OR REPLACE FUNCTION get_similarity_threshold()
RETURNS real AS $$
BEGIN
    RETURN 0.3; -- 30% similarity threshold
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Verify extension and indexes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        RAISE EXCEPTION 'pg_trgm extension not installed';
    END IF;

    RAISE NOTICE 'pg_trgm extension installed successfully';
    RAISE NOTICE 'Trigram indexes created for fuzzy text search';
END $$;