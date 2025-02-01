import os
import secrets
import logging
import requests
import base64
import time
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response, make_response
from werkzeug.utils import secure_filename
from config import Config
from history_manager import HistoryManager
from fetch_manager import FetchManager
import json
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s    %(name)s:%(filename)s:%(lineno)d %(message)s'))
logger.addHandler(handler)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

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

# Initialize history manager
history_manager = HistoryManager(Config.HISTORY_FILE, Config.MAX_HISTORY_ENTRIES)

# Initialize fetch manager
fetch_manager = FetchManager()

# Load prompts from JSON file
try:
    prompts_path = os.path.join(app.root_path, 'prompts.json')
    logger.debug(f"Loading prompts from: {prompts_path}")
    with open(prompts_path) as f:
        PROMPTS = json.load(f)
    logger.debug(f"Loaded prompts: {PROMPTS}")
    logger.debug(f"Rendering template with prompts: {PROMPTS}")
except Exception as e:
    logger.error(f"Error loading prompts.json: {e}")
    PROMPTS = {
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

# Define vision models
VISION_MODELS = ['llava', 'bakllava']  # Add more vision models as needed

# Configure upload folder
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Debug levels
DEBUG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# Constants

# Global variable to store active requests
active_requests = {}

@app.route('/debug_level', methods=['POST'])
def set_debug_level():
    """Set the debug level for the application."""
    try:
        level = request.form.get('level', 'INFO').upper()
        logger.info(f'Attempting to set debug level to: {level}')
        
        if level not in DEBUG_LEVELS:
            logger.error(f'Invalid debug level requested: {level}')
            return jsonify({
                'status': 'error',
                'message': f'Invalid debug level: {level}. Must be one of {DEBUG_LEVELS}'
            }), 400
        
        # Set the debug level in session
        session_id = request.cookies.get('session_id')
        if session_id:
            sess, _ = Session.get_or_create(session_id)
            sess.set_data(level)
        
        # Log messages at different levels for testing
        logger.debug('Debug message - should show if level is DEBUG or lower')
        logger.info('Info message - should show if level is INFO or lower')
        logger.warning('Warning message - should show if level is WARNING or lower')
        logger.error('Error message - should show if level is ERROR or lower')
        
        logger.info(f'Successfully set debug level to: {level}')
        return jsonify({
            'status': 'success',
            'current_debug_level': level,
            'message': f'Debug level set to {level}'
        })
        
    except Exception as e:
        logger.error(f'Error setting debug level: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error setting debug level: {str(e)}'
        }), 500

@app.route('/models')
@csrf.exempt  # Exempt CSRF for this GET route
def models():
    """Get list of available models."""
    try:
        models_list = get_available_models()
        logger.debug(f'Returning models: {models_list}')
        return jsonify(models_list)
    except Exception as e:
        logger.error(f'Error in /models route: {str(e)}', exc_info=True)
        return jsonify([])

@app.route('/')
def index():
    """Render the index page."""
    try:
        # Get available models and select first one as default
        models = get_available_models()
        default_model = models[0] if models else None
        
        # Load history
        history = history_manager.load_history()
        history_limit = int(os.getenv('HISTORY_PROMPT_LIMIT', '3'))
        history_prompts = get_history_prompts(history, None, history_limit)
        
        # Get all prompts and suggestions
        all_prompts = []
        for model_type in ['vision_models', 'text_models']:
            all_prompts.extend(PROMPTS[model_type]['suggestions'])
        
        prompt_suggestions = history_prompts + [p for p in all_prompts if p not in history_prompts]
        
        logger.info(f'Loaded {len(models)} models')
        logger.info(f'Using default model: {default_model}')
        logger.info(f'Loaded {len(history)} history entries')
        logger.info(f'Loaded {len(prompt_suggestions)} prompt suggestions')
        
        return render_template('index.html', 
                            models=models,
                            model=default_model['name'] if default_model else None,
                            prompts=PROMPTS,
                            prompt_suggestions=prompt_suggestions,
                            default_prompt=PROMPTS['text_models']['default'])
    except Exception as e:
        logger.error(f'Error rendering index: {e}')
        return f'Error: {str(e)}', 500

@app.route('/select_model', methods=['POST'])
def select_model():
    """Handle model selection."""
    model = request.form.get('model')
    if not model:
        return jsonify({'status': 'error', 'message': 'No model specified'}), 400
    
    # Store selected model in session
    session_id = request.cookies.get('session_id')
    if session_id:
        sess, _ = Session.get_or_create(session_id)
        sess.set_data(model)
    
    # Get all prompts
    all_prompts = []
    for model_type in ['vision_models', 'text_models']:
        all_prompts.extend(PROMPTS[model_type]['suggestions'])
    
    # Get history prompts
    history = history_manager.load_history()
    history_limit = int(os.getenv('HISTORY_PROMPT_LIMIT', '3'))
    history_prompts = get_history_prompts(history, None, history_limit)
    
    # Combine all prompts with history prompts
    prompt_suggestions = all_prompts + [p for p in history_prompts if p not in all_prompts]
    
    # Use text model default prompt
    default_prompt = PROMPTS['text_models']['default']
    
    return jsonify({
        'status': 'success',
        'model': model,
        'default_prompt': default_prompt,
        'prompt_suggestions': prompt_suggestions
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze prompt with selected model."""
    try:
        # Get model and prompt
        model = request.form.get('model')
        prompt = request.form.get('prompt')
        logger.info(f'Starting analysis with model: {model}')
        logger.info(f'Prompt: {prompt}')

        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        logger.info(f'Request type: {"AJAX" if is_ajax else "regular"}')

        # Get all prompts and suggestions
        history = history_manager.load_history()
        history_limit = int(os.getenv('HISTORY_PROMPT_LIMIT', '3'))
        history_prompts = get_history_prompts(history, None, history_limit)
        
        all_prompts = []
        for model_type in ['vision_models', 'text_models']:
            all_prompts.extend(PROMPTS[model_type]['suggestions'])
        
        prompt_suggestions = history_prompts + [p for p in all_prompts if p not in history_prompts]

        # Handle file if provided
        file = request.files.get('file')
        if file:
            # Process file for vision model
            image_data = file.read()
            image_b64 = base64.b64encode(image_data).decode()
            messages = [
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_b64]
                }
            ]
            data = {'model': model, 'messages': messages}
        else:
            # Regular text prompt
            data = {'model': model, 'prompt': prompt}

        # Make request to Ollama API
        start_time = time.time()
        response = requests.post(
            f'{Config.OLLAMA_HOST}/api/chat' if file else f'{Config.OLLAMA_HOST}/api/generate',
            json=data,
            stream=True
        )

        # Store request for potential abort
        request_id = secrets.token_urlsafe(16)
        active_requests[request_id] = response

        # Check response status
        if response.status_code != 200:
            error_msg = f'Error from Ollama API: {response.text}'
            logger.error(error_msg)
            if not is_ajax:
                return render_template('index.html', 
                                    models=get_available_models(),
                                    model=model,
                                    prompts=PROMPTS,
                                    prompt_suggestions=prompt_suggestions,
                                    default_prompt=PROMPTS['text_models']['default'],
                                    result=error_msg)
            else:
                return jsonify({'error': error_msg}), response.status_code

        # Stream the response
        def generate():
            try:
                full_response = ''
                response_start = time.time()

                for line in response.iter_lines():
                    if line:
                        try:
                            json_line = json.loads(line)
                            logger.debug(f'Received line: {json_line}')
                            if 'response' in json_line:
                                chunk = json_line['response']
                                full_response += chunk
                                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                            elif 'error' in json_line:
                                error_msg = f"Error from Ollama API: {json_line['error']}"
                                logger.error(error_msg)
                                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                                break
                        except json.JSONDecodeError as e:
                            error_msg = f'Error decoding JSON response: {e}'
                            logger.error(error_msg)
                            yield f"data: {json.dumps({'error': error_msg})}\n\n"
                            break

                # Store in history after successful completion
                if full_response:
                    try:
                        duration = time.time() - response_start
                        history_manager.add_entry(
                            model=model,
                            prompt=prompt,
                            result=full_response,
                            duration=duration,
                            success=True
                        )
                        logger.info(f'Analysis completed in {duration:.2f} seconds')
                    except Exception as e:
                        logger.error(f'Error adding to history: {e}')
                        # Don't stop the response if history fails
                        pass

                # Clean up request
                if request_id in active_requests:
                    del active_requests[request_id]

                yield f"data: {json.dumps({'done': True})}\n\n"

            except Exception as e:
                error_msg = f'Error during analysis: {str(e)}'
                logger.error(error_msg)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"

            finally:
                # Always clean up request
                if request_id in active_requests:
                    del active_requests[request_id]

        # Return streamed response for AJAX requests
        if is_ajax:
            return Response(generate(), mimetype='text/event-stream')
        
        # For non-AJAX requests, collect the full response and render the template
        full_response = ''
        for line in response.iter_lines():
            if line:
                try:
                    json_line = json.loads(line)
                    if 'response' in json_line:
                        full_response += json_line['response']
                    elif 'error' in json_line:
                        error_msg = f"Error from Ollama API: {json_line['error']}"
                        logger.error(error_msg)
                        return render_template('index.html', 
                                            models=get_available_models(),
                                            model=model,
                                            prompts=PROMPTS,
                                            prompt_suggestions=prompt_suggestions,
                                            default_prompt=PROMPTS['text_models']['default'],
                                            result=error_msg)
                except json.JSONDecodeError as e:
                    error_msg = f'Error decoding JSON response: {e}'
                    logger.error(error_msg)
                    return render_template('index.html', 
                                        models=get_available_models(),
                                        model=model,
                                        prompts=PROMPTS,
                                        prompt_suggestions=prompt_suggestions,
                                        default_prompt=PROMPTS['text_models']['default'],
                                        result=error_msg)

        # Store in history
        try:
            duration = time.time() - start_time
            history_manager.add_entry(
                model=model,
                prompt=prompt,
                result=full_response,
                duration=duration,
                success=True
            )
            logger.info(f'Analysis completed in {duration:.2f} seconds')
        except Exception as e:
            logger.error(f'Error adding to history: {e}')

        return render_template('index.html', 
                            models=get_available_models(),
                            model=model,
                            prompts=PROMPTS,
                            prompt_suggestions=prompt_suggestions,
                            default_prompt=PROMPTS['text_models']['default'],
                            result=full_response)

    except Exception as e:
        error_msg = f'Error during analysis: {str(e)}'
        logger.error(error_msg)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': error_msg}), 500
        return render_template('index.html', 
                            models=get_available_models(),
                            model=model,
                            prompts=PROMPTS,
                            prompt_suggestions=prompt_suggestions,
                            default_prompt=PROMPTS['text_models']['default'],
                            result=error_msg)

@app.route('/abort', methods=['POST'])
def abort_analysis():
    """Abort the current analysis."""
    try:
        # Check if there are any active requests
        if not active_requests:
            return jsonify({
                'status': 'error',
                'message': 'No active request to abort'
            }), 404

        # Get active request
        request_id = next(iter(active_requests))
        response = active_requests.pop(request_id)
        if hasattr(response, 'close'):
            response.close()

        return jsonify({
            'status': 'success',
            'message': 'Analysis aborted'
        })
    except Exception as e:
        logger.error(f'Error aborting analysis: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'Error aborting analysis: {str(e)}'
        }), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear all history."""
    try:
        history_manager.clear_history()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.exception('Error clearing history')
        return jsonify({'status': 'error', 'message': str(e)}), 500

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

@app.route('/library/models', methods=['GET'])
def get_library_models():
    """Get available models from Ollama library."""
    try:
        models_data = fetch_manager.get_library_models()
        if models_data is None:
            return jsonify({'error': 'Failed to fetch library models'}), 500
        return jsonify(models_data)
    except Exception as e:
        logger.error(f"Error in get_library_models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/pull/model', methods=['POST'])
@csrf.exempt
def pull_model():
    """Pull a model from Ollama library."""
    try:
        model_name = request.json.get('name')
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
            
        def generate():
            try:
                for progress in fetch_manager.pull_model(model_name):
                    if progress:
                        # Add event type for SSE
                        yield f"event: progress\ndata: {json.dumps(progress)}\n\n"
                # Send done event
                yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
            except Exception as e:
                logger.error(f"Error pulling model: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        logger.error(f"Error in pull_model: {e}")
        return jsonify({'error': str(e)}), 500

def get_history_prompts(history=None, model_type=None, limit=None):
    """Get prompt suggestions from history."""
    if history is None:
        history = history_manager.load_history()
    if limit is None:
        limit = Config.HISTORY_PROMPT_LIMIT

    prompts = []
    for entry in history[:limit]:
        try:
            if 'prompt' in entry:
                prompts.append(entry['prompt'])
        except Exception as e:
            logger.error(f'Error processing history entry: {e}')
            continue

    return prompts

def is_vision_model(model_name):
    """Check if a model is a vision model."""
    vision_models = VISION_MODELS  # Add more vision models as needed
    return any(vm in model_name.lower() for vm in vision_models)

def get_supported_file_types(model_name):
    """Get supported file types based on model capabilities."""
    if is_vision_model(model_name):
        return {
            'extensions': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'],
            'description': 'Images (JPG, PNG, GIF, etc.)',
            'type': 'image/*',
            'required': True
        }
    else:
        return {
            'extensions': ['txt', 'md', 'pdf', 'doc', 'docx', 'csv', 'json'],
            'description': 'Documents (TXT, PDF, DOC, etc.)',
            'type': 'application/pdf,text/plain,.doc,.docx,.md,.csv,.json',
            'required': False
        }

def get_available_models():
    """Get list of available models."""
    try:
        response = requests.get(f"{Config.OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            return response.json().get('models', [])
        return []
    except Exception as e:
        app.logger.error(f"Error getting models: {e}")
        return []

if __name__ == '__main__':
    logger.setLevel(logging.INFO)  # Set default level to INFO
    port = int(os.getenv('FLASK_PORT', 5002))  # Use FLASK_PORT from .env, default to 5002 if not set
    app.run(debug=True, port=port)
