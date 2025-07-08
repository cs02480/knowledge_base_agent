# src/ingestion_manager.py

import os
import logging
import time
from typing import Dict

from qdrant_manager import QdrantManager
from document_processors import DocumentProcessor, PdfProcessor, TextProcessor # Import all processors
from file_tracker import FileTracker
from config import PDF_DIR, TEXT_DIR, COLLECTION_NAME # Import directories and collection name

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IngestionManager:
    """
    Orchestrates the entire document ingestion process.
    Handles discovery, processing, embedding, and uploading to Qdrant.
    Manages file tracking to ensure only new or modified documents are processed.
    """
    def __init__(self, use_grpc: bool = True):
        self.qdrant_manager = QdrantManager(use_grpc=use_grpc)
        self.file_tracker = FileTracker()
        
        self.processors: Dict[str, DocumentProcessor] = {
            "pdf": PdfProcessor(),
            "txt": TextProcessor()
            # Add other processors here when available:
            # "docx": DocxProcessor(),
            # "jpg": ImageProcessor(),
            # "png": ImageProcessor(),
        }
        logging.info("IngestionManager initialized with QdrantManager, FileTracker, and document processors.")

    def _process_and_ingest_single_document(self, file_path: str, file_type: str):
        """
        Internal method to process a single document and ingest its chunks into Qdrant.
        Manages the full lifecycle for one file, including error handling and status tracking.
        """
        logging.info(f"Starting ingestion process for file: '{os.path.basename(file_path)}' (Type: {file_type})")
        
        processor = self.processors.get(file_type)
        if not processor:
            logging.error(f"No document processor found for file type: '{file_type}'. Skipping '{file_path}'.")
            self.file_tracker.update_file_status(file_path, "failed", f"No processor for type '{file_type}'")
            return

        file_name = os.path.basename(file_path)
        ingestion_status = "failed"
        error_message = None
        start_time = time.time()
        
        try:
            # --- START FIX ---
            file_abspath = os.path.abspath(file_path)
            
            # Check if the file was previously successfully ingested and exists in Qdrant
            # Use get_collection_info() from QdrantManager for robustness
            collection_info = self.qdrant_manager.get_collection_info()
            
            # Only attempt to delete if:
            # 1. The file was tracked as successfully ingested before.
            # 2. Qdrant collection exists and has vectors (optional, but good for efficiency).
            # 3. This isn't the first time the collection is created (as recreate_collection is used).
            #    Given we use recreate_collection at the start of run_ingestion_scan,
            #    the collection is usually empty on the *first* run of the whole scan.
            #    However, if a file is modified and *then* re-processed *within the same scan*,
            #    or if you run `process_and_ingest_single_document` independently,
            #    this logic becomes crucial.
            
            if (file_abspath in self.file_tracker.tracker and 
                self.file_tracker.tracker[file_abspath].status == "success" and
                collection_info and collection_info.vectors_count is not None and collection_info.vectors_count > 0):
                
                logging.info(f"Detected modification/re-ingestion for '{file_name}'. Deleting old points from Qdrant.")
                self.qdrant_manager.delete_points_by_file(file_name)
            # --- END FIX ---


            # Step 1: Extract Text
            extracted_text_content = processor.extract_text(file_path)
            if not extracted_text_content or all(not t.strip() for t in extracted_text_content):
                logging.warning(f"No usable text extracted from '{file_path}'. Skipping ingestion.")
                ingestion_status = "skipped_empty"
                error_message = "No text extracted or extracted text was empty."
                return

            # Step 2: Chunk Text
            document_chunks = processor.chunk_document(file_path, extracted_text_content)
            if not document_chunks:
                logging.warning(f"No chunks generated for '{file_path}'. Skipping ingestion.")
                ingestion_status = "skipped_no_chunks"
                error_message = "No chunks generated from extracted text."
                return

            # Step 3: Embed and Upload to Qdrant
            uploaded_count = self.qdrant_manager.upload_chunks(document_chunks)
            if uploaded_count == len(document_chunks):
                ingestion_status = "success"
                logging.info(f"Successfully ingested and uploaded {uploaded_count} chunks for '{file_name}'.")
            else:
                ingestion_status = "failed"
                error_message = f"Mismatch in uploaded chunks count. Expected {len(document_chunks)}, got {uploaded_count}."
                logging.error(error_message)

        except Exception as e:
            logging.error(f"Critical error during ingestion of '{file_path}': {e}", exc_info=True)
            ingestion_status = "failed"
            error_message = str(e)
        finally:
            self.file_tracker.update_file_status(file_path, ingestion_status, error_message)
            logging.info(f"Finished processing '{file_path}' in {time.time() - start_time:.2f} seconds with final status: {ingestion_status}")


    def run_ingestion_scan(self):
        """
        Scans designated data directories for new or modified documents
        and triggers their ingestion into Qdrant.
        """
        logging.info("Starting Qdrant collection setup...")
        # For development, recreating is fine. In production, consider `create_collection_if_not_exists()`
        # which would be part of QdrantManager.
        self.qdrant_manager.recreate_collection() 

        logging.info("Starting document ingestion scan...")

        # Process PDF files
        for f in os.listdir(PDF_DIR):
            if f.endswith('.pdf'):
                file_path = os.path.join(PDF_DIR, f)
                if self.file_tracker.should_ingest(file_path):
                    self._process_and_ingest_single_document(file_path, "pdf")
        
        # Process TXT files
        for f in os.listdir(TEXT_DIR):
            if f.endswith('.txt'):
                file_path = os.path.join(TEXT_DIR, f)
                if self.file_tracker.should_ingest(file_path):
                    self._process_and_ingest_single_document(file_path, "txt")

        logging.info("Document ingestion scan complete.")
        self.qdrant_manager.get_collection_info() # Display final collection stats