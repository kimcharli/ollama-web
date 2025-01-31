import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Application configuration class"""
    
    # Flask Configuration
    SECRET_KEY = None
    DEBUG = None
    PORT = None
    
    # File Storage Configuration
    UPLOAD_FOLDER = None
    HISTORY_FILE = None
    MAX_HISTORY_ENTRIES = None
    
    # Ollama Configuration
    OLLAMA_HOST = None
    
    # Prompts Configuration
    PROMPTS_FILE = None
    
    @classmethod
    def load_prompts(cls):
        """Load prompts from the prompts file"""
        try:
            prompts_file = cls.PROMPTS_FILE or os.getenv('PROMPTS_FILE', 'prompts.json')
            if os.path.exists(prompts_file):
                with open(prompts_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading prompts: {e}")
        
        # Return default prompts if file cannot be loaded
        return {
            "vision_models": {
                "default": "What do you see in this image?",
                "suggestions": ["What do you see in this image?"]
            },
            "text_models": {
                "default": "Please analyze this text:",
                "suggestions": ["Please analyze this text:"]
            }
        }
    
    @classmethod
    def init_app(cls, app):
        """Initialize application configuration"""
        # Set configuration values from environment or use defaults
        cls.SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
        cls.DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
        cls.PORT = int(os.getenv('FLASK_PORT', '5001'))
        cls.UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
        cls.HISTORY_FILE = os.getenv('HISTORY_FILE', 'query_history.json')
        cls.MAX_HISTORY_ENTRIES = int(os.getenv('MAX_HISTORY_ENTRIES', '100'))
        cls.OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        cls.PROMPTS_FILE = os.getenv('PROMPTS_FILE', 'prompts.json')
        
        # Set Flask configuration
        app.config['SECRET_KEY'] = cls.SECRET_KEY
        app.config['DEBUG'] = cls.DEBUG
        app.config['UPLOAD_FOLDER'] = cls.UPLOAD_FOLDER
        app.config['HISTORY_FILE'] = cls.HISTORY_FILE
        app.config['MAX_HISTORY_ENTRIES'] = cls.MAX_HISTORY_ENTRIES
        app.config['OLLAMA_HOST'] = cls.OLLAMA_HOST
        
        # Load prompts into app config
        app.config['PROMPTS'] = cls.load_prompts()
        
        # Create upload folder if it doesn't exist
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
