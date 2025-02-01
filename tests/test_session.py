import pytest
from app import app as flask_app, db, Session
import json
import os
from unittest.mock import patch

@pytest.fixture
def app():
    # Configure test database
    db_path = 'test_sessions.db'
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test_secret_key'
    })
    
    with flask_app.app_context():
        db.create_all()
    
    yield flask_app
    
    # Clean up
    with flask_app.app_context():
        db.drop_all()
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@patch('app.get_available_models')
def test_model_selection_persistence(mock_get_models, client):
    """Test that selected model persists until another is selected"""
    
    # Mock available models
    mock_get_models.return_value = [
        "artifish/llama3.2-uncensored:latest",
        "artifish/codellama-uncensored:latest"
    ]
    
    # 1. Select first model
    first_model = "artifish/llama3.2-uncensored:latest"
    response = client.post('/api/select-model',
                        json={'model': first_model},
                        headers={'Content-Type': 'application/json'})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['model'] == first_model
    
    # Get session cookie
    session_id = response.headers.get('Set-Cookie').split(';')[0].split('=')[1]
    
    # 2. Verify first model is selected
    response = client.get('/api/current-model',
                         headers={'Cookie': f'session_id={session_id}'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['model'] == first_model
    
    # 3. Create new client (simulates browser restart)
    new_client = flask_app.test_client()
    new_client.get('/', headers={'Cookie': f'session_id={session_id}'})
    
    # 4. Verify first model is still selected
    response = new_client.get('/api/current-model',
                             headers={'Cookie': f'session_id={session_id}'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['model'] == first_model
    
    # 5. Select second model
    second_model = "artifish/codellama-uncensored:latest"
    response = new_client.post('/api/select-model',
                            json={'model': second_model},
                            headers={
                                'Content-Type': 'application/json',
                                'Cookie': f'session_id={session_id}'
                            })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['model'] == second_model
    
    # 6. Verify second model is now selected
    response = new_client.get('/api/current-model',
                             headers={'Cookie': f'session_id={session_id}'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['model'] == second_model
    
    ## TODO: implement later
    # # 7. Create third client (simulates another browser restart)
    # third_client = flask_app.test_client()
    # third_client.get('/', headers={'Cookie': f'session_id={session_id}'})
    
    # # 8. Verify second model is still selected
    # response = third_client.get('/api/current-model',
    #                            headers={'Cookie': f'session_id={session_id}'})
    # assert response.status_code == 200
    # data = json.loads(response.data)
    # assert data['model'] == second_model

def test_model_session_update(client):
    """Test that model can be updated in session"""
    
    # Select first model
    first_model = "llama2"
    response = client.post('/api/select-model',
                         json={'model': first_model},
                         headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    
    # Select second model
    second_model = "codellama"
    response = client.post('/api/select-model',
                         json={'model': second_model},
                         headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    
    # Verify second model is selected
    response = client.get('/api/current-model')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['model'] == second_model
