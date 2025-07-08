# src/models.py

from pydantic import BaseModel
from typing import List, Dict, Union, Optional

class DocumentChunk(BaseModel):
    """Represents a chunk of text from a document with associated metadata."""
    text: str
    metadata: Dict[str, Union[str, int, float, List[str]]]

class IngestedFileInfo(BaseModel):
    """Represents information about an ingested file for tracking."""
    file_path: str
    last_modified: float # Unix timestamp of last modification
    ingested_at: float   # Unix timestamp of ingestion
    status: str          # e.g., "success", "failed", "skipped_empty", "skipped_no_chunks"
    error_message: Optional[str] = None