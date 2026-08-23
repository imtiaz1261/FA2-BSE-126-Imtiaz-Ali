-- PostgreSQL initialization script for pgvector extension

-- Create pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for common searches
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- Create indexes for ForeignKeys if they don't exist
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);

-- Optimize for vector search if document embeddings table exists
-- This will be created by Alembic, so just ensure it has proper indexes
-- ALTER TABLE document_embeddings ADD CONSTRAINT document_embeddings_pkey PRIMARY KEY (id);
-- CREATE INDEX IF NOT EXISTS idx_document_embeddings_user_id ON document_embeddings(user_id);
-- CREATE INDEX IF NOT EXISTS idx_document_embeddings_embedding ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Set reasonable defaults for connection pooling
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Create schema version table for migrations tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version BIGINT PRIMARY KEY,
    installed_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE schema_migrations IS 'Tracks Alembic migrations';

-- Log initialization
SELECT 'PostgreSQL initialized with pgvector extension'::text as status;
