import os
import pytest
import json
from flask import session
from app import app, DEBUG_LEVELS

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

def test_debug_level_static():
    """Test debug level constants and validation"""
    # Test DEBUG_LEVELS constant
    assert isinstance(DEBUG_LEVELS, list), "DEBUG_LEVELS should be a list"
    assert len(DEBUG_LEVELS) > 0, "DEBUG_LEVELS should not be empty"
    assert all(isinstance(level, str) for level in DEBUG_LEVELS), "All debug levels should be strings"
    assert all(level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'] for level in DEBUG_LEVELS), "Invalid debug levels"

def test_debug_level_route(client):
    """Test debug level route functionality"""
    # Test setting valid debug level
    for level in DEBUG_LEVELS:
        response = client.post('/debug_level', data={'level': level})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['current_debug_level'] == level

    # Test invalid debug level
    response = client.post('/debug_level', data={'level': 'INVALID'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'

    # Test missing debug level
    response = client.post('/debug_level', data={})
    assert response.status_code == 200  # Should use default 'INFO'
    data = json.loads(response.data)
    assert data['current_debug_level'] == 'INFO'

def test_debug_level_session(client):
    """Test debug level session handling"""
    # Set debug level
    client.post('/debug_level', data={'level': 'DEBUG'})
    
    # Check if debug level persists
    response = client.get('/')
    assert response.status_code == 200
    assert b'Debug Level: DEBUG' in response.data

def test_home_page_debug_dropdown(client):
    """Test debug level dropdown in home page"""
    response = client.get('/')
    assert response.status_code == 200
    
    # Check for debug button
    assert b'id="debugButton"' in response.data
    assert b'Debug Level:' in response.data
    
    # Check for debug dropdown
    assert b'id="debugDropdown"' in response.data
    
    # Check for all debug levels in dropdown
    for level in DEBUG_LEVELS:
        assert level.encode() in response.data

def test_debug_level_javascript():
    """Test debug level JavaScript functions"""
    # Read the template file
    template_path = os.path.join(app.root_path, 'templates', 'index.html')
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Check for required JavaScript functions
    required_functions = [
        'toggleDebugDropdown',
        'setDebugLevel',
    ]
    for func in required_functions:
        assert f'function {func}' in template_content, f"Missing JavaScript function: {func}"
    
    # Check for event listeners
    assert 'addEventListener' in template_content
    assert "document.querySelectorAll('[data-debug-level]')" in template_content

def test_online_debug_level(client):
    """Test debug level functionality with live server"""
    # Set debug level
    response = client.post('/debug_level', data={'level': 'DEBUG'})
    assert response.status_code == 200
    
    # Make a request that should generate debug logs
    client.get('/')
    
    # Set different levels and verify logging behavior
    for level in DEBUG_LEVELS:
        response = client.post('/debug_level', data={'level': level})
        assert response.status_code == 200
        
        # Make a request that generates logs
        client.get('/')
        
        # TODO: Add log file checks here once logging to file is implemented

def test_prompt_suggestions_static():
    """Test prompt suggestions structure"""
    # Read the template file
    template_path = os.path.join(app.root_path, 'templates', 'index.html')
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Check for prompt dropdown elements
    assert 'id="promptDropdownButton"' in template_content
    assert 'id="promptDropdown"' in template_content
    
    # Check for prompt JavaScript functions
    required_functions = [
        'toggleDropdown',
        'updatePromptDropdown',
        'setPrompt',
    ]
    for func in required_functions:
        assert f'function {func}' in template_content, f"Missing JavaScript function: {func}"

def test_prompt_suggestions_route(client):
    """Test prompt suggestions functionality"""
    # Get home page
    response = client.get('/')
    assert response.status_code == 200
    
    # Check for prompt suggestions in response
    assert b'promptSuggestions' in response.data
    assert b'defaultPrompt' in response.data
    
    # Test model selection with prompt update
    response = client.post('/select_model', data={'model': 'llama2'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'prompt_suggestions' in data
    assert 'default_prompt' in data

def test_model_type_detection():
    """Test model type detection for prompts"""
    from app import VISION_MODELS, is_vision_model
    
    # Test vision models
    for model in VISION_MODELS:
        assert is_vision_model(model), f"{model} should be detected as vision model"
    
    # Test non-vision models
    assert not is_vision_model('llama2'), "llama2 should not be detected as vision model"
    assert not is_vision_model('mistral'), "mistral should not be detected as vision model"

def test_error_handling(client):
    """Test error handling for debug and prompt functionality"""
    # Test invalid debug level format
    response = client.post('/debug_level', data={'level': '123'})
    assert response.status_code == 400
    
    # Test missing model in selection
    response = client.post('/select_model', data={})
    assert response.status_code == 400
    
    # Test invalid model name
    response = client.post('/select_model', data={'model': 'nonexistent'})
    assert response.status_code == 200  # Should handle gracefully
    
    # Test prompt suggestions with invalid model type
    with client.session_transaction() as session:
        client.post('/select_model', data={'model': 'invalid_model'})
        response = client.get('/')
        assert response.status_code == 200  # Should handle gracefully
