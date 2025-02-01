import os
import secrets
import logging
import requests
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from config import Config
from history_manager import HistoryManager
import json

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s    %(name)s:%(filename)s:%(lineno)d %(message)s'))
logger.addHandler(handler)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Initialize configuration
Config.init_app(app)

# Initialize CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Initialize history manager
history_manager = HistoryManager(app.config['HISTORY_FILE'], app.config['MAX_HISTORY_ENTRIES'])

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
        session['debug_level'] = level
        
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
def home():
    """Home page route."""
    # Get available models
    models = get_available_models()
    
    # Get selected model from session, use first available model as default
    selected_model = session.get('selected_model')
    if not selected_model and models:
        selected_model = models[0]
        session['selected_model'] = selected_model
    
    # Get all prompts
    all_prompts = []
    for model_type in ['vision_models', 'text_models']:
        if model_type in PROMPTS and 'suggestions' in PROMPTS[model_type]:
            all_prompts.extend(PROMPTS[model_type]['suggestions'])
    
    # Get history prompts
    history = history_manager.load_history()
    history_limit = int(os.getenv('HISTORY_PROMPT_LIMIT', '3'))
    app.logger.debug(f"Loaded history: {history}")
    history_prompts = get_history_prompts(history, None, history_limit)
    app.logger.debug(f"History prompts: {history_prompts}")
    
    # Combine all prompts with history prompts
    prompt_suggestions = list(dict.fromkeys(all_prompts + history_prompts))  # Remove duplicates while preserving order
    app.logger.debug(f"All prompts: {all_prompts}")
    app.logger.debug(f"Combined prompt suggestions: {prompt_suggestions}")
    
    # Use text model default prompt as default
    default_prompt = PROMPTS['text_models']['default']
    
    # Render template with data
    return render_template('index.html',
                        models=models,
                        selected_model=selected_model,
                        debug_levels=DEBUG_LEVELS,
                        current_debug_level=session.get('debug_level', 'INFO'),
                        prompt_suggestions=prompt_suggestions,
                        default_prompt=default_prompt,
                        prompts=PROMPTS)

@app.route('/select_model', methods=['POST'])
def select_model():
    """Handle model selection."""
    model = request.form.get('model')
    if not model:
        return jsonify({'status': 'error', 'message': 'No model specified'}), 400
    
    # Store selected model in session
    session['selected_model'] = model
    
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
    """Analyze an image or process a text prompt."""
    start_time = datetime.now()
    model = request.form.get('model')
    prompt = request.form.get('prompt', 'Analyze this.')
    
    try:
        logger.info(f'Starting analysis with model: {model}')
        logger.info(f'Prompt: {prompt}')
        
        # Update session with current model if provided, otherwise use session model
        if model:
            session['selected_model'] = model
            logger.debug(f'Updated session model to: {model}')
        else:
            model = session.get('selected_model')
            logger.debug(f'Using model from session: {model}')
        
        # Handle file if provided
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            filename = secure_filename(file.filename)
            
            # Save and process file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Read file as base64
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                file_base64 = base64.b64encode(file_data).decode('utf-8')
                
                # Use Ollama API with image
                response = requests.post(
                    f"{Config.OLLAMA_HOST}/api/chat",
                    json={
                        "model": model,
                        "messages": [{
                            "role": "user",
                            "content": prompt,
                            "images": [file_base64]
                        }]
                    }
                )
            finally:
                # Clean up the uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            # Use Ollama API without image
            response = requests.post(
                f"{Config.OLLAMA_HOST}/api/chat",
                json={
                    "model": model,
                    "messages": [{
                        "role": "user",
                        "content": prompt
                    }]
                }
            )
        
        # Check response status
        if response.status_code != 200:
            error_msg = f"Error from Ollama API: {response.text}"
            logger.error(error_msg)
            return render_template('index.html', 
                                 models=get_available_models(),
                                 debug_levels=DEBUG_LEVELS,
                                 current_debug_level=session.get('debug_level', 'INFO'),
                                 result=error_msg)
        
        # Parse response
        try:
            lines = response.text.strip().split('\n')
            full_response = ""
            
            # Process each line of the streaming response
            for line in lines:
                try:
                    response_json = json.loads(line)
                    if 'message' in response_json:
                        # Chat response
                        content = response_json['message']['content']
                        full_response += content
                    elif 'response' in response_json:
                        # Generate response
                        content = response_json['response']
                        full_response += content
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Format response with timing
            result_with_timing = f"Response (took {duration:.2f} seconds):\n\n{full_response}"
            
            # Add to persistent history
            history = history_manager.add_entry(
                model=model,
                prompt=prompt,
                result=result_with_timing,
                duration=duration,
                success=True
            )
        except Exception as e:
            error_msg = f"Error parsing response: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Response text: {response.text}")
            return render_template('index.html', 
                                models=get_available_models(),
                                debug_levels=DEBUG_LEVELS,
                                current_debug_level=session.get('debug_level', 'INFO'),
                                result=error_msg)
        
        # Get prompt suggestions
        history_limit = int(os.getenv('HISTORY_PROMPT_LIMIT', '3'))
        history_prompts = get_history_prompts(history, None, history_limit)
        
        prompt_suggestions = [
            'What do you see in this image?',
            'Describe this image in detail',
            'What objects are present in this image?',
            'Analyze the composition of this image',
            'What is the main subject of this image?'
        ]
        
        # Combine suggestions with history prompts
        prompt_suggestions = prompt_suggestions + [p for p in history_prompts if p not in prompt_suggestions]
        
        logger.info('Analysis completed successfully')
        return render_template('index.html', 
                             models=get_available_models(),
                             debug_levels=DEBUG_LEVELS,
                             current_debug_level=session.get('debug_level', 'INFO'),
                             selected_model=model,
                             result=result_with_timing,
                             history=history,
                             prompt_suggestions=prompt_suggestions)
    
    except Exception as e:
        logger.exception('Error in analyze')
        error_with_timing = f"Error (after {(datetime.now() - start_time).total_seconds():.2f} seconds): {str(e)}"
        
        # Add to persistent history
        history = history_manager.add_entry(
            model=model,
            prompt=prompt,
            result=error_with_timing,
            duration=(datetime.now() - start_time).total_seconds(),
            success=False
        )
        
        return render_template('index.html', 
                             models=get_available_models(),
                             debug_levels=DEBUG_LEVELS,
                             current_debug_level=session.get('debug_level', 'INFO'),
                             selected_model=model,
                             result=error_with_timing,
                             history=history)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear all history."""
    try:
        history_manager.clear_history()
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.exception('Error clearing history')
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_history_prompts(history, model_type, limit=3):
    """Get unique prompts from history for a specific model type."""
    app.logger.debug(f"Getting history prompts with model_type={model_type}, limit={limit}")
    if not history:
        app.logger.debug("No history found")
        return []
        
    prompts = []
    seen = set()
    
    for entry in history:
        prompt = entry.get('prompt')
        app.logger.debug(f"Processing entry: {entry}")
        if not prompt or prompt in seen:
            app.logger.debug(f"Skipping prompt: {prompt} (empty or duplicate)")
            continue
            
        # Check if model type matches
        is_vision = is_vision_model(entry.get('model', ''))
        current_type = 'vision' if is_vision else 'text'
        app.logger.debug(f"Entry model type: {current_type}")
        
        if model_type is None or current_type == model_type:
            app.logger.debug(f"Adding prompt: {prompt}")
            prompts.append(prompt)
            seen.add(prompt)
            
            if len(prompts) >= limit:
                app.logger.debug(f"Reached limit of {limit} prompts")
                break
    
    app.logger.debug(f"Returning prompts: {prompts}")
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
            models = response.json().get('models', [])
            return [model['name'] for model in models] if models else []
        return []
    except Exception as e:
        app.logger.error(f"Error getting models: {e}")
        return []

if __name__ == '__main__':
    logger.setLevel(logging.INFO)  # Set default level to INFO
    port = int(os.getenv('FLASK_PORT', 5002))  # Use FLASK_PORT from .env, default to 5002 if not set
    app.run(debug=True, port=port)
