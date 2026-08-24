-- =============================================================
-- AIHub — PostgreSQL Initialisation Script
-- =============================================================
-- This script runs ONCE when the postgres container is first
-- created (via docker-entrypoint-initdb.d).
--
-- It enables the pgvector extension so we can store and query
-- embedding vectors directly in PostgreSQL — no separate
-- vector database needed in production.
-- =============================================================

-- Enable pgvector (provides the vector column type + operators)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for fast full-text search (used by admin queries)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Confirm extensions are active
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');
