-- ============================================================================
-- EXTENSIONS - Required PostgreSQL extensions
-- ============================================================================
-- Ejecutar primero: Habilita extensiones necesarias para toda la BD

-- UUID functions for session tracking
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Text search with accent support
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Trigram text search (fuzzy matching)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Vector similarity search (AI embeddings)
CREATE EXTENSION IF NOT EXISTS "vector";

-- Cryptographic functions (digest, hmac, encrypt/decrypt, etc.)
-- NOTE: Currently installed but not actively used by application functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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
