import os
import json
import unittest
from config import Config
from flask import Flask

class TestConfig(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.test_prompts = {
            "vision_models": {
                "default": "Test vision prompt",
                "suggestions": ["Test vision prompt"]
            },
            "text_models": {
                "default": "Test text prompt",
                "suggestions": ["Test text prompt"]
            }
        }
        
        # Create test prompts file
        self.test_prompts_file = 'test_prompts.json'
        with open(self.test_prompts_file, 'w') as f:
            json.dump(self.test_prompts, f)
        
        # Create test app
        self.app = Flask(__name__)
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_prompts_file):
            os.remove(self.test_prompts_file)
    
    def test_load_prompts(self):
        """Test loading prompts from file"""
        # Set prompts file in environment
        os.environ['PROMPTS_FILE'] = self.test_prompts_file
        
        # Reload config
        prompts = Config.load_prompts()
        
        # Check prompts
        self.assertEqual(prompts['vision_models']['default'], 'Test vision prompt')
        self.assertEqual(prompts['text_models']['default'], 'Test text prompt')
    
    def test_init_app(self):
        """Test initializing app with config"""
        # Set test environment variables
        os.environ['FLASK_SECRET_KEY'] = 'test-key'
        os.environ['PROMPTS_FILE'] = self.test_prompts_file
        
        # Initialize app with config
        Config.init_app(self.app)
        
        # Check config values
        self.assertEqual(self.app.config['SECRET_KEY'], 'test-key')
        self.assertEqual(self.app.config['PROMPTS']['vision_models']['default'], 'Test vision prompt')
        self.assertEqual(self.app.config['PROMPTS']['text_models']['default'], 'Test text prompt')

if __name__ == '__main__':
    unittest.main()
