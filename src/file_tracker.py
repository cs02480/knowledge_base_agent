# src/file_tracker.py

import os
import json
import time
import logging
from typing import Dict
from src.models import IngestedFileInfo
from src.config import INGESTED_TRACKER_FILE # Import tracker file path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FileTracker:
    """Manages the tracking of ingested files using a JSON file."""
    def __init__(self):
        self.tracker: Dict[str, IngestedFileInfo] = self._load_tracker()

    def _load_tracker(self) -> Dict[str, IngestedFileInfo]:
        """Loads the state of ingested files from a JSON file."""
        if not os.path.exists(INGESTED_TRACKER_FILE):
            logging.info(f"Ingested files tracker not found at {INGESTED_TRACKER_FILE}. Creating empty tracker.")
            return {}
        try:
            with open(INGESTED_TRACKER_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Deserialize into IngestedFileInfo objects
                return {k: IngestedFileInfo(**v) for k, v in data.items()}
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding ingested files tracker: {e}. Starting with empty tracker.", exc_info=True)
            return {}
        except Exception as e:
            logging.error(f"Unexpected error loading ingested files tracker: {e}. Starting with empty tracker.", exc_info=True)
            return {}

    def _save_tracker(self):
        """Saves the current state of ingested files to a JSON file."""
        try:
            # Serialize IngestedFileInfo objects to dictionary for JSON saving
            data_to_save = {k: v.model_dump() for k, v in self.tracker.items()}
            os.makedirs(os.path.dirname(INGESTED_TRACKER_FILE), exist_ok=True) # Ensure directory exists
            with open(INGESTED_TRACKER_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
            logging.debug("Ingested files tracker saved.")
        except Exception as e:
            logging.error(f"Error saving ingested files tracker: {e}", exc_info=True)

    def should_ingest(self, file_path: str) -> bool:
        """
        Checks if a file needs to be ingested (new or modified).
        Returns True if ingestion is required, False otherwise.
        """
        file_abspath = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            logging.warning(f"File does not exist: {file_path}. Cannot check ingestion status.")
            return False # Or raise an error, depending on desired strictness

        current_last_modified = os.path.getmtime(file_path)

        if file_abspath not in self.tracker:
            logging.info(f"File '{os.path.basename(file_path)}' is new. Will ingest.")
            return True

        tracked_info = self.tracker[file_abspath]

        if tracked_info.status != "success":
            logging.warning(f"File '{os.path.basename(file_path)}' was previously '{tracked_info.status}'. Re-ingesting.")
            return True # Always retry if previous ingestion failed or was skipped

        if current_last_modified > tracked_info.last_modified:
            logging.info(f"File '{os.path.basename(file_path)}' has been modified (last modified: {time.ctime(current_last_modified)} > tracked: {time.ctime(tracked_info.last_modified)}). Will re-ingest.")
            return True
        
        logging.debug(f"File '{os.path.basename(file_path)}' already ingested and not modified.")
        return False

    def update_file_status(self, file_path: str, status: str, error_message: str = None):
        """Updates the ingestion status of a file in the tracker."""
        file_abspath = os.path.abspath(file_path)
        self.tracker[file_abspath] = IngestedFileInfo(
            file_path=file_abspath,
            last_modified=os.path.getmtime(file_path) if os.path.exists(file_path) else time.time(), # Use current if file deleted
            ingested_at=time.time(),
            status=status,
            error_message=error_message
        )
        self._save_tracker() # Save after each update to ensure persistence