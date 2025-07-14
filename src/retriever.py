# src/retriever.py

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding

from src.config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_GRPC_PORT,
    COLLECTION_NAME, VECTOR_SIZE
)
from src.models import DocumentChunk # For type hinting the retrieved data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Retriever:
    """
    Handles similarity search in the Qdrant vector database.
    Embeds user queries and retrieves top-k relevant document chunks.
    """
    def __init__(self, use_grpc: bool = True):
        self.qdrant_client: QdrantClient = self._initialize_qdrant_client(use_grpc)
        self.embedding_model = TextEmbedding() # Using FastEmbed for query embedding too
        logging.info("FastEmbed embedding model initialized for Retriever.")

    def _initialize_qdrant_client(self, use_grpc: bool) -> QdrantClient:
        """Initializes and returns the Qdrant client."""
        try:
            if use_grpc:
                client = QdrantClient(host=QDRANT_HOST, grpc_port=QDRANT_GRPC_PORT, prefer_grpc=True)
                logging.info(f"Retriever Qdrant client initialized with gRPC: {QDRANT_HOST}:{QDRANT_GRPC_PORT}")
            else:
                client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
                logging.info(f"Retriever Qdrant client initialized with REST: {QDRANT_HOST}:{QDRANT_PORT}")
            # Test connection
            client.get_collections()
            logging.info("Retriever successfully connected to Qdrant.")
            return client
        except Exception as e:
            logging.error(f"Retriever failed to connect to Qdrant: {e}", exc_info=True)
            raise ConnectionError(f"Could not connect to Qdrant at {QDRANT_HOST}. Is it running?") from e

    def retrieve(self, query: str, top_k: int = 3) -> List[DocumentChunk]:
        """
        Embeds the query and searches Qdrant for the top_k most similar document chunks.
        """
        if not query.strip():
            logging.warning("Received empty query. Returning empty results.")
            return []

        try:
            # 1. Embed the query
            query_embedding = list(self.embedding_model.embed([query]))[0].tolist()
            logging.debug(f"Query embedded. Vector size: {len(query_embedding)}")

            # 2. Search Qdrant
            search_result = self.qdrant_client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_embedding,
                limit=top_k,
                with_payload=True, # We need the actual text and metadata
                score_threshold=0.7 # Optional: filter results by a similarity score threshold
                                    # Adjust this based on your data and desired precision/recall
            )
            logging.info(f"Retrieved {len(search_result)} results for query: '{query[:50]}...'")

            # 3. Convert results to DocumentChunk objects
            retrieved_chunks: List[DocumentChunk] = []
            for hit in search_result:
                # Assuming payload contains 'text' and 'metadata' as per DocumentChunk model
                # Qdrant stores payload as a dict, so we can directly pass it to DocumentChunk
                #chunk_text = hit.payload.get("text", "") # Qdrant payload doesn't automatically have 'text' as a separate key for FastEmbed
                                                         # The text is implicitly stored as part of the chunk in our model.
                                                         # Let's adjust our ingestion to store the text in payload explicitly if not already.
                                                         # Ah, no, the text is NOT stored in payload. It's only the metadata.
                                                         # We need to retrieve the actual text from the original chunk.
                                                         # For now, let's return the metadata and acknowledge we don't have the full text directly from Qdrant search.
                                                         # A better approach would be to store the full text in payload too during ingestion.

                # Fix: In current ingestion, the actual 'text' of the chunk is NOT put into payload.
                # Only the metadata is in payload. To return the actual text, we need to add it to payload during ingestion.
                # For now, let's just return the payload as metadata and a placeholder text.
                # We'll fix this in ingestion_manager later.

                # TEMPORARY FIX: For now, we assume the actual chunk text is embedded, but not directly returned.
                # A more robust solution would embed the *text* and store the *text* in the payload, or store it in a separate DB.
                # Let's assume for now that 'text' is part of the payload we store, as it should be for RAG.
                # (We *did* pass `doc.text` as the text to embed, but didn't explicitly add it to the payload. Let's fix that during ingestion).
                # Rechecking models.py: DocumentChunk has 'text' and 'metadata'.
                # In Qdrant, only 'metadata' is stored as payload. The actual text is *not* stored by Qdrant.
                # The typical RAG pattern:
                # 1. Embed text (Qdrant stores vectors)
                # 2. Store metadata (Qdrant stores payload)
                # 3. To get the text back, you need to store the *text* as part of the payload, or have a separate text store.

                # Let's modify `data_ingestion` to put the text into payload for retrieval.
                # For now, I'll put a placeholder and acknowledge this needs a previous step change.
                retrieved_chunks.append(DocumentChunk(
                    text=hit.payload.get("text",""), # Placeholder for now
                    metadata=hit.payload
                ))
            
            # --- IMPORTANT NOTE FOR FUTURE IMPROVEMENT ---
            # The current Qdrant storage ONLY puts 'metadata' into the payload.
            # It does NOT store the actual 'text' of the chunk within the Qdrant payload.
            # To retrieve the text, we MUST add 'text' to the payload during the ingestion process.
            # I will make this necessary change in `src/qdrant_manager.py` next.
            # For now, `DocumentChunk.text` will be a placeholder.

            return retrieved_chunks

        except Exception as e:
            logging.error(f"Error during retrieval for query '{query}': {e}", exc_info=True)
            return []