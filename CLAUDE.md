# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG (Retrieval-Augmented Generation) application that enables semantic search and question-answering over PDF documents. The system uses OpenAI embeddings, Supabase pgvector for storage, and GPT-4o-mini for answer generation.

## Development Commands

### Running the Application
```bash
streamlit run app.py
```

### Testing Individual Components
Each module has a `__main__` block for standalone testing:

```bash
# Test PDF processor
python pdf_processor.py

# Test vector store operations
python vector_store.py

# Test RAG engine end-to-end
python rag_engine.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture & Data Flow

### RAG Pipeline Architecture

The application follows a classic RAG pattern with three distinct phases:

1. **Indexing Phase** (PDF → Chunks → Embeddings → Vector DB)
   - `PDFProcessor` extracts and chunks PDFs using RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
   - `VectorStore` creates embeddings via OpenAI's text-embedding-3-small (1536 dimensions)
   - Documents stored in Supabase with metadata (file_hash for change detection)

2. **Retrieval Phase** (Query → Embedding → Similarity Search)
   - User query embedded using same model as documents
   - Supabase RPC `match_documents()` performs cosine similarity search
   - Fallback mechanism: Python-based similarity if RPC unavailable (less efficient)

3. **Generation Phase** (Context + Query → LLM → Answer)
   - Top-k relevant chunks assembled as context
   - GPT-4o-mini generates grounded answer (temperature=0.7, max_tokens=500)
   - Source attribution included in response

### Component Responsibilities

**RAGEngine** (rag_engine.py) - Orchestration layer
- Coordinates between PDFProcessor and VectorStore
- Implements incremental indexing (file hash comparison)
- Handles force re-indexing via `index_documents(force_reindex=True)`

**VectorStore** (vector_store.py) - Database abstraction
- Wraps Supabase client and OpenAI embeddings API
- Batch insertion (50 documents at a time to avoid timeouts)
- Dual search strategy: RPC-based (optimal) with Python fallback

**PDFProcessor** (pdf_processor.py) - Document processing
- MD5 hashing for duplicate detection
- Chunking preserves semantic boundaries via RecursiveCharacterTextSplitter
- Metadata tracking: file_name, file_path, file_hash, chunk_index

**app.py** - Streamlit UI layer
- Session state management for RAGEngine instance and chat history
- Auto-indexing on first load (checks for new/modified files)
- Source document expansion in chat interface

## Critical Implementation Details

### Incremental Indexing
The system uses MD5 file hashes stored in document metadata to detect changes. `RAGEngine.index_documents()` queries Supabase for existing file_hash values to skip already-indexed files unless `force_reindex=True`.

### Vector Search Strategy
`VectorStore.similarity_search()` attempts to call Supabase RPC function `match_documents()` first (defined in supabase_setup.sql). If this fails, it falls back to fetching all documents and computing cosine similarity in Python - this fallback is NOT scalable beyond ~100 documents.

### Streamlit Session State
- `rag_engine`: Initialized once per session with credentials from .env
- `messages`: Chat history (list of dicts with role/content/sources)
- `indexed`: Boolean flag to trigger auto-indexing only on first load

## Environment Configuration

Required variables in `.env`:
- `OPENAI_API_KEY` - Used for both embeddings and chat completion
- `SUPABASE_URL` - Project URL from Supabase dashboard
- `SUPABASE_KEY` - Anon/public key (not service role key)
- `PDF_DIRECTORY` - Path to PDF folder (default: ./pdfs)

## Supabase Schema

The `documents` table structure (see supabase_setup.sql):
```sql
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

The `match_documents` RPC function expects:
- `query_embedding`: vector(1536)
- `match_threshold`: float (default 0.5)
- `match_count`: int (default 5)

## Common Modification Scenarios

### Changing Chunk Size
Modify `PDFProcessor.__init__()` chunk_size and chunk_overlap parameters. Note: requires re-indexing existing documents.

### Switching LLM Models
Update `RAGEngine.__init__()` self.chat_model. Ensure the new model supports the API format used.

### Adjusting Embedding Model
Change `VectorStore.__init__()` self.embedding_model and self.embedding_dimension. CRITICAL: Must update Supabase vector column dimension and re-index all documents.

### Modifying Retrieval Count
Pass `top_k` parameter to `RAGEngine.query()`. Higher values provide more context but increase token usage.
