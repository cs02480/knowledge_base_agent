# main_ingestion.py

import os
import logging
import fitz # For dummy PDF creation
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from ingestion_manager import IngestionManager
from config import PDF_DIR, TEXT_DIR # Import necessary paths

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_dummy_data():
    """Creates sample PDF and text files for testing purposes."""
    logging.info("Ensuring dummy data directories exist...")
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TEXT_DIR, exist_ok=True)

    # Dummy text file
    txt_file_path = os.path.join(TEXT_DIR, "sample_article.txt")
    with open(txt_file_path, "w", encoding="utf-8") as f:
        f.write("This is a sample text document about the benefits of renewable energy. "
                "Solar power is increasingly becoming a major contributor to the energy grid. "
                "Wind energy also plays a crucial role in sustainable development. "
                "The world is moving towards a greener future. "
                "This document contains several sentences and aims to test the chunking process. "
                "It's important to keep chunks semantically coherent. This is a new sentence.")
    logging.info(f"Dummy text file '{os.path.basename(txt_file_path)}' created/updated.")

    # Dummy PDF file
    pdf_file_path = os.path.join(PDF_DIR, "sample_report.pdf")
    try:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "This is the first page of a sample PDF document.\n\nIt talks about various topics like artificial intelligence.")
        page = doc.new_page()
        page.insert_text((72, 72), "The second page continues the discussion, focusing on machine learning and deep learning applications. "
                                     "These technologies are transforming industries worldwide. "
                                     "Data is the new oil in the digital economy. Some more content here to make it a bit longer.")
        doc.save(pdf_file_path)
        doc.close()
        logging.info(f"Dummy PDF '{os.path.basename(pdf_file_path)}' created/updated.")
    except Exception as e:
        logging.error(f"Could not create dummy PDF (PyMuPDF might be having issues saving): {e}", exc_info=True)
        logging.warning("Please ensure PyMuPDF is correctly installed or manually create a sample PDF.")


if __name__ == "__main__":
    print("\n--- Starting Knowledge Base Data Ingestion Process ---")
    create_dummy_data() # Ensure sample data is present for testing

    ingestion_manager = IngestionManager(use_grpc=True) # Initialize the orchestrator
    
    # --- Initial Ingestion Run ---
    logging.info("\n--- Running initial ingestion scan (all files) ---")
    ingestion_manager.run_ingestion_scan()
    logging.info("Initial ingestion scan complete.")

    # --- Simulate adding new documents and modifying existing ones ---
    logging.info("\n--- Simulating new document addition and modification for next run ---")

    # Add a truly new text document
    new_txt_path = os.path.join(TEXT_DIR, "new_research_paper.txt")
    with open(new_txt_path, "w", encoding="utf-8") as f:
        f.write("A groundbreaking new research paper on quantum computing has been published. "
                "It describes novel algorithms for error correction. "
                "The future of computing looks very different. This is brand new information.")
    logging.info(f"New document '{os.path.basename(new_txt_path)}' created.")

    # Modify an existing PDF by adding content and saving it again
    modified_pdf_path = os.path.join(PDF_DIR, "sample_report.pdf")
    try:
        doc = fitz.open(modified_pdf_path) # Open existing
        # Add a new page or modify content on existing page
        if doc.page_count < 3:
            page = doc.new_page()
            page.insert_text((72, 72), "This is a NEW third page with important updates on AI ethics and responsible development. "
                                         "Considering the current year 2025, ethical AI is a top priority.")
            logging.info("Added a new page to 'sample_report.pdf'.")
        else:
            # If already 3 pages, just update content of an existing page to trigger timestamp change
            page = doc.load_page(0)
            page.insert_text((72, 92), " (Updated content on page 1) ", fontsize=8) # Small update to change content hash/timestamp
            logging.info("Updated content on page 1 of 'sample_report.pdf'.")

        doc.save(modified_pdf_path, clean=True, pretty=True, garbage=4) # Overwrite existing with cleaner output
        doc.close()
        logging.info(f"Existing PDF '{os.path.basename(modified_pdf_path)}' modified.")
    except Exception as e:
        logging.error(f"Could not modify dummy PDF: {e}", exc_info=True)

    # Re-run the ingestion process
    logging.info("\n--- Running ingestion scan again (should only process new/modified files) ---")
    ingestion_manager.run_ingestion_scan()
    logging.info("Second ingestion scan complete.")

    logging.info("\n--- All ingestion processes finished. ---")