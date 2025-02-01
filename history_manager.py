import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages the history of queries and results."""
    
    def __init__(self, history_file='query_history.json', max_entries=100):
        """Initialize the history manager.
        
        Args:
            history_file (str): Path to the history file
            max_entries (int): Maximum number of entries to keep in history
        """
        self.history_file = history_file or Config.HISTORY_FILE
        self.max_entries = max_entries or Config.MAX_HISTORY_ENTRIES
        logger.info(f'Initialized HistoryManager with file: {self.history_file}, max_entries: {self.max_entries}')
        
        # Create history file if it doesn't exist
        if not os.path.exists(self.history_file):
            logger.info(f'History file not found, creating new one at: {self.history_file}')
            self.save_history([])
    
    def load_history(self) -> List[Dict[str, Any]]:
        """Load history from file."""
        try:
            if os.path.exists(self.history_file):
                logger.debug(f'Loading history from: {self.history_file}')
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    # Ensure we don't exceed max entries
                    return history[-self.max_entries:]
            logger.warning(f'History file not found at: {self.history_file}')
            return []
        except Exception as e:
            logger.error(f'Error loading history: {e}', exc_info=True)
            return []
    
    def save_history(self, history: List[Dict[str, Any]]):
        """Save history to file."""
        try:
            logger.debug(f'Saving history to: {self.history_file}')
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f'Error saving history: {e}', exc_info=True)
            raise
    
    def add_entry(self, model: str, prompt: str, result: str, duration: float, success: bool):
        """Add a new entry to history.
        
        Args:
            model (str): The model used for analysis
            prompt (str): The prompt text
            result (str): The response from the model
            duration (float): Time taken in seconds
            success (bool): Whether the analysis was successful
        """
        try:
            logger.info(f'Adding history entry for model: {model}')
            history = self.load_history()
            
            # Create new entry
            entry = {
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'prompt': prompt,
                'result': result,
                'duration': duration,
                'success': success
            }
            
            # Add to end of list
            history.append(entry)
            
            # Trim to max entries
            if len(history) > self.max_entries:
                logger.debug(f'Trimming history to {self.max_entries} entries')
                history = history[-self.max_entries:]
            
            # Save updated history
            self.save_history(history)
            return history
        except Exception as e:
            logger.error(f'Error adding history entry: {e}', exc_info=True)
            raise

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get history entries, optionally limited to the last N entries"""
        history = self.load_history()
        if limit:
            return history[-limit:]
        return history

    def clear_history(self):
        """Clear all history."""
        logger.info('Clearing history')
        self.save_history([])
