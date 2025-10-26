import os
import logging
from typing import List, Dict, Optional
from supabase import create_client, Client
from openai import OpenAI

# Get logger (don't reconfigure, use app's config)
logger = logging.getLogger(__name__)


class VectorStore:
    """Handles vector embeddings and storage in Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str, openai_api_key: str):
        """
        Initialize the vector store.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon/public key
            openai_api_key: OpenAI API key
        """
        logger.info("Initializing VectorStore")
        logger.debug(f"Supabase URL: {supabase_url}")
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimension = 1536
        logger.info(f"VectorStore initialized with model: {self.embedding_model}")

    def create_embedding(self, text: str) -> List[float]:
        """
        Create an embedding vector for the given text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        logger.debug(f"Creating embedding for text (length: {len(text)})")
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            logger.debug("Embedding created successfully")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise

    def add_documents(self, documents: List[Dict], progress_callback=None) -> bool:
        """
        Add documents to the vector store.

        Args:
            documents: List of dicts with 'content' and 'metadata' keys
            progress_callback: Optional callback function(current, total, message)

        Returns:
            True if successful
        """
        if not documents:
            print("No documents to add")
            return False

        total_docs = len(documents)
        print(f"Creating embeddings and inserting to database for {total_docs} documents...")
        if progress_callback:
            progress_callback(0, total_docs, f"Processing {total_docs} documents...")

        # Hybrid approach: Create embeddings and insert in mini-batches
        batch_size = 50  # Insert every 50 embeddings
        current_batch = []
        skipped = 0
        total_inserted = 0

        for idx, doc in enumerate(documents):
            # Skip empty content
            if not doc.get('content') or len(doc['content'].strip()) == 0:
                logger.warning(f"Skipping document {idx + 1} - empty content")
                skipped += 1
                continue

            # Progress update every 10 documents
            if idx % 10 == 0:
                msg = f"Processing {idx + 1}/{total_docs}..."
                print(msg)
                if progress_callback:
                    progress_callback(idx, total_docs, msg)

            # Create embedding
            embedding = self.create_embedding(doc['content'])

            record = {
                "content": doc['content'],
                "metadata": doc['metadata'],
                "embedding": embedding
            }
            current_batch.append(record)

            # Insert to Supabase when batch is full
            if len(current_batch) >= batch_size:
                try:
                    self.supabase.table("documents").insert(current_batch).execute()
                    total_inserted += len(current_batch)
                    batch_num = total_inserted // batch_size
                    msg = f"Saved batch {batch_num} to database ({total_inserted}/{total_docs} done)"
                    print(msg)
                    logger.info(msg)
                    if progress_callback:
                        progress_callback(idx + 1, total_docs, msg)
                    current_batch = []  # Clear batch
                except Exception as e:
                    logger.error(f"Error inserting batch: {str(e)}")
                    return False

        # Insert remaining documents
        if current_batch:
            try:
                self.supabase.table("documents").insert(current_batch).execute()
                total_inserted += len(current_batch)
                msg = f"Saved final batch to database ({total_inserted} total)"
                print(msg)
                logger.info(msg)
            except Exception as e:
                logger.error(f"Error inserting final batch: {str(e)}")
                return False

        if skipped > 0:
            logger.warning(f"Skipped {skipped} documents with empty content")

        print(f"✅ Successfully added {total_inserted} documents to vector store")
        logger.info(f"Added {total_inserted} documents to vector store")
        return True

    def similarity_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for similar documents using vector similarity.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of similar documents with content and metadata
        """
        logger.info(f"Similarity search for query (top_k={top_k})")
        logger.debug(f"Query: {query[:100]}...")

        # Create embedding for the query
        query_embedding = self.create_embedding(query)

        # Perform similarity search using Supabase RPC
        # Note: We'll use cosine similarity with pgvector
        try:
            logger.info("Attempting RPC-based similarity search")
            # Call the RPC function for similarity search
            # Very low threshold for maximum recall (0.01 = ~99% of documents)
            response = self.supabase.rpc(
                'match_documents',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': 0.01,  # Très bas pour plus de résultats
                    'match_count': top_k
                }
            ).execute()

            logger.info(f"RPC search returned {len(response.data)} results")

            # If RPC returns 0 results, log details for debugging
            if len(response.data) == 0:
                logger.warning("RPC returned 0 results - checking if documents exist in DB")
                doc_count = self.get_document_count()
                logger.warning(f"Total documents in DB: {doc_count}")
                if doc_count > 0:
                    logger.warning("Documents exist but similarity too low - trying fallback search")
                    raise Exception("No results from RPC, forcing fallback")

            return response.data

        except Exception as e:
            # Fallback: if RPC doesn't exist, we'll do a simple query
            # and calculate similarity in Python (less efficient)
            logger.warning(f"RPC search failed: {str(e)}")
            logger.info("Falling back to Python-based similarity search")

            # Get all documents (note: this is not scalable for large datasets)
            all_docs = self.supabase.table("documents").select("*").limit(100).execute()

            if not all_docs.data:
                logger.warning("No documents found in database")
                return []

            logger.info(f"Retrieved {len(all_docs.data)} documents for fallback search")

            # Calculate cosine similarity
            results = []
            for doc in all_docs.data:
                if doc.get('embedding'):
                    similarity = self._cosine_similarity(query_embedding, doc['embedding'])
                    results.append({
                        'id': doc['id'],
                        'content': doc['content'],
                        'metadata': doc['metadata'],
                        'similarity': similarity
                    })

            # Sort by similarity and return top_k
            results.sort(key=lambda x: x['similarity'], reverse=True)
            logger.info(f"Fallback search returning {len(results[:top_k])} results")
            return results[:top_k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        import json

        # Convertir en liste si c'est une string JSON
        if isinstance(vec1, str):
            vec1 = json.loads(vec1)
        if isinstance(vec2, str):
            vec2 = json.loads(vec2)

        # S'assurer que ce sont des listes de floats
        if not isinstance(vec1, list) or not isinstance(vec2, list):
            logger.error(f"Invalid vector types: vec1={type(vec1)}, vec2={type(vec2)}")
            return 0.0

        dot_product = sum(float(a) * float(b) for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(float(a) * float(a) for a in vec1))
        magnitude2 = math.sqrt(sum(float(b) * float(b) for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def clear_all_documents(self) -> bool:
        """
        Delete all documents from the vector store.

        Returns:
            True if successful
        """
        try:
            self.supabase.table("documents").delete().neq('id', 0).execute()
            print("All documents cleared from vector store")
            return True
        except Exception as e:
            print(f"Error clearing documents: {str(e)}")
            return False

    def get_document_count(self) -> int:
        """Get the total number of documents in the store."""
        try:
            response = self.supabase.table("documents").select("id", count="exact").execute()
            return response.count if response.count else 0
        except Exception as e:
            print(f"Error getting document count: {str(e)}")
            return 0

    def check_file_exists(self, file_hash: str) -> bool:
        """
        Check if a file with the given hash already exists in the database.

        Args:
            file_hash: MD5 hash of the file

        Returns:
            True if file exists
        """
        logger.debug(f"Checking if file exists with hash: {file_hash}")
        try:
            response = self.supabase.table("documents").select("id").eq(
                'metadata->>file_hash', file_hash
            ).limit(1).execute()

            exists = len(response.data) > 0
            logger.debug(f"File exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False


if __name__ == "__main__":
    # Test the vector store
    from dotenv import load_dotenv
    load_dotenv()

    store = VectorStore(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    print(f"Document count: {store.get_document_count()}")
