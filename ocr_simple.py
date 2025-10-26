#!/usr/bin/env python3
"""
Simple OCR Script for Scanned PDFs - Minimal Dependencies

This is a simplified version that only requires:
- Python packages: ocrmypdf, pillow
- External: Tesseract OCR

No need for: ghostscript, unpaper, or other utilities

Usage:
    python ocr_simple.py input.pdf output.pdf
    python ocr_simple.py --dir pdfs/ pdfs_ocr/
"""

import os
import sys
import logging
import argparse
from pathlib import Path

try:
    import ocrmypdf
except ImportError:
    print("❌ ocrmypdf not installed. Run: pip install ocrmypdf pillow")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def ocr_pdf_simple(input_path: str, output_path: str, lang: str = 'eng') -> bool:
    """
    Apply OCR to a PDF with minimal settings.

    Args:
        input_path: Input PDF path
        output_path: Output PDF path
        lang: Language code (eng, fra, deu, etc.)

    Returns:
        True if successful
    """
    logger.info(f"Processing: {os.path.basename(input_path)}")

    try:
        # Minimal OCR settings - no external dependencies required
        ocrmypdf.ocr(
            input_path,
            output_path,
            language=lang,
            skip_text=True,      # Skip pages with existing text
            progress_bar=True,   # Show progress
            use_threads=True,    # Faster processing
        )
        logger.info(f"✅ Success!")
        return True

    except ocrmypdf.exceptions.PriorOcrFoundError:
        logger.warning(f"⚠️  File already has text - copying...")
        import shutil
        shutil.copy2(input_path, output_path)
        return True

    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False


def ocr_directory(input_dir: str, output_dir: str, lang: str = 'eng'):
    """Process all PDFs in directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    if not input_path.exists():
        logger.error(f"Directory not found: {input_dir}")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found")
        return

    logger.info(f"Found {len(pdf_files)} PDFs to process\n")

    success = 0
    failed = 0

    for i, pdf_file in enumerate(pdf_files, 1):
        output_file = output_path / pdf_file.name

        logger.info(f"[{i}/{len(pdf_files)}] {pdf_file.name}")

        if ocr_pdf_simple(str(pdf_file), str(output_file), lang):
            success += 1
        else:
            failed += 1

        print()

    logger.info("=" * 60)
    logger.info(f"Complete: {success} successful, {failed} failed")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Simple OCR for scanned PDFs")
    parser.add_argument('input', help='Input PDF or directory')
    parser.add_argument('output', help='Output PDF or directory')
    parser.add_argument('--dir', action='store_true', help='Process directory')
    parser.add_argument('--lang', default='eng', help='Language (default: eng)')

    args = parser.parse_args()

    if args.dir:
        ocr_directory(args.input, args.output, args.lang)
    else:
        if ocr_pdf_simple(args.input, args.output, args.lang):
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
