# RAG Application with Advanced Search and Re-ranking

A production-ready Retrieval-Augmented Generation (RAG) application optimized for French content with hybrid search and cross-encoder re-ranking capabilities.

## Features

### Core Capabilities
- **Advanced PDF Processing**: PyMuPDF extraction with PyPDF2 fallback
- **Hybrid Search**: 60% keyword matching + 40% semantic search for better French language support
- **Cross-Encoder Re-ranking**: Multilingual re-ranking model for improved relevance
- **Vector Storage**: Supabase pgvector with cosine similarity search
- **AI Generation**: GPT-4o-mini for context-aware answer generation
- **Streamlit UI**: Interactive chat interface with source attribution

### Advanced Features
- **Incremental Indexing**: MD5 hash-based change detection to avoid re-processing
- **Streaming Progress**: Real-time feedback during PDF processing and embedding
- **OCR Support**: Scripts for handling scanned PDFs (see INSTALL_OCR.md)
- **Debug Mode**: Comprehensive logging with configurable log levels
- **Batch Processing**: Efficient embedding generation and database insertion

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Supabase account and project

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/nmarchand73/RAG_2025.git
cd RAG_2025
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
PDF_DIRECTORY=./pdfs
```

### 3. Setup Supabase

1. Go to your [Supabase Dashboard](https://supabase.com) → SQL Editor
2. Copy and run the contents of `supabase_setup.sql`
3. This creates the `documents` table, pgvector extension, and search functions

### 4. Run the Application

```bash
streamlit run app.py
```

Place PDFs in the `pdfs/` directory and start asking questions!

## Architecture

### RAG Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   PDF       │────▶│  Chunking    │────▶│  Embedding  │
│   Files     │     │  (1000 chars)│     │  (OpenAI)   │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  Supabase   │
                                         │  pgvector   │
                                         └─────────────┘
                                                │
                    ┌───────────────────────────┘
                    │
                    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│  Hybrid      │────▶│  Cross-     │
│   Query     │     │  Search      │     │  Encoder    │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  GPT-4o-    │
                                         │  mini       │
                                         └─────────────┘
```

### Key Components

**RAGEngine** ([rag_engine.py](rag_engine.py))
- Orchestrates the entire RAG pipeline
- Implements incremental indexing with file hash tracking
- Integrates hybrid search and re-ranking

**VectorStore** ([vector_store.py](vector_store.py))
- Manages OpenAI embeddings API
- Handles Supabase vector operations with RPC fallback
- Batch insertion (50 docs at a time) for efficiency

**PDFProcessor** ([pdf_processor.py](pdf_processor.py))
- Dual extraction: PyMuPDF (primary) + PyPDF2 (fallback)
- RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
- Detects scanned PDFs and suggests OCR

**Hybrid Search** ([hybrid_search.py](hybrid_search.py))
- Combines semantic embeddings with keyword matching
- Optimized for French content (60% keywords, 40% semantic)
- Stopword filtering and fuzzy matching support

**Re-Ranker** ([reranker.py](reranker.py))
- Cross-encoder model: `mmarco-mMiniLMv2-L12-H384-v1`
- Multilingual support (especially French)
- Two-stage retrieval for better precision

## Project Structure

```
RAG_2025/
├── app.py                  # Streamlit UI with progress tracking
├── rag_engine.py           # RAG orchestration and query processing
├── vector_store.py         # Supabase + OpenAI embeddings interface
├── pdf_processor.py        # PDF extraction and chunking
├── hybrid_search.py        # Keyword + semantic search fusion
├── reranker.py             # Cross-encoder re-ranking
├── ocr_simple.py           # OCR script for scanned PDFs
├── supabase_setup.sql      # Database schema and functions
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── CLAUDE.md               # Development guidelines
├── INSTALL_OCR.md          # OCR setup instructions
└── README.md               # This file
```

## Usage

### Basic Usage

1. **Index PDFs**: Place files in `pdfs/` directory
2. **Auto-indexing**: App automatically detects and indexes new/modified files
3. **Ask Questions**: Use the chat interface to query your documents
4. **View Sources**: Expand source documents to see relevant chunks

### Advanced Usage

**Force Re-indexing**
```python
# In app.py, enable force reindex
files, chunks = rag_engine.index_documents(force_reindex=True)
```

**Adjust Search Parameters**
```python
# In rag_engine.py query() method
relevant_docs = hybrid_search(
    self.vector_store,
    question,
    top_k=40,              # More candidates for re-ranking
    keyword_boost=0.7      # Increase keyword weight
)
```

**Debug Mode**
- Enable via sidebar in Streamlit UI
- Set log level to DEBUG or INFO
- Check `rag_app.log` for detailed traces

### OCR for Scanned PDFs

If PDFs contain scanned images without text:

```bash
# Install Tesseract OCR (see INSTALL_OCR.md)
python ocr_simple.py
```

This creates searchable PDFs in `pdfs_ocr/` directory.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and chat | Required |
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_KEY` | Supabase anon/public key | Required |
| `PDF_DIRECTORY` | Directory containing PDFs | `./pdfs` |

### Search Configuration

Edit [rag_engine.py](rag_engine.py):

```python
# Retrieval count
top_k=20  # Number of final documents to use for context

# Hybrid search weights
keyword_boost=0.6  # 0.0 = pure semantic, 1.0 = pure keyword

# Similarity threshold (in supabase_setup.sql)
match_threshold=0.01  # Lower = more results, higher = stricter
```

### Chunk Size

Edit [pdf_processor.py](pdf_processor.py):

```python
RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Characters per chunk
    chunk_overlap=200,    # Overlap for context continuity
)
```

**Note**: Changing chunk size requires re-indexing all documents.

## Troubleshooting

### Common Issues

**No Search Results**
- Lower `match_threshold` in `supabase_setup.sql`
- Increase `top_k` in query
- Check if embeddings exist: `SELECT COUNT(*) FROM documents WHERE embedding IS NOT NULL;`

**Poor French Relevance**
- Increase `keyword_boost` to favor exact matches
- Verify cross-encoder model is loading (check logs)
- Consider upgrading to `text-embedding-3-large`

**PDF Extraction Returns 0 Characters**
- Install PyMuPDF: `pip install pymupdf`
- If scanned PDF, use OCR: `python ocr_simple.py`
- Check logs for extraction errors

**Import Errors**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (needs 3.8+)

**API Rate Limits**
- OpenAI: Reduce batch size in `vector_store.py`
- Supabase: Add delays between RPC calls

### Logs and Debugging

Check `rag_app.log` for detailed execution traces:

```bash
tail -f rag_app.log  # Follow log in real-time
grep ERROR rag_app.log  # Find errors
grep "Re-ranking" rag_app.log  # Check re-ranker activity
```

## Performance Optimization

### For Large Document Collections (>1000 PDFs)

1. **Use RPC-based search** (requires `match_documents` SQL function)
2. **Increase batch size** in vector_store.py (currently 50)
3. **Enable IVFFlat index** in Supabase (see supabase_setup.sql)
4. **Consider caching** embeddings for repeated queries

### For Better French Search

1. ✅ Hybrid search with keyword boost (implemented)
2. ✅ Cross-encoder re-ranking (implemented)
3. 🔄 Upgrade to `text-embedding-3-large` (optional)
4. 🔄 Implement query expansion (future enhancement)

## Contributing

This is a personal project, but suggestions are welcome! Please check [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

MIT License - feel free to use and modify for your own projects.

## Acknowledgments

- Built with [Streamlit](https://streamlit.io)
- Powered by [OpenAI](https://openai.com) and [Supabase](https://supabase.com)
- Search optimization inspired by modern RAG research
- Developed with assistance from [Claude Code](https://claude.com/claude-code)
