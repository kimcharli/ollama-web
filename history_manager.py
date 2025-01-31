import json
import os
from datetime import datetime
from typing import List, Dict, Any

class HistoryManager:
    def __init__(self, history_file: str = 'query_history.json'):
        self.history_file = history_file
        self._ensure_history_file()

    def _ensure_history_file(self):
        """Create history file if it doesn't exist"""
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f)

    def load_history(self) -> List[Dict[str, Any]]:
        """Load history from file"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_history(self, history: List[Dict[str, Any]]):
        """Save history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def add_entry(self, model: str, prompt: str, result: str, duration: float, success: bool):
        """Add a new entry to history"""
        history = self.load_history()
        entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'model': model,
            'prompt': prompt,
            'result': result,
            'duration': duration,
            'success': success
        }
        history.append(entry)
        
        # Keep only the last 100 entries
        if len(history) > 100:
            history = history[-100:]
            
        self.save_history(history)
        return history

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get history entries, optionally limited to the last N entries"""
        history = self.load_history()
        if limit:
            return history[-limit:]
        return history

    def clear_history(self):
        """Clear all history"""
        self.save_history([])
