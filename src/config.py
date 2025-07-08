# src/config.py

import os

# Base directory for data
DATA_DIR = "data"
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
TEXT_DIR = os.path.join(DATA_DIR, "texts")

# File to track ingested documents
INGESTED_TRACKER_FILE = os.path.join(DATA_DIR, "ingested_files.json")

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333  # Default REST API port for Qdrant
QDRANT_GRPC_PORT = 6334 # Default gRPC port for Qdrant
COLLECTION_NAME = "knowledge_base_collection"
VECTOR_SIZE = 384  # Default embedding size for BGE-small-en-v1.5 (used by FastEmbed)
DISTANCE_METRIC = "Cosine" # Cosine similarity is common for embeddings

# Text Chunking parameters
CHUNK_SIZE = 500  # Number of characters per chunk
CHUNK_OVERLAP = 50 # Overlap between chunks to maintain context

# Ensure directories exist (handled in main_ingestion.py now or at startup of the whole system)
# For now, let's keep it here for simplicity when individual modules are run.
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)