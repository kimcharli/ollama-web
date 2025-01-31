import os
import json
import unittest
from datetime import datetime
from history_manager import HistoryManager

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        """Set up test history file"""
        self.test_history_file = 'test_history.json'
        self.history_manager = HistoryManager(
            history_file=self.test_history_file,
            max_entries=3
        )
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_history_file):
            os.remove(self.test_history_file)
    
    def test_add_entry(self):
        """Test adding entries to history"""
        # Add first entry
        self.history_manager.add_entry(
            model='test-model',
            prompt='test prompt',
            result='test result',
            duration=1.0,
            success=True
        )
        
        history = self.history_manager.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['model'], 'test-model')
        self.assertEqual(history[0]['prompt'], 'test prompt')
        
        # Add more entries than max_entries
        for i in range(3):
            self.history_manager.add_entry(
                model=f'model-{i}',
                prompt=f'prompt {i}',
                result=f'result {i}',
                duration=1.0,
                success=True
            )
        
        history = self.history_manager.load_history()
        self.assertEqual(len(history), 3)  # Should be limited by max_entries
        self.assertEqual(history[-1]['model'], 'model-2')
    
    def test_clear_history(self):
        """Test clearing history"""
        # Add some entries
        self.history_manager.add_entry(
            model='test-model',
            prompt='test prompt',
            result='test result',
            duration=1.0,
            success=True
        )
        
        # Clear history
        self.history_manager.clear_history()
        
        # Check that history is empty
        history = self.history_manager.load_history()
        self.assertEqual(len(history), 0)
    
    def test_history_persistence(self):
        """Test that history is properly saved and loaded"""
        # Add an entry
        self.history_manager.add_entry(
            model='test-model',
            prompt='test prompt',
            result='test result',
            duration=1.0,
            success=True
        )
        
        # Create a new history manager instance with same file
        new_manager = HistoryManager(
            history_file=self.test_history_file,
            max_entries=3
        )
        
        # Load history with new instance
        history = new_manager.load_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['model'], 'test-model')

if __name__ == '__main__':
    unittest.main()
