import os
import hashlib
import logging
from typing import List, Dict, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configure logging
logger = logging.getLogger(__name__)

# Try to import PDF libraries with fallbacks
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.info("PyMuPDF available for PDF extraction")
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available, falling back to PyPDF2")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
    logger.info("PyPDF2 available for PDF extraction")
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.error("PyPDF2 not available")


class PDFProcessor:
    """Handles PDF extraction, chunking, and tracking for auto re-indexing."""

    def __init__(self, pdf_directory: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the PDF processor.

        Args:
            pdf_directory: Path to directory containing PDF files
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        logger.info(f"Initializing PDFProcessor with directory: {pdf_directory}")
        self.pdf_directory = pdf_directory
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        logger.info(f"PDFProcessor initialized (chunk_size={chunk_size}, overlap={chunk_overlap})")

    def get_pdf_files(self) -> List[str]:
        """Get all PDF files from the directory."""
        if not os.path.exists(self.pdf_directory):
            logger.info(f"PDF directory does not exist, creating: {self.pdf_directory}")
            os.makedirs(self.pdf_directory)
            return []

        pdf_files = []
        for file in os.listdir(self.pdf_directory):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(self.pdf_directory, file))

        logger.info(f"Found {len(pdf_files)} PDF files in {self.pdf_directory}")
        return pdf_files

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file to detect changes.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash of the file
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract all text from a PDF file using PyMuPDF (preferred) or PyPDF2 (fallback).

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content
        """
        logger.info(f"Extracting text from: {os.path.basename(file_path)}")

        # Try PyMuPDF first (better text extraction)
        if PYMUPDF_AVAILABLE:
            try:
                logger.debug("Using PyMuPDF for extraction")
                doc = fitz.open(file_path)
                text = ""
                page_count = len(doc)
                logger.debug(f"PDF has {page_count} pages")

                for i, page in enumerate(doc):
                    page_text = page.get_text()
                    text += page_text + "\n"
                    if (i + 1) % 10 == 0:
                        logger.debug(f"Processed {i + 1}/{page_count} pages")

                doc.close()
                text = text.strip()
                logger.info(f"Extracted {len(text)} characters from {page_count} pages (PyMuPDF)")

                if len(text) == 0:
                    logger.warning("PyMuPDF extracted 0 characters - PDF may be scanned/image-based")

                return text
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {str(e)}, trying PyPDF2")

        # Fallback to PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                logger.debug("Using PyPDF2 for extraction")
                reader = PdfReader(file_path)
                text = ""
                page_count = len(reader.pages)
                logger.debug(f"PDF has {page_count} pages")

                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    if (i + 1) % 10 == 0:
                        logger.debug(f"Processed {i + 1}/{page_count} pages")

                text = text.strip()
                logger.info(f"Extracted {len(text)} characters from {page_count} pages (PyPDF2)")

                if len(text) == 0:
                    logger.warning("PyPDF2 extracted 0 characters - PDF may be scanned/image-based")

                return text
            except Exception as e:
                logger.error(f"PyPDF2 extraction failed: {str(e)}")
                return ""

        logger.error("No PDF extraction library available")
        return ""

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks.

        Args:
            text: Text to split

        Returns:
            List of text chunks
        """
        if not text:
            logger.warning("Empty text provided for chunking")
            return []

        chunks = self.text_splitter.split_text(text)
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks

    def process_pdf(self, file_path: str) -> Tuple[List[str], Dict]:
        """
        Process a single PDF file: extract text and chunk it.

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (text chunks, metadata dict)
        """
        file_name = os.path.basename(file_path)
        file_hash = self.get_file_hash(file_path)

        text = self.extract_text_from_pdf(file_path)

        # Check if PDF is scanned (no extractable text)
        if len(text) == 0:
            logger.error(f"❌ {file_name} appears to be a scanned PDF (image-only)")
            logger.error(f"   OCR is required to extract text from scanned PDFs")
            logger.error(f"   Consider using tools like Adobe Acrobat, Tesseract OCR, or online OCR services")
            logger.error(f"   Skipping this file for now...")

        chunks = self.chunk_text(text)

        metadata = {
            "file_name": file_name,
            "file_path": file_path,
            "file_hash": file_hash,
            "num_chunks": len(chunks),
            "is_scanned": len(text) == 0
        }

        return chunks, metadata

    def process_all_pdfs(self) -> List[Dict]:
        """
        Process all PDFs in the directory.

        Returns:
            List of dicts containing chunks and metadata for each PDF
        """
        pdf_files = self.get_pdf_files()

        if not pdf_files:
            print(f"No PDF files found in {self.pdf_directory}")
            return []

        processed_docs = []

        for pdf_file in pdf_files:
            print(f"Processing {os.path.basename(pdf_file)}...")
            chunks, metadata = self.process_pdf(pdf_file)

            for idx, chunk in enumerate(chunks):
                doc = {
                    "content": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": idx
                    }
                }
                processed_docs.append(doc)

        print(f"Processed {len(pdf_files)} PDF files into {len(processed_docs)} chunks")
        return processed_docs


if __name__ == "__main__":
    # Test the processor
    processor = PDFProcessor("./pdfs")
    docs = processor.process_all_pdfs()
    print(f"\nTotal documents: {len(docs)}")
    if docs:
        print(f"Sample chunk: {docs[0]['content'][:200]}...")
