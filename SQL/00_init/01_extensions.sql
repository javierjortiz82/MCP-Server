-- ============================================================================
-- EXTENSIONS - Required PostgreSQL extensions
-- ============================================================================
-- Ejecutar primero: Habilita extensiones necesarias para toda la BD

-- UUID functions for session tracking
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public;

-- Text search with accent support
CREATE EXTENSION IF NOT EXISTS "unaccent" SCHEMA public;

-- Trigram text search (fuzzy matching)
CREATE EXTENSION IF NOT EXISTS "pg_trgm" SCHEMA public;

-- Vector similarity search (AI embeddings)
CREATE EXTENSION IF NOT EXISTS "vector" SCHEMA public;

-- Cryptographic functions (digest, hmac, encrypt/decrypt, etc.)
-- NOTE: Currently installed but not actively used by application functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto" SCHEMA public;

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✅ Extensions installed:';
    RAISE NOTICE '   ✓ uuid-ossp (UUID generation)';
    RAISE NOTICE '   ✓ unaccent (Text search)';
    RAISE NOTICE '   ✓ pg_trgm (Fuzzy matching)';
    RAISE NOTICE '   ✓ vector (AI embeddings)';
    RAISE NOTICE '   ✓ pgcrypto (Cryptographic functions)';
END $$;
