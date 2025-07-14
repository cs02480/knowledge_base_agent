# src/qdrant_manager.py

import logging
import hashlib
from typing import List
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

from src.config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_GRPC_PORT,
    COLLECTION_NAME, VECTOR_SIZE, DISTANCE_METRIC
)
from src.models import DocumentChunk # Import DocumentChunk for type hinting

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QdrantManager:
    """Manages all interactions with the Qdrant vector database."""
    def __init__(self, use_grpc: bool = True):
        self.qdrant_client: QdrantClient = self._initialize_qdrant_client(use_grpc)
        self.embedding_model = TextEmbedding() # FastEmbed is initialized here
        logging.info("FastEmbed embedding model initialized for QdrantManager.")

    def _initialize_qdrant_client(self, use_grpc: bool) -> QdrantClient:
        """Initializes and returns the Qdrant client."""
        try:
            if use_grpc:
                client = QdrantClient(host=QDRANT_HOST, grpc_port=QDRANT_GRPC_PORT, prefer_grpc=True)
                logging.info(f"Qdrant client initialized with gRPC: {QDRANT_HOST}:{QDRANT_GRPC_PORT}")
            else:
                client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
                logging.info(f"Qdrant client initialized with REST: {QDRANT_HOST}:{QDRANT_PORT}")
            # Test connection
            client.get_collections()
            logging.info("Successfully connected to Qdrant.")
            return client
        except Exception as e:
            logging.error(f"Failed to connect to Qdrant: {e}", exc_info=True)
            raise ConnectionError(f"Could not connect to Qdrant at {QDRANT_HOST}. Is it running?") from e

    def recreate_collection(self) -> None:
        """Recreates the Qdrant collection, deleting any existing data."""
        try:
            self.qdrant_client.recreate_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(size=VECTOR_SIZE, distance=models.Distance[DISTANCE_METRIC.upper()]),
            )
            logging.info(f"Collection '{COLLECTION_NAME}' recreated (or created) with vector size {VECTOR_SIZE} and distance metric {DISTANCE_METRIC}.")
        except Exception as e:
            logging.error(f"Error recreating Qdrant collection '{COLLECTION_NAME}': {e}", exc_info=True)
            raise

    def upload_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Generates embeddings for chunks and uploads them to Qdrant.
        Returns the number of points successfully uploaded.
        """
        if not chunks:
            logging.warning("No chunks provided for upload to Qdrant.")
            return 0

        texts_to_embed = [chunk.text for chunk in chunks]
        
        embeddings_generator = self.embedding_model.embed(texts_to_embed)
        
        points_to_upsert: List[models.PointStruct] = []
        
        for i, (embedding, original_chunk) in enumerate(zip(embeddings_generator, chunks)):
             # --- DEBUG PRINTS START ---
            if i < 5: # Only print for the first few chunks to avoid spamming the console
                logging.info(f"Debug: Processing chunk {i} from file {original_chunk.metadata.get('source_file')}")
                logging.info(f"Debug: Type of embedding: {type(embedding)}")
                if hasattr(embedding, 'shape'):
                    logging.info(f"Debug: Shape of embedding: {embedding.shape}")
                logging.info(f"Debug: First 5 elements of embedding: {embedding.tolist()[:5]}")
            # --- DEBUG PRINTS END ---
            # Use a deterministic ID for each point based on source_file, page_number, and chunk_index
            unique_chunk_identifier = f"{original_chunk.metadata['source_file']}_{original_chunk.metadata.get('page_number', '')}_{original_chunk.metadata['chunk_index']}"
            point_id = int(hashlib.sha256(unique_chunk_identifier.encode('utf-8')).hexdigest()[:16], 16)
            
            # --- IMPORTANT MODIFICATION HERE ---
            # Add the actual 'text' of the chunk to the payload so it can be retrieved later.
            payload = original_chunk.metadata.copy() # Start with existing metadata
            payload["text"] = original_chunk.text    # Add the full chunk text to payload
            
            points_to_upsert.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload
                )
            )

        try:
            operation_info = self.qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                wait=True,
                points=points_to_upsert
            )
            logging.info(f"Upserted {len(points_to_upsert)} points to Qdrant. Status: {operation_info.status}")
            return len(points_to_upsert)
        except Exception as e:
            logging.error(f"Error during Qdrant upsert operation: {e}", exc_info=True)
            raise # Re-raise to indicate failure

    def delete_points_by_file(self, file_name: str) -> int:
        """
        Deletes all points associated with a specific file from the Qdrant collection.
        Returns the number of points deleted.
        """
        try:
            delete_result = self.qdrant_client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="source_file",
                                match=models.MatchValue(value=file_name)
                            )
                        ]
                    )
                ),
                wait=True
            )
            logging.info(f"Attempted to delete points for file '{file_name}' from Qdrant. Status: {delete_result.status}")
            return 1 # Indicate that delete operation was attempted
        except Exception as e:
            logging.error(f"Error deleting points for file '{file_name}' from Qdrant: {e}", exc_info=True)
            raise

    def get_collection_info(self):
        """Retrieves and logs information about the Qdrant collection."""
        try:
            collection_info = self.qdrant_client.get_collection(collection_name=COLLECTION_NAME)
            logging.info(f"Collection '{COLLECTION_NAME}' status: {collection_info.status}")
            logging.info(f"Number of points in collection: {collection_info.vectors_count}")
            logging.info(f"Collection config: {collection_info.config}")
            return collection_info
        except Exception as e:
            logging.error(f"Error getting collection info for '{COLLECTION_NAME}': {e}", exc_info=True)
            # Depending on context, you might want to raise, but for info retrieval, return None is often fine.
            return None