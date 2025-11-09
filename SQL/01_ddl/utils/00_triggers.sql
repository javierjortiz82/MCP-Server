-- ============================================================================
-- Common Trigger Functions
-- ============================================================================
-- Purpose: Reusable trigger functions for common database operations
-- Created: 2025-11-09
-- Author: Odiseo AI Team
-- ============================================================================

-- ============================================================================
-- Auto-update updated_at timestamp
-- ============================================================================
-- Usage: Apply this trigger to any table with an updated_at column
-- Example:
--   CREATE TRIGGER update_my_table_updated_at
--       BEFORE UPDATE ON my_table
--       FOR EACH ROW
--       EXECUTE FUNCTION :SCHEMA_NAME.update_updated_at_column();
-- ============================================================================

CREATE OR REPLACE FUNCTION :SCHEMA_NAME.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION :SCHEMA_NAME.update_updated_at_column() IS 'Auto-update updated_at timestamp on row modification';
