import os
import pytest
import tempfile

@pytest.fixture
def app():
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture(autouse=True)
def clean_uploads(app):
    """Clean up uploaded files after each test"""
    yield
    upload_folder = app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        os.remove(os.path.join(upload_folder, filename))
