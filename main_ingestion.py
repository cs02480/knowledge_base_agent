# main_ingestion.py

import os
import logging
import fitz # For dummy PDF creation
import time # For simulating touch
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from src.ingestion_manager import IngestionManager
from src.config import PDF_DIR, TEXT_DIR # Import necessary paths

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_initial_dummy_data():
    """Creates initial sample PDF and text files if they don't exist."""
    logging.info("Ensuring dummy data directories exist...")
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(TEXT_DIR, exist_ok=True)

    txt_file_path = os.path.join(TEXT_DIR, "sample_article.txt")
    pdf_file_path = os.path.join(PDF_DIR, "sample_report.pdf")

    if not os.path.exists(txt_file_path):
        with open(txt_file_path, "w", encoding="utf-8") as f:
            f.write("This is a sample text document about the benefits of renewable energy. "
                    "Solar power is increasingly becoming a major contributor to the energy grid. "
                    "Wind energy also plays a crucial role in sustainable development. "
                    "The world is moving towards a greener future. "
                    "This document contains several sentences and aims to test the chunking process. "
                    "It's important to keep chunks semantically coherent.")
        logging.info(f"Initial dummy text file '{os.path.basename(txt_file_path)}' created.")
    else:
        logging.info(f"Dummy text file '{os.path.basename(txt_file_path)}' already exists. Skipping initial creation.")

    if not os.path.exists(pdf_file_path):
        try:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "This is the first page of a sample PDF document.\n\nIt talks about various topics like artificial intelligence.")
            page = doc.new_page()
            page.insert_text((72, 72), "The second page continues the discussion, focusing on machine learning and deep learning applications. "
                                         "These technologies are transforming industries worldwide. "
                                         "Data is the new oil in the digital economy.")
            doc.save(pdf_file_path)
            doc.close()
            logging.info(f"Initial dummy PDF '{os.path.basename(pdf_file_path)}' created.")
        except Exception as e:
            logging.error(f"Could not create dummy PDF (PyMuPDF might be having issues saving): {e}", exc_info=True)
            logging.warning("Please ensure PyMuPDF is correctly installed or manually create a sample PDF.")
    else:
        logging.info(f"Dummy PDF '{os.path.basename(pdf_file_path)}' already exists. Skipping initial creation.")


def simulate_document_changes():
    """Simulates adding a new document and modifying an existing one."""
    logging.info("\n--- Simulating new document addition and modification for next run ---")

    # Add a truly new text document
    new_txt_path = os.path.join(TEXT_DIR, "new_research_paper.txt")
    if not os.path.exists(new_txt_path): # Only create if new
        with open(new_txt_path, "w", encoding="utf-8") as f:
            f.write("A groundbreaking new research paper on quantum computing has been published. "
                    "It describes novel algorithms for error correction. "
                    "The future of computing looks very different. This is brand new information.")
        logging.info(f"New document '{os.path.basename(new_txt_path)}' created.")
    else:
        # If it exists, modify it to trigger re-ingestion
        logging.info(f"Modifying existing new document '{os.path.basename(new_txt_path)}' to trigger re-ingestion.")
        with open(new_txt_path, "a", encoding="utf-8") as f: # Append some data
            f.write(f"\nAppended new content at {time.ctime()} for re-ingestion test.")


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
            # A simple touch operation might be better if you don't want to change content
            # For this example, let's append a small text to ensure content change and mtime change
            # However, for real testing, a simple `os.utime(modified_pdf_path, None)` would just update mtime.
            page_text = page.get_text("text")
            page.delete_contents()
            page.insert_text((72, 72), page_text + f" (Updated content on page 1 at {time.ctime()}) ", fontsize=8) # Small update to change content hash/timestamp
            logging.info("Updated content on page 1 of 'sample_report.pdf'.")

        doc.save(modified_pdf_path, clean=True, pretty=True, garbage=4) # Overwrite existing with cleaner output
        doc.close()
        logging.info(f"Existing PDF '{os.path.basename(modified_pdf_path)}' modified.")
    except Exception as e:
        logging.error(f"Could not modify dummy PDF: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n--- Starting Knowledge Base Data Ingestion Process ---")
    
    # --- IMPORTANT CHANGE HERE ---
    # Call create_initial_dummy_data() only if you want to ensure they exist
    # For repeated runs where you don't want to re-ingest, comment this out
    create_initial_dummy_data() 

    ingestion_manager = IngestionManager(use_grpc=True) # Initialize the orchestrator
    
    # --- OPTION TO CLEAR ALL DATA ---
    # Uncomment the line below if you want to clear ALL previously ingested data
    # from Qdrant and reset the file tracker before proceeding.
    # This is useful for starting with a completely clean slate.
    # 
    # >>> Add/Uncomment it HERE:
    ingestion_manager.clear_all_ingested_data()
    
    # --- Initial Ingestion Run ---
    logging.info("\n--- Running initial ingestion scan (should process untouched files) ---")
    ingestion_manager.run_ingestion_scan()
    logging.info("Initial ingestion scan complete.")

    # --- To test subsequent runs without re-ingesting unmodified files: ---
    # 1. Run the script once (above).
    # 2. Comment out `create_initial_dummy_data()` and `simulate_document_changes()` calls below.
    # 3. Run the script again. It should log that files are "already ingested and NOT MODIFIED."

    # --- To test new/modified document scenario: ---
    # After an initial run, uncomment this block to simulate changes and run again.
    #simulate_document_changes() # Prepare new/modified files
    #logging.info("\n--- Running ingestion scan again (should only process new/modified files) ---")
    #ingestion_manager.run_ingestion_scan()
    #logging.info("Second ingestion scan complete.")

    logging.info("\n--- All ingestion processes finished. ---")