import os
import secrets
import logging
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from config import Config
from history_manager import HistoryManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEBUG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
VISION_MODELS = {'llava', 'bakllava'}  # Add other vision models as needed

# Initialize Flask app
app = Flask(__name__)

# Initialize configuration
Config.init_app(app)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize history manager
history_manager = HistoryManager(app.config['HISTORY_FILE'], app.config['MAX_HISTORY_ENTRIES'])

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Debug levels for the UI
DEBUG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

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
    try:
        # Get available models
        models = get_available_models()
        model_names = [model['name'] for model in models]
        
        # Get selected model from session or use default
        selected_model = session.get('selected_model')
        if not selected_model and model_names:
            selected_model = model_names[0]
            session['selected_model'] = selected_model
        
        # Get current debug level
        current_debug_level = session.get('debug_level', 'INFO')
        
        # Get prompts for model type
        prompts = app.config.get('PROMPTS', {})
        if not prompts:
            prompts = {
                'vision_models': {'default': '', 'suggestions': []},
                'text_models': {'default': '', 'suggestions': []}
            }
        
        # Determine model type and get prompts
        if selected_model:
            model_type = 'vision_models' if is_vision_model(selected_model) else 'text_models'
            model_prompts = prompts.get(model_type, {})
            default_prompt = model_prompts.get('default', '')
            prompt_suggestions = model_prompts.get('suggestions', [])
        else:
            default_prompt = ''
            prompt_suggestions = []
        
        # Render template with data
        return render_template('index.html',
                            models=models,
                            selected_model=selected_model,
                            default_prompt=default_prompt,
                            prompt_suggestions=prompt_suggestions,
                            prompts=prompts,
                            debug_levels=DEBUG_LEVELS,
                            current_debug_level=current_debug_level,
                            history=history_manager.load_history())
    except Exception as e:
        app.logger.error(f"Error in home route: {e}")
        return render_template('index.html', error=str(e))

@app.route('/select_model', methods=['POST'])
def select_model():
    """Handle model selection"""
    try:
        model = request.form.get('model')
        if not model:
            return jsonify({'status': 'error', 'message': 'No model specified'}), 400

        # Store selected model in session
        session['selected_model'] = model

        # Determine model type and get prompts
        model_type = 'vision_models' if is_vision_model(model) else 'text_models'
        prompts = app.config.get('PROMPTS', {})
        if not prompts:
            prompts = {
                'vision_models': {'default': '', 'suggestions': []},
                'text_models': {'default': '', 'suggestions': []}
            }

        model_prompts = prompts.get(model_type, {})
        default_prompt = model_prompts.get('default', '')
        prompt_suggestions = model_prompts.get('suggestions', [])

        return jsonify({
            'status': 'success',
            'model': model,
            'default_prompt': default_prompt,
            'prompt_suggestions': prompt_suggestions
        })

    except Exception as e:
        app.logger.error(f"Error in select_model: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

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
        
        is_vision = is_vision_model(model)
        file_types = get_supported_file_types(model)
        
        # Check if file is required but not provided
        if file_types['required'] and 'file' not in request.files:
            error_msg = f"This model requires a {file_types['description']} file"
            logger.warning(error_msg)
            return render_template('index.html', 
                                 models=get_available_models(),
                                 debug_levels=DEBUG_LEVELS,
                                 current_debug_level=session.get('debug_level', 'INFO'),
                                 result=error_msg)
        
        # Handle file if provided
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            filename = secure_filename(file.filename)
            file_ext = filename.split('.')[-1].lower()
            
            # Validate file extension
            if file_ext not in file_types['extensions']:
                error_msg = f"Invalid file type. Supported types: {file_types['description']}"
                logger.warning(error_msg)
                return render_template('index.html', 
                                     models=get_available_models(),
                                     debug_levels=DEBUG_LEVELS,
                                     current_debug_level=session.get('debug_level', 'INFO'),
                                     result=error_msg)
            
            # Save and process file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                if is_vision:
                    # Use Ollama to analyze the image
                    response = ollama.chat(
                        model=model,
                        messages=[{
                            "role": "user",
                            "content": f"Prompt: {prompt}\nPlease analyze this image and answer the prompt.",
                            "images": [filepath]
                        }],
                    )
                else:
                    # Read and process text-based file
                    try:
                        with open(filepath, 'r') as f:
                            file_content = f.read()
                    except UnicodeDecodeError:
                        error_msg = "Could not read file. Make sure it's a valid text file."
                        logger.error(error_msg)
                        return render_template('index.html', 
                                             models=get_available_models(),
                                             debug_levels=DEBUG_LEVELS,
                                             current_debug_level=session.get('debug_level', 'INFO'),
                                             result=error_msg)
                    
                    # Use Ollama to analyze the document
                    response = ollama.chat(
                        model=model,
                        messages=[{
                            "role": "user",
                            "content": f"Here is the document content:\n\n{file_content}\n\nPrompt: {prompt}"
                        }],
                    )
            finally:
                # Clean up the uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            # No file provided, just process the prompt
            if file_types['required']:
                error_msg = f"This model requires a {file_types['description']} file"
                logger.warning(error_msg)
                return render_template('index.html', 
                                     models=get_available_models(),
                                     debug_levels=DEBUG_LEVELS,
                                     current_debug_level=session.get('debug_level', 'INFO'),
                                     result=error_msg)
            
            response = ollama.chat(
                model=model,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
            )
        
        result = response['message']['content']
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Format response with timing
        result_with_timing = f"Response (took {duration:.2f} seconds):\n\n{result}"
        
        # Add to persistent history
        history = history_manager.add_entry(
            model=model,
            prompt=prompt,
            result=result_with_timing,
            duration=duration,
            success=True
        )
        
        logger.info('Analysis completed successfully')
        return render_template('index.html', 
                             models=get_available_models(),
                             debug_levels=DEBUG_LEVELS,
                             current_debug_level=session.get('debug_level', 'INFO'),
                             selected_model=model,
                             result=result_with_timing,
                             history=history)
    
    except Exception as e:
        logger.exception('Error during analysis')
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        error_with_timing = f"Error (after {duration:.2f} seconds): {str(e)}"
        
        # Add error to persistent history
        history = history_manager.add_entry(
            model=model,
            prompt=prompt,
            result=error_with_timing,
            duration=duration,
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

def is_vision_model(model_name):
    """Check if a model is a vision model."""
    vision_models = ['llava', 'bakllava']  # Add more vision models as needed
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
            return models if models else []
        return []
    except Exception as e:
        app.logger.error(f"Error getting models: {e}")
        return []

if __name__ == '__main__':
    logger.setLevel(logging.INFO)  # Set default level to INFO
    app.run(debug=True, port=5002)
