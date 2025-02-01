import unittest
import json
from unittest.mock import patch, MagicMock
from app import app
from fetch_manager import FetchManager

class TestModelManager(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        self.fetch_manager = FetchManager()

    def test_fetch_models_list(self):
        # Mock subprocess.run to simulate ollama list output
        mock_output = """
NAME                    ID              SIZE     MODIFIED
llama2                 abcd1234        4.0 GB   2 weeks ago
mistral                efgh5678        3.0 GB   2 weeks ago
"""
        with patch('subprocess.run') as mock_run:
            # Configure mock
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_output
            mock_run.return_value.stderr = ""
            
            # Test /fetch/models endpoint
            response = self.client.post('/fetch/models')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertIn('models', data)
            self.assertEqual(len(data['models']), 2)
            
            # Verify model structure
            model = data['models'][0]
            self.assertIn('name', model)
            self.assertIn('model', model)
            self.assertIn('modified_at', model)
            self.assertIn('size', model)

    def test_library_models(self):
        response = self.client.get('/library/models')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('models', data)
        self.assertTrue(len(data['models']) > 0)
        
        # Verify model structure
        model = data['models'][0]
        self.assertIn('name', model)
        self.assertIn('description', model)

    def test_current_model(self):
        # Test getting current model when none selected
        response = self.client.get('/api/current-model')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('model', data)
        
        # Test selecting a model
        test_model = "llama2"
        response = self.client.post('/api/select-model',
                                  json={'model': test_model})
        self.assertEqual(response.status_code, 200)
        
        # Verify selected model is returned
        response = self.client.get('/api/current-model')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['model'], test_model)

    def test_pull_model(self):
        test_model = "llama2"
        mock_progress = [
            {'status': 'downloading', 'completed': 1000000, 'total': 4000000000},
            {'status': 'downloading', 'completed': 2000000, 'total': 4000000000},
            {'status': 'complete'}
        ]
        
        with patch('requests.post') as mock_post:
            # Configure mock to return progress events
            mock_response = MagicMock()
            mock_response.iter_lines.return_value = [
                json.dumps(progress).encode() for progress in mock_progress
            ]
            mock_post.return_value = mock_response
            mock_post.return_value.ok = True
            
            # Test pull model endpoint
            response = self.client.post('/pull/model',
                                      json={'name': test_model})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content_type.startswith('text/event-stream'))

if __name__ == '__main__':
    unittest.main()
