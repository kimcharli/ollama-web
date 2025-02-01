import os
import secrets
import logging
import requests
import base64
import time
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response, session
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from prompt_manager import PromptManager
from config import Config
from history_manager import HistoryManager
from fetch_manager import FetchManager
from model_manager import ModelManager

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s    %(name)s:%(filename)s:%(lineno)d %(message)s'))
logger.addHandler(handler)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Ensure secret key is set
if not app.secret_key:
    app.secret_key = 'dev-secret-key-change-in-production'  # For development only

# Initialize SQLAlchemy for sessions
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sessions.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Session model
class Session(db.Model):
    id = db.Column(db.String(256), primary_key=True)
    data = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_or_create(cls, session_id=None):
        if not session_id:
            session_id = secrets.token_hex(32)
        sess = cls.query.get(session_id)
        if not sess:
            sess = cls(id=session_id)
            db.session.add(sess)
            db.session.commit()
        return sess, session_id

    def set_data(self, data):
        self.data = data
        self.updated_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def get_data(self):
        return self.data

# Create tables
with app.app_context():
    db.create_all()

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize fetch manager
fetch_manager = FetchManager()

# Initialize model manager
model_manager = ModelManager()

# Session handling routes
@app.route('/api/select-model', methods=['POST'])
def api_select_model():
    """Select a model and store in session."""
    try:
        data = request.get_json()
        model = data.get('model')
        if not model:
            return jsonify({'status': 'error', 'message': 'No model specified'}), 400
        
        # Store selected model in session
        session_id = request.cookies.get('session_id')
        if session_id:
            sess, _ = Session.get_or_create(session_id)
            sess.set_data(model)
        
        return jsonify({
            'status': 'success',
            'model': model
        })
    except Exception as e:
        logger.error(f'Error in api_select_model: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/current-model', methods=['GET'])
def get_current_model():
    """Get currently selected model from session."""
    try:
        session_id = request.cookies.get('session_id')
        if session_id:
            sess = Session.query.get(session_id)
            if sess:
                model = sess.get_data()
                logger.info(f"Getting current model from session: {model}")
                return jsonify({'model': model})
        return jsonify({'model': None})
    except Exception as e:
        logger.error(f"Error getting current model: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pull-model', methods=['POST'])
@csrf.exempt
def pull_model():
    """Pull a model from Ollama library."""
    try:
        data = request.get_json()
        if not data or 'model' not in data:
            return jsonify({'error': 'No model specified'}), 400

        model_name = data['model']
        logger.info(f"Starting model pull for {model_name}")

        def generate():
            # Send request to Ollama pull endpoint
            response = requests.post(
                f"{Config.OLLAMA_HOST}/api/pull",
                json={"name": model_name},
                stream=True
            )
            
            for line in response.iter_lines():
                if line:
                    try:
                        progress_data = json.loads(line)
                        # Calculate progress percentage
                        if 'total' in progress_data and progress_data['total'] > 0:
                            completed = progress_data.get('completed', 0)
                            total = progress_data['total']
                            progress = int((completed / total) * 100)
                            progress_data['progress'] = progress
                            
                            # Convert bytes to MB for display
                            progress_data['completed_mb'] = round(completed / 1024 / 1024, 1)
                            progress_data['total_mb'] = round(total / 1024 / 1024, 1)
                        
                        # Send progress update
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        
                        if progress_data.get('status') == 'success':
                            logger.info(f"Successfully pulled model {model_name}")
                            yield f"data: {json.dumps({'status': 'done', 'progress': 100})}\n\n"
                            break
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing progress data: {e}")
                        continue

        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        logger.error(f"Error in pull_model: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ollama-status')
def check_ollama_status():
    """Check if Ollama is running."""
    try:
        response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=2)
        return jsonify({'running': response.ok})
    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}")
        return jsonify({'running': False})

@app.route('/api/models')
def get_models_api():
    """Get list of available models."""
    try:
        models = get_available_models()
        return jsonify({'models': models})
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/library-models')
def get_library_models():
    """Get list of available models from Ollama library."""
    try:
        # Common models that are available in Ollama
        common_models = [
            {
                'name': 'llama2',
                'description': 'Meta\'s Llama 2 LLM, fine-tuned for chat'
            },
            {
                'name': 'llama2:13b',
                'description': 'Meta\'s Llama 2 13B parameter variant'
            },
            {
                'name': 'llama2:70b',
                'description': 'Meta\'s Llama 2 70B parameter variant'
            },
            {
                'name': 'codellama',
                'description': 'Meta\'s Llama 2 model optimized for code completion and generation'
            },
            {
                'name': 'mistral',
                'description': 'Mistral AI\'s 7B parameter model with strong performance'
            },
            {
                'name': 'mixtral',
                'description': 'Mistral AI\'s Mixture of Experts model'
            },
            {
                'name': 'dolphin-mixtral',
                'description': 'Mixtral fine-tuned by Ehartford'
            },
            {
                'name': 'neural-chat',
                'description': 'Intel\'s neural chat model'
            },
            {
                'name': 'starling-lm',
                'description': 'Starling LM model fine-tuned on conversation data'
            },
            {
                'name': 'openchat',
                'description': 'OpenChat\'s model fine-tuned for conversation'
            },
            {
                'name': 'phi',
                'description': 'Microsoft\'s Phi model'
            },
            {
                'name': 'orca-mini',
                'description': 'Small but capable model based on Orca architecture'
            }
        ]
        return jsonify({'models': common_models})
    except Exception as e:
        logger.error(f"Error getting library models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/fetch/models', methods=['POST'])
@csrf.exempt
def fetch_models():
    """Fetch list of available models."""
    try:
        models_data = fetch_manager.fetch_models_list()
        if models_data is None:
            return jsonify({'error': 'Failed to fetch models'}), 500
        logger.info(f"Returning models data: {models_data}")
        return jsonify(models_data)
    except Exception as e:
        logger.error(f"Error in fetch_models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
@csrf.exempt
def analyze():
    """Analyze text using selected model."""
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        if not data or 'prompt' not in data:
            return jsonify({'error': 'No prompt provided'}), 400

        # Get current model from session
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session found'}), 400
            
        sess = Session.query.get(session_id)
        if not sess:
            return jsonify({'error': 'No session found'}), 400
            
        model = sess.get_data()
        if not model:
            return jsonify({'error': 'No model selected'}), 400

        prompt = data['prompt']
        logger.info(f"Analyzing prompt with model {model}: {prompt}")

        response = requests.post(
            f"{Config.OLLAMA_HOST}/api/generate",
            json={
                'model': model,
                'prompt': prompt,
                'stream': False
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        return jsonify({
            'response': result.get('response', ''),
            'model': model
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama API: {e}")
        return jsonify({'error': 'Failed to connect to Ollama API'}), 500
    except Exception as e:
        logger.error(f"Error in analyze: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    models = get_available_models()
    history = history_manager.load_history()

    # Determine model type based on selected model
    model = request.args.get('model', models[0] if models else '')
    model_type = 'vision' if 'llava' in model else 'text'
    
    # Load prompts using PromptManager
    prompt_manager = PromptManager.load_prompts(model_type)
    
    return render_template('index.html',
                         models=models,
                         model=model,
                         history=history,
                         default_prompt=prompt_manager.get_default_prompt(),
                         prompt_suggestions=prompt_manager.get_prompt_suggestions(),
                         prompts=load_prompts())

# ... rest of the code remains the same ...

def get_available_models():
    """Get list of available models from Ollama API."""
    try:
        response = requests.get(f"{Config.OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            data = response.json()
            # Extract model names from the 'models' list, which contains objects with 'name' field
            return [model['name'] for model in data.get('models', [])]
        logger.error(f"Failed to get models: {response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return []

def load_prompts():
    """Load prompts from JSON file."""
    try:
        with open('prompts.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading prompts.json: {e}")
        return {
            'vision_models': {
                'default': 'What do you see in this image?',
                'suggestions': [
                    'What do you see in this image?',
                    'Describe this image in detail',
                    'What objects are present in this image?',
                    'Analyze the composition of this image',
                    'What is the main subject of this image?'
                ]
            },
            'text_models': {
                'default': 'How can I help you today?',
                'suggestions': [
                    'How can I help you today?',
                    'Tell me about yourself',
                    'What can you do?',
                    'Help me with a task',
                    'Give me some information'
                ]
            }
        }

# Initialize history manager
history_manager = HistoryManager(Config.HISTORY_FILE, Config.MAX_HISTORY_ENTRIES)

if __name__ == '__main__':
    # Set logging level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logger.setLevel(log_level)
    
    # Get port from Config, which reads from .env
    port = int(os.getenv('FLASK_PORT', Config.PORT))
    
    logger.info(f'Starting server on port {port}')
    app.run(debug=Config.DEBUG, port=port)
