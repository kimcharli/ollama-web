import os
import json
import io
import pytest
from unittest.mock import patch, MagicMock
from app import app, DEBUG_LEVELS

@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_requests():
    """Mock requests module for testing."""
    with patch('requests.post') as mock_post:
        yield mock_post

@pytest.fixture
def mock_history():
    """Mock history manager"""
    history = []
    mock_manager = MagicMock()
    mock_manager.load_history.return_value = history
    mock_manager.add_entry = lambda **kwargs: history.append(kwargs) or history
    with patch('app.history_manager', mock_manager):
        yield mock_manager, history

def test_debug_level_static():
    """Test debug level constants and validation"""
    # Test DEBUG_LEVELS constant
    assert isinstance(DEBUG_LEVELS, list), "DEBUG_LEVELS should be a list"
    assert len(DEBUG_LEVELS) > 0, "DEBUG_LEVELS should not be empty"
    assert all(isinstance(level, str) for level in DEBUG_LEVELS), "All debug levels should be strings"
    assert all(level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] for level in DEBUG_LEVELS), "Invalid debug levels"

def test_analyze_with_text_prompt(client, mock_requests, mock_history):
    """Test analyze endpoint with a text prompt"""
    mock_manager, history = mock_history
    model = os.getenv('TEST_MODEL', 'tinyllama')
    prompt = os.getenv('TEST_PROMPT', 'What is the capital of France?')

    # Mock Ollama API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        json.dumps({'response': 'The capital of France is Paris.'}).encode()
    ]
    mock_requests.return_value = mock_response

    # Make sure model is available
    response = client.get('/')
    assert response.status_code == 200

    # Set the model in session
    with client.session_transaction() as session:
        session['selected_model'] = model

    # Send analyze request
    response = client.post('/analyze', data={
        'model': model,
        'prompt': prompt
    })
    assert response.status_code == 200

    # Check that we got a response
    html = response.data.decode()
    assert 'Response (took' in html
    assert 'Error from Ollama API' not in html  # No API error
    assert 'Error (after' not in html  # No general error
    assert 'The capital of France is Paris.' in html  # Response should be in the output

    # Check that history was updated
    assert len(history) == 1
    latest = history[0]
    assert latest['model'] == model
    assert latest['prompt'] == prompt
    assert latest['success'] is True
    assert 'duration' in latest
    assert isinstance(latest['duration'], (int, float))
    assert latest['duration'] > 0

def test_analyze_with_vision_model(client, mock_requests, mock_history):
    """Test analyze endpoint with a vision model"""
    mock_manager, history = mock_history
    model = 'llava'  # Vision model
    prompt = 'What do you see in this image?'

    # Create a test image
    image_data = b'fake image data'
    image = io.BytesIO(image_data)
    image.filename = 'test.jpg'

    # Mock Ollama API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        json.dumps({
            'message': {
                'role': 'assistant',
                'content': 'I see a test image.',
            }
        }).encode()
    ]
    mock_requests.return_value = mock_response

    # Make sure model is available
    response = client.get('/')
    assert response.status_code == 200

    # Set the model in session
    with client.session_transaction() as session:
        session['selected_model'] = model

    # Send analyze request with image
    response = client.post('/analyze', data={
        'model': model,
        'prompt': prompt,
        'file': (image, 'test.jpg')
    })
    assert response.status_code == 200

    # Check that we got a response
    html = response.data.decode()
    assert 'Response (took' in html
    assert 'Error from Ollama API' not in html  # No API error
    assert 'Error (after' not in html  # No general error
    assert 'I see a test image.' in html  # Response should be in the output

    # Check that history was updated
    assert len(history) == 1
    latest = history[0]
    assert latest['model'] == model
    assert latest['prompt'] == prompt
    assert latest['success'] is True
    assert 'duration' in latest
    assert isinstance(latest['duration'], (int, float))
    assert latest['duration'] > 0

    # Verify API call
    mock_requests.assert_called_once()
    call_args = mock_requests.call_args
    assert call_args is not None

    # Check URL
    url = call_args[0][0]
    assert url.endswith('/api/chat')  # Vision models use chat endpoint

    # Check request data
    json_data = call_args[1]['json']
    assert json_data['model'] == model
    assert len(json_data['messages']) == 1
    assert json_data['messages'][0]['role'] == 'user'
    assert 'images' in json_data['messages'][0]
    assert len(json_data['messages'][0]['images']) == 1  # Should have one base64 image

def test_suggested_prompts_after_analyze(client, mock_requests, mock_history):
    """Test that suggested prompts are maintained after analysis"""
    mock_manager, history = mock_history
    model = 'llava'  # Use a vision model to test suggestions
    prompt = 'What do you see in this image?'

    # Mock Ollama API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        json.dumps({
            'message': {
                'role': 'assistant',
                'content': 'I see a test image.',
            }
        }).encode()
    ]
    mock_requests.return_value = mock_response

    # Make sure model is available and get initial suggestions
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode()

    # Verify initial suggestions are present
    assert 'What do you see in this image?' in html
    assert 'Describe this image in detail' in html

    # Set the model in session
    with client.session_transaction() as session:
        session['selected_model'] = model

    # Create a test image
    image_data = b'fake image data'
    image = io.BytesIO(image_data)
    image.filename = 'test.jpg'

    # Send analyze request with image
    response = client.post('/analyze', data={
        'model': model,
        'prompt': prompt,
        'file': (image, 'test.jpg')
    })
    assert response.status_code == 200

    # Check suggestions in analyze response
    html = response.data.decode()
    assert 'What do you see in this image?' in html
    assert 'Describe this image in detail' in html
    assert 'What objects are present in this image?' in html
    assert 'Analyze the composition of this image' in html
    assert 'What is the main subject of this image?' in html

    # Get the homepage again
    response = client.get('/')
    assert response.status_code == 200
    html = response.data.decode()

    # Verify suggestions are still present
    assert 'What do you see in this image?' in html
    assert 'Describe this image in detail' in html
    assert 'What objects are present in this image?' in html
    assert 'Analyze the composition of this image' in html
    assert 'What is the main subject of this image?' in html

    # Also check that our used prompt is in history prompts
    assert prompt in html  # The used prompt should appear in history suggestions

def test_abort_without_active_request(client):
    """Test aborting when there's no active request"""
    response = client.post('/abort')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'No active request to abort' in data['message']

def test_abort_with_active_request(client, mock_requests, mock_history):
    """Test aborting an active request"""
    mock_manager, history = mock_history
    model = 'llama2'
    prompt = 'Tell me a long story'

    # Create a mock response that simulates a long-running request
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.side_effect = lambda: iter([])  # Never yield any lines
    mock_response.close = MagicMock()  # Add close method
    mock_requests.return_value = mock_response

    # Set up session
    with client.session_transaction() as session:
        session['selected_model'] = model

    # Mock active_requests to simulate a running request
    with patch('app.active_requests') as mock_active_requests:
        mock_active_requests.__iter__.return_value = ['fake_request_id']
        mock_active_requests.pop.return_value = mock_response

        # Now abort the request
        response = client.post('/abort')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'Analysis aborted' in data['message']

        # Verify that the request was closed
        assert mock_response.close.call_count == 1

def test_analyze_with_streaming_response(client, mock_requests, mock_history):
    """Test analyze endpoint with streaming response"""
    mock_manager, history = mock_history
    model = 'llama2'
    prompt = 'Tell me a story'

    # Mock streaming response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        json.dumps({'response': 'Once'}).encode(),
        json.dumps({'response': ' upon'}).encode(),
        json.dumps({'response': ' a'}).encode(),
        json.dumps({'response': ' time'}).encode()
    ]
    mock_requests.return_value = mock_response

    # Make request
    with client.session_transaction() as session:
        session['selected_model'] = model

    response = client.post('/analyze', data={
        'model': model,
        'prompt': prompt
    })

    # Check response
    assert response.status_code == 200
    html = response.data.decode()
    assert 'Response (took' in html
    assert 'Error from Ollama API' not in html  # No API error
    assert 'Error (after' not in html  # No general error
    assert 'Once upon a time' in html

    # Verify streaming was enabled
    assert mock_requests.call_args[1]['stream'] is True
