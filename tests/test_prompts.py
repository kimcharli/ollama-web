import os
import json
import unittest
import pytest
from app import app, VISION_MODELS, history_manager
from config import Config
from unittest.mock import patch

@pytest.mark.unit
class TestPrompts(unittest.TestCase):
    """Test suite for prompt-related functionality."""
    
    def setUp(self):
        """Set up test client and test data."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # Load test prompts from prompts.json
        with open('prompts.json') as f:
            prompts = json.load(f)
            
        # Map prompts to vision/text for easier testing
        self.test_prompts = {
            'vision_models': prompts['vision_models'],
            'text_models': prompts['text_models']
        }
    
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
        # Mock history manager to return empty history
        with patch.object(history_manager, 'load_history', return_value=[]):
            # Select a model
            test_model = 'tinyllama'
            response = self.client.post('/select_model',
                                    data={'model': test_model})
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)

            # Check response data
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['model'], test_model)
            
            # Verify all prompts are included
            all_expected_prompts = (
                self.test_prompts['vision_models']['suggestions'] +
                self.test_prompts['text_models']['suggestions']
            )
            for prompt in all_expected_prompts:
                self.assertIn(prompt, data['prompt_suggestions'])
            
            # Get page and verify prompts
            with self.client.session_transaction() as session:
                session['selected_model'] = test_model
            
            response = self.client.get('/')
            html = response.data.decode()
            for prompt in all_expected_prompts:
                self.assertIn(prompt, html)
    
    def test_model_type_detection(self):
        """Test that model types are correctly detected and all prompts are included"""
        # Test with vision model
        response = self.client.post('/select_model',
                                  data={'model': 'llava'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should always use text model default prompt
        self.assertEqual(data['default_prompt'], self.test_prompts['text_models']['default'])
        
        # Should include all prompts from both model types
        all_expected_prompts = (
            self.test_prompts['vision_models']['suggestions'] +
            self.test_prompts['text_models']['suggestions']
        )
        for prompt in all_expected_prompts:
            self.assertIn(prompt, data['prompt_suggestions'])
        
        # Test with text model - should behave the same
        response = self.client.post('/select_model',
                                  data={'model': 'mistral'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should use text model default prompt
        self.assertEqual(data['default_prompt'], self.test_prompts['text_models']['default'])
        
        # Should include all prompts
        for prompt in all_expected_prompts:
            self.assertIn(prompt, data['prompt_suggestions'])
    
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
        # Mock history manager to return empty history
        with patch.object(history_manager, 'load_history', return_value=[]):
            # Set a model
            test_model = 'tinyllama'
            with self.client.session_transaction() as session:
                session['selected_model'] = test_model
            
            # Get page
            response = self.client.get('/')
            self.assertEqual(response.status_code, 200)
            html = response.data.decode()
            
            # Check for prompt dropdown
            self.assertIn('id="promptDropdownButton"', html)
            self.assertIn('id="promptDropdown"', html)
            
            # Check for all prompts from both vision and text models
            for model_type in ['vision_models', 'text_models']:
                for suggestion in self.test_prompts[model_type]['suggestions']:
                    self.assertIn(suggestion, html)
                    
            # Check JavaScript initialization
            self.assertIn('let promptSuggestions =', html)
            
            # Find the promptSuggestions array in JavaScript
            import re
            match = re.search(r'let promptSuggestions = (\[.*?\]);', html, re.DOTALL)
            self.assertIsNotNone(match, "Could not find promptSuggestions in HTML")
            
            suggestions_str = match.group(1)
            suggestions = json.loads(suggestions_str)
            self.assertTrue(len(suggestions) > 0, "Prompt suggestions array is empty")
            
            # Verify that suggestions contain prompts from both model types
            all_expected_prompts = (
                self.test_prompts['vision_models']['suggestions'] +
                self.test_prompts['text_models']['suggestions']
            )
            for prompt in all_expected_prompts:
                self.assertIn(prompt, suggestions)
    
    def test_history_prompts(self):
        """Test that history prompts are included in suggestions"""
        # Create some test history
        history = [
            {'prompt': 'History prompt 1', 'model': 'test-model', 'duration': 1.0},
            {'prompt': 'History prompt 2', 'model': 'test-model', 'duration': 1.0},
            {'prompt': 'History prompt 3', 'model': 'test-model', 'duration': 1.0},
            {'prompt': 'History prompt 4', 'model': 'test-model', 'duration': 1.0},  # Should not be included due to limit
        ]

        # Create test prompts
        test_prompts = {
            'vision_models': {
                'default': 'Test vision prompt',
                'suggestions': ['Test vision prompt']
            },
            'text_models': {
                'default': 'Test text prompt',
                'suggestions': ['Test text prompt']
            }
        }

        # Mock both history_manager and PROMPTS
        with patch.object(history_manager, 'load_history', return_value=history), \
             patch('app.PROMPTS', test_prompts):
            # Set environment variable for history limit
            with patch.dict('os.environ', {'HISTORY_PROMPT_LIMIT': '3'}):
                # Set a default model
                with self.client.session_transaction() as session:
                    session['selected_model'] = 'test-model'

                # Get page
                response = self.client.get('/')
                self.assertEqual(response.status_code, 200)
                html = response.data.decode()

                # Find the promptSuggestions array in JavaScript
                import re
                match = re.search(r'let promptSuggestions = (\[.*?\]);', html, re.DOTALL)
                self.assertIsNotNone(match, "Could not find promptSuggestions in HTML")

                suggestions_str = match.group(1)
                suggestions = json.loads(suggestions_str)

                # Check that first 3 history prompts are included
                for i in range(1, 4):
                    self.assertIn(f'History prompt {i}', suggestions)

                # Check that the 4th prompt is not included in suggestions
                self.assertNotIn('History prompt 4', suggestions)

@pytest.mark.integration
class TestPromptsLive(unittest.TestCase):
    """Integration tests for prompt functionality with live server."""
    
    @classmethod
    def setUpClass(cls):
        """Start the Flask server for testing."""
        import subprocess
        import time
        import requests
        import os

        # Get port from environment variable
        port = os.getenv('FLASK_PORT', '5001')
        
        # Start the server
        cls.server_process = subprocess.Popen(['uv', 'run', 'app.py'],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(2)
        
        # Check if server is running
        try:
            response = requests.get(f'http://localhost:{port}')
            if response.status_code != 200:
                raise Exception(f"Server returned status code {response.status_code}")
        except Exception as e:
            cls.server_process.terminate()
            raise Exception(f"Could not connect to server: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Stop the Flask server."""
        cls.server_process.terminate()
        cls.server_process.wait()
    
    def setUp(self):
        """Load test prompts."""
        with open('prompts.json') as f:
            prompts = json.load(f)
        self.test_prompts = prompts
    
    def test_live_prompts_loading(self):
        """Test that prompts are correctly loaded in live server."""
        import requests
        import os

        # Get port from environment variable
        port = os.getenv('FLASK_PORT', '5001')
        
        # Get the home page
        response = requests.get(f'http://localhost:{port}')
        self.assertEqual(response.status_code, 200)
        html = response.text
        
        # Check for prompt dropdown
        self.assertIn('id="promptDropdownButton"', html)
        self.assertIn('id="promptDropdown"', html)
        
        # Check that all prompts are included
        for model_type in ['vision_models', 'text_models']:
            for suggestion in self.test_prompts[model_type]['suggestions']:
                self.assertIn(suggestion, html)
    
    def test_live_model_selection(self):
        """Test model selection with live server."""
        import requests
        import os

        # Get port from environment variable
        port = os.getenv('FLASK_PORT', '5001')
        
        # Create session to maintain CSRF token
        session = requests.Session()
        
        # Get the home page first to set up session
        response = session.get(f'http://localhost:{port}')
        
        # Extract CSRF token from the response
        import re
        match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"[^>]*>', 
                         response.text)
        self.assertIsNotNone(match, "Could not find CSRF token in page")
        csrf_token = match.group(1)
        
        # Select a model
        response = session.post(f'http://localhost:{port}/select_model',
                              data={'model': 'llava',
                                   'csrf_token': csrf_token})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response
        self.assertEqual(data['status'], 'success')
        
        # Check that all prompts are included
        all_prompts = (self.test_prompts['vision_models']['suggestions'] +
                      self.test_prompts['text_models']['suggestions'])
        for prompt in all_prompts:
            self.assertIn(prompt, data['prompt_suggestions'])
    
    def test_live_dropdown_functionality(self):
        """Test dropdown functionality with live server."""
        import requests
        import os
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        # Get port from environment variable
        port = os.getenv('FLASK_PORT', '5001')
        
        # Start Chrome in headless mode
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        
        try:
            # Load the page
            driver.get(f'http://localhost:{port}')
            
            # Wait for page to be ready
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Print initial JavaScript state
            js_state = driver.execute_script("""
                return {
                    defaultPrompt: window.defaultPrompt,
                    promptSuggestions: window.promptSuggestions,
                    prompts: window.prompts,
                    isDropdownOpen: window.isDropdownOpen
                };
            """)
            print("\nInitial JavaScript state:", js_state)
            
            # Wait for dropdown button
            dropdown_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "promptDropdownButton"))
            )
            
            # Print initial button state
            print("\nInitial button state:")
            print(f"Button text: {dropdown_button.text}")
            print(f"Button classes: {dropdown_button.get_attribute('class')}")
            
            # Wait for button event handler to be ready
            time.sleep(1)  # Give DOMContentLoaded event time to complete
            
            # Call toggleDropdown function directly
            driver.execute_script("""
                const event = { preventDefault: () => {}, stopPropagation: () => {} };
                toggleDropdown(event);
            """)
            
            # Print button state after click
            print("\nButton state after click:")
            print(f"Button text: {dropdown_button.text}")
            print(f"Button classes: {dropdown_button.get_attribute('class')}")
            
            # Wait for dropdown to appear
            dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "promptDropdown"))
            )
            
            # Print dropdown state
            print("\nDropdown state:")
            print(f"Dropdown classes: {dropdown.get_attribute('class')}")
            print(f"Dropdown style: {dropdown.get_attribute('style')}")
            print(f"Dropdown display: {dropdown.value_of_css_property('display')}")
            print(f"Dropdown HTML: {dropdown.get_attribute('innerHTML')}")
            
            # Print JavaScript state
            js_state = driver.execute_script("""
                return {
                    isDropdownOpen: window.isDropdownOpen,
                    buttonExpanded: document.getElementById('promptDropdownButton').getAttribute('aria-expanded'),
                    dropdownHidden: document.getElementById('promptDropdown').classList.contains('hidden'),
                    promptSuggestions: window.promptSuggestions
                };
            """)
            print("\nJavaScript state:", js_state)
            
            # Wait for dropdown to be visible
            def check_dropdown_visible(driver):
                dropdown = driver.find_element(By.ID, "promptDropdown")
                classes = dropdown.get_attribute('class').split()
                return 'hidden' not in classes
            
            WebDriverWait(driver, 10).until(check_dropdown_visible)
            
            # Check that all prompts are in the dropdown
            dropdown_html = dropdown.get_attribute('innerHTML')
            for model_type in ['vision_models', 'text_models']:
                for suggestion in self.test_prompts[model_type]['suggestions']:
                    self.assertIn(suggestion, dropdown_html)
        
        finally:
            driver.quit()
    
    def _get_csrf_token(self):
        """Get CSRF token from page."""
        import requests
        import os
        import re

        # Get port from environment variable
        port = os.getenv('FLASK_PORT', '5001')
        
        session = requests.Session()
        response = session.get(f'http://localhost:{port}')
        match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"[^>]*>', 
                         response.text)
        if not match:
            raise Exception("Could not find CSRF token in page")
        return match.group(1)

if __name__ == '__main__':
    unittest.main()
