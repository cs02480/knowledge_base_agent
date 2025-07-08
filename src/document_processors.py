# src/document_processors.py

import os
import fitz  # PyMuPDF
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Union
from langchain.text_splitter import RecursiveCharacterTextSplitter

from models import DocumentChunk
from config import CHUNK_SIZE, CHUNK_OVERLAP # Import chunking config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DocumentProcessor(ABC):
    """
    Abstract base class for document processors.
    Defines the interface for extracting text and chunking.
    """
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        logging.debug(f"Text splitter initialized in {self.__class__.__name__} with chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}")

    @abstractmethod
    def extract_text(self, file_path: str) -> List[str]:
        """
        Abstract method to extract text from a given file path.
        Returns a list of strings, where each string represents text from a page, section, or the whole document.
        Raises an exception if extraction fails.
        """
        pass

    def chunk_document(self, file_path: str, text_content: List[str]) -> List[DocumentChunk]:
        """
        Chunks the extracted text content into smaller, overlapping segments.
        Handles multi-page/section content and adds relevant metadata to each chunk.
        """
        all_processed_chunks: List[DocumentChunk] = []
        file_name = os.path.basename(file_path)
        file_type = os.path.splitext(file_name)[1].lstrip('.')

        # Determine if content is multi-page (list of strings) or single string
        is_multi_page = len(text_content) > 1 or (len(text_content) == 1 and '\n\n' in text_content[0] and file_type == 'pdf') # Heuristic for PDF pages

        for i, section_text in enumerate(text_content):
            if not section_text.strip():
                logging.debug(f"Skipping empty text section {i+1} from {file_name}.")
                continue

            chunks = self.text_splitter.split_text(section_text)
            for j, chunk_text in enumerate(chunks):
                metadata = {
                    "source_file": file_name,
                    "file_type": file_type,
                    "chunk_index": j,
                    "text_length": len(chunk_text),
                }
                if is_multi_page:
                    metadata["page_number"] = i + 1  # Add page number for multi-page documents
                    metadata["chunk_id"] = f"{file_name}_p{i+1}_{j}"
                else:
                     metadata["chunk_id"] = f"{file_name}_{j}"


                all_processed_chunks.append(DocumentChunk(text=chunk_text, metadata=metadata))

        logging.info(f"Generated {len(all_processed_chunks)} chunks for {file_name}.")
        return all_processed_chunks

class PdfProcessor(DocumentProcessor):
    """Processor for PDF documents using PyMuPDF."""
    def extract_text(self, file_path: str) -> List[str]:
        text_content: List[str] = []
        try:
            document = fitz.open(file_path)
            for page_num in range(document.page_count):
                page = document.load_page(page_num)
                text = page.get_text("text")
                text_content.append(text)
            logging.info(f"Successfully extracted text from {document.page_count} pages of PDF: {file_path}")
            return text_content
        except Exception as e:
            logging.error(f"Error extracting text from PDF {file_path}: {e}")
            raise # Re-raise to indicate extraction failure

class TextProcessor(DocumentProcessor):
    """Processor for plain text (.txt) documents."""
    def extract_text(self, file_path: str) -> List[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logging.info(f"Successfully read text from TXT: {file_path}")
            return [content] # Return as a list for consistency
        except Exception as e:
            logging.error(f"Error reading text from TXT {file_path}: {e}")
            raise # Re-raise to indicate reading failure

# Add more processors here as needed
# class DocxProcessor(DocumentProcessor):
#     def extract_text(self, file_path: str) -> List[str]:
#         # Implement docx text extraction logic here
#         pass

# class ImageProcessor(DocumentProcessor):
#     def extract_text(self, file_path: str) -> List[str]:
#         # Implement OCR logic here for images
#         pass