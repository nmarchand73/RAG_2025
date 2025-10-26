import os
import logging
from typing import List, Dict, Tuple
from openai import OpenAI
from vector_store import VectorStore
from pdf_processor import PDFProcessor
from hybrid_search import hybrid_search
from reranker import ReRanker

# Configure logging
logger = logging.getLogger(__name__)


class RAGEngine:
    """Manages the RAG pipeline: indexing, retrieval, and generation."""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        openai_api_key: str,
        pdf_directory: str
    ):
        """
        Initialize the RAG engine.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/public key
            openai_api_key: OpenAI API key
            pdf_directory: Directory containing PDF files
        """
        logger.info("Initializing RAGEngine")
        logger.debug(f"PDF directory: {pdf_directory}")
        self.vector_store = VectorStore(supabase_url, supabase_key, openai_api_key)
        self.pdf_processor = PDFProcessor(pdf_directory)
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.chat_model = "gpt-4o-mini"
        self.reranker = ReRanker("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
        logger.info(f"RAGEngine initialized with chat model: {self.chat_model}")

    def index_documents(self, force_reindex: bool = False, progress_callback=None) -> Tuple[int, int]:
        """
        Index all PDFs in the directory.

        Args:
            force_reindex: If True, clear existing docs and reindex all
            progress_callback: Optional callback function(current, total, message)

        Returns:
            Tuple of (number of files processed, number of chunks indexed)
        """
        if force_reindex:
            print("Force reindex: clearing existing documents...")
            if progress_callback:
                progress_callback(0, 1, "Clearing existing documents...")
            self.vector_store.clear_all_documents()

        # Get all PDFs
        pdf_files = self.pdf_processor.get_pdf_files()

        if not pdf_files:
            print("No PDF files found to index")
            return 0, 0

        total_files = len(pdf_files)
        print(f"Found {total_files} PDF files to process")
        if progress_callback:
            progress_callback(0, total_files, f"Found {total_files} PDF files")

        # Process PDFs and check which ones need indexing
        documents_to_add = []
        files_processed = 0
        files_skipped = 0

        for file_idx, pdf_file in enumerate(pdf_files):
            file_name = os.path.basename(pdf_file)
            file_hash = self.pdf_processor.get_file_hash(pdf_file)

            # Skip if already indexed (unless force reindex)
            if not force_reindex and self.vector_store.check_file_exists(file_hash):
                print(f"Skipping {file_name} (already indexed)")
                files_skipped += 1
                if progress_callback:
                    progress_callback(file_idx + 1, total_files, f"Skipping {file_name} (already indexed)")
                continue

            # Process the PDF
            print(f"Processing {file_name}...")
            if progress_callback:
                progress_callback(file_idx + 1, total_files, f"Processing {file_name}...")

            chunks, metadata = self.pdf_processor.process_pdf(pdf_file)

            # Skip if no chunks extracted (scanned PDF without OCR)
            if len(chunks) == 0:
                logger.warning(f"Skipping {file_name} - no text extracted (scanned PDF)")
                print(f"⚠️  Skipped {file_name} - scanned PDF (0 chunks)")
                continue

            # Add chunks to the list
            for idx, chunk in enumerate(chunks):
                doc = {
                    "content": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": idx
                    }
                }
                documents_to_add.append(doc)

            files_processed += 1
            print(f"Extracted {len(chunks)} chunks from {file_name}")

        # Add documents to vector store
        if documents_to_add:
            if progress_callback:
                progress_callback(total_files, total_files, f"Indexing {len(documents_to_add)} chunks...")
            self.vector_store.add_documents(documents_to_add, progress_callback)
            print(f"Indexed {files_processed} files ({len(documents_to_add)} chunks)")
        else:
            print("No new documents to index")
            if progress_callback:
                progress_callback(total_files, total_files, f"All {total_files} files already indexed")

        return files_processed, len(documents_to_add)

    def query(
        self,
        question: str,
        top_k: int = 20,  # Augmenté à 20 pour améliorer les chances de trouver la bonne info
        include_sources: bool = True
    ) -> Dict:
        """
        Answer a question using RAG.

        Args:
            question: The question to answer
            top_k: Number of document chunks to retrieve
            include_sources: Whether to include source documents in response

        Returns:
            Dict with 'answer' and optionally 'sources'
        """
        # Retrieve relevant documents with hybrid search
        logger.info(f"Query received: {question[:100]}...")
        logger.info(f"Searching for relevant documents (top_k={top_k}) with hybrid search...")

        # Utilise la recherche hybride (sémantique + mots-clés)
        # Poids mots-clés augmenté pour mieux gérer le contenu français
        relevant_docs = hybrid_search(
            self.vector_store,
            question,
            top_k=top_k * 2,  # Récupère plus de candidats pour le re-ranking
            keyword_boost=0.6  # 60% poids mots-clés, 40% sémantique (inversé!)
        )

        if not relevant_docs:
            logger.warning("No relevant documents found for query")
            return {
                "answer": "I couldn't find any relevant information in the documents to answer your question.",
                "sources": []
            }

        logger.info(f"Retrieved {len(relevant_docs)} relevant documents")

        # Re-rank with cross-encoder for better French relevance
        if relevant_docs and self.reranker and self.reranker.model:
            logger.info("Applying cross-encoder re-ranking...")
            relevant_docs = self.reranker.rerank(question, relevant_docs, top_k=top_k)
            logger.info(f"Re-ranked to top {len(relevant_docs)} documents")

        # Prepare context from retrieved documents
        context = "\n\n".join([
            f"Document {i+1}:\n{doc['content']}"
            for i, doc in enumerate(relevant_docs)
        ])
        logger.debug(f"Context length: {len(context)} characters")

        # Generate answer using GPT-4o-mini
        logger.info(f"Generating answer with {self.chat_model}...")
        system_prompt = """Tu es un assistant intelligent qui répond aux questions en te basant UNIQUEMENT sur le contexte fourni.
Règles importantes:
- Réponds en français
- Utilise SEULEMENT les informations du contexte fourni
- Sois précis et structuré dans tes réponses
- Si l'information n'est pas dans le contexte, dis-le clairement
- Synthétise les informations de plusieurs passages si nécessaire"""

        user_prompt = f"""Contexte (extrait du document):
{context}

Question: {question}

Réponds à la question en te basant UNIQUEMENT sur le contexte ci-dessus. Si le contexte ne contient pas assez d'informations, dis-le."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            answer = response.choices[0].message.content
            logger.info("Answer generated successfully")
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            raise

        # Prepare sources
        sources = []
        if include_sources:
            for doc in relevant_docs:
                source = {
                    "file_name": doc.get('metadata', {}).get('file_name', 'Unknown'),
                    "chunk_index": doc.get('metadata', {}).get('chunk_index', 0),
                    "content": doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
                }
                sources.append(source)

        return {
            "answer": answer,
            "sources": sources
        }

    def get_stats(self) -> Dict:
        """
        Get statistics about the indexed documents.

        Returns:
            Dict with statistics
        """
        pdf_count = len(self.pdf_processor.get_pdf_files())
        chunk_count = self.vector_store.get_document_count()

        return {
            "pdf_files": pdf_count,
            "total_chunks": chunk_count
        }


if __name__ == "__main__":
    # Test the RAG engine
    from dotenv import load_dotenv
    load_dotenv()

    engine = RAGEngine(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        pdf_directory=os.getenv("PDF_DIRECTORY", "./pdfs")
    )

    # Index documents
    print("\n=== Indexing Documents ===")
    files, chunks = engine.index_documents()
    print(f"Indexed {files} files, {chunks} chunks")

    # Get stats
    print("\n=== Stats ===")
    stats = engine.get_stats()
    print(stats)

    # Test query
    if chunks > 0:
        print("\n=== Test Query ===")
        result = engine.query("What is this document about?")
        print(f"Answer: {result['answer']}")
        print(f"\nSources: {len(result['sources'])} documents")
