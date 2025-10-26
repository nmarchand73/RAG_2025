# RAG Application with Supabase Vector DB and OpenAI

A Retrieval-Augmented Generation (RAG) application that allows you to search through PDF documents using Supabase vector database and OpenAI.

## Features

- PDF document processing and indexing
- Vector similarity search using Supabase pgvector
- AI-powered question answering with GPT-4o-mini
- Simple chat interface built with Streamlit
- Auto re-indexing of new/modified PDFs

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Supabase account and project

## Supabase Setup

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click "New Project"
3. Fill in your project details and wait for it to initialize

### 2. Run the Setup SQL Script

1. In your Supabase dashboard, go to "SQL Editor"
2. Open the `supabase_setup.sql` file from this project
3. Copy and paste the entire contents into the SQL Editor
4. Click "Run" to execute the script

This will:
- Enable the pgvector extension
- Create the documents table with vector column
- Create indexes for faster similarity search
- Create a similarity search function for optimal performance

**Alternative: Manual Setup**

You can also run the commands manually if preferred. See the `supabase_setup.sql` file for the individual SQL commands.

### 3. Get Your Credentials

1. Go to Project Settings > API
2. Copy your "Project URL" (SUPABASE_URL)
3. Copy your "anon/public" key (SUPABASE_KEY)

## Installation

1. Clone this repository or download the files

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file by copying `.env.example`:
```bash
cp .env.example .env
```

4. Edit `.env` and add your credentials:
```
OPENAI_API_KEY=your_actual_openai_key
SUPABASE_URL=your_actual_supabase_url
SUPABASE_KEY=your_actual_supabase_key
PDF_DIRECTORY=./pdfs
```

## Usage

1. Place your PDF files in the `pdfs/` directory

2. Run the Streamlit app:
```bash
streamlit run app.py
```

3. The app will:
   - Automatically check for new or modified PDFs
   - Index them into Supabase vector database
   - Allow you to chat and ask questions about your documents

4. Ask questions in the chat interface and get AI-powered answers based on your PDFs!

## Project Structure

```
RAG_2025/
├── pdfs/                # Place your PDF files here
├── app.py               # Streamlit chat interface
├── rag_engine.py        # RAG logic (retrieval + generation)
├── pdf_processor.py     # PDF extraction and chunking
├── vector_store.py      # Supabase vector operations
├── supabase_setup.sql   # Supabase database setup script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your environment variables (create from .env.example)
└── README.md            # This file
```

## How It Works

1. **PDF Processing**: PDFs are extracted and split into chunks
2. **Embedding**: Each chunk is converted to a vector embedding using OpenAI
3. **Storage**: Embeddings are stored in Supabase with pgvector
4. **Retrieval**: User questions are embedded and matched against stored vectors
5. **Generation**: Relevant chunks are sent to GPT-4o-mini to generate answers

## Troubleshooting

- **Import errors**: Make sure you've installed all requirements
- **API errors**: Verify your OpenAI API key is valid and has credits
- **Supabase errors**: Check that pgvector extension is enabled and table is created
- **No PDFs found**: Ensure PDFs are in the correct directory specified in .env
