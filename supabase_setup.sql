-- Supabase Vector Store Setup Script
-- Run this in your Supabase SQL Editor

-- 1. Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the documents table
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- 3. Create an index for faster similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create a function for similarity search
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.1,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id bigint,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE 1 - (documents.embedding <=> query_embedding) >= match_threshold
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 5. Verify the setup
SELECT
    'Extension enabled' as status,
    (SELECT count(*) FROM pg_extension WHERE extname = 'vector') as vector_enabled;

SELECT
    'Table created' as status,
    (SELECT count(*) FROM information_schema.tables WHERE table_name = 'documents') as table_exists;

SELECT
    'Function created' as status,
    (SELECT count(*) FROM pg_proc WHERE proname = 'match_documents') as function_exists;
