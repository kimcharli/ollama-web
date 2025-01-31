import os
import json
import unittest
from app import app, VISION_MODELS
from config import Config

class TestPrompts(unittest.TestCase):
    def setUp(self):
        """Set up test client and test prompts"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.client = app.test_client()
        
        # Create test prompts
        self.test_prompts = {
            "vision_models": {
                "default": "Test vision prompt",
                "suggestions": [
                    "Test vision prompt 1",
                    "Test vision prompt 2",
                    "A very long vision prompt that should be truncated in the display but still fully accessible"
                ]
            },
            "text_models": {
                "default": "Test text prompt",
                "suggestions": [
                    "Test text prompt 1",
                    "Test text prompt 2",
                    "A very long text prompt that should be truncated in the display but still fully accessible"
                ]
            }
        }
        
        # Update app config to use test prompts
        app.config['PROMPTS'] = self.test_prompts
    
    def tearDown(self):
        """Clean up test files"""
        if 'test_prompts_file' in self.__dict__:
            if os.path.exists(self.test_prompts_file):
                os.remove(self.test_prompts_file)
    
    def test_initial_page_load(self):
        """Test initial page load without any session data"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode()
        
        # Check model selector exists
        self.assertIn('id="model"', html)
        self.assertIn('select', html.lower())
        
        # Check prompt input exists
        self.assertIn('id="prompt"', html)
        self.assertIn('textarea', html.lower())
        
        # Check dropdown button exists
        self.assertIn('id="promptDropdownButton"', html)
        self.assertIn('Suggested Prompts', html)
        
        # Check JavaScript initialization
        self.assertIn('let defaultPrompt =', html)
        self.assertIn('let promptSuggestions =', html)
        self.assertIn('let prompts =', html)
        self.assertIn('updatePromptDropdown()', html)
    
    def test_model_selection_functionality(self):
        """Test complete model selection flow"""
        # First try without a model (should get default)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # Select a vision model
        vision_model = 'llava'
        response = self.client.post('/select_model',
                                data={'model': vision_model})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Check response data
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['model'], vision_model)
        self.assertEqual(data['default_prompt'], self.test_prompts['vision_models']['default'])
        self.assertEqual(data['prompt_suggestions'], self.test_prompts['vision_models']['suggestions'])

        # Get page and verify vision prompts
        with self.client.session_transaction() as session:
            session['selected_model'] = vision_model
        
        response = self.client.get('/')
        html = response.data.decode()
        self.assertIn(self.test_prompts['vision_models']['default'], html)

        # Select a text model
        text_model = 'mistral'
        response = self.client.post('/select_model',
                                  data={'model': text_model})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Check response data
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['model'], text_model)
        self.assertEqual(data['default_prompt'], self.test_prompts['text_models']['default'])
        self.assertEqual(data['prompt_suggestions'], self.test_prompts['text_models']['suggestions'])

        # Get page and verify text prompts
        with self.client.session_transaction() as session:
            session['selected_model'] = text_model
        
        response = self.client.get('/')
        html = response.data.decode()
        self.assertIn(self.test_prompts['text_models']['default'], html)
        for suggestion in self.test_prompts['text_models']['suggestions']:
            self.assertIn(suggestion, html)
    
    def test_model_type_detection(self):
        """Test that model types are correctly detected"""
        # Test vision model
        response = self.client.post('/select_model',
                                  data={'model': 'llava'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['default_prompt'], self.test_prompts['vision_models']['default'])
        
        # Test text model
        response = self.client.post('/select_model',
                                  data={'model': 'mistral'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['default_prompt'], self.test_prompts['text_models']['default'])
    
    def test_invalid_model_selection(self):
        """Test handling of invalid model selection"""
        # Test with missing model
        response = self.client.post('/select_model', data={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        
        # Test with invalid model name
        response = self.client.post('/select_model',
                                  data={'model': 'invalid_model'})
        self.assertEqual(response.status_code, 200)  # Should still work but use text model type
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['default_prompt'], self.test_prompts['text_models']['default'])
    
    def test_prompt_suggestions_dropdown(self):
        """Test prompt suggestions dropdown functionality"""
        # Set a default model
        with self.client.session_transaction() as session:
            session['selected_model'] = 'test-model'
        
        # Get page
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode()

        # Check for prompt dropdown elements
        self.assertIn('id="promptDropdownButton"', html)
        self.assertIn('id="promptDropdown"', html)

        # Check that default prompt and suggestions are passed to JavaScript
        self.assertIn('let defaultPrompt = "' + self.test_prompts['text_models']['default'] + '"', html)
        self.assertIn('let promptSuggestions = ' + json.dumps(self.test_prompts['text_models']['suggestions']), html)

if __name__ == '__main__':
    unittest.main()
