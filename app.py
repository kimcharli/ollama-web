import os
import secrets
import logging
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, Response
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import ollama

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for CSRF
app.config['UPLOAD_FOLDER'] = 'uploads'
csrf = CSRFProtect(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Debug levels for the UI
DEBUG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

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
        
        # Convert string level to logging constant
        numeric_level = getattr(logging, level)
        
        # Set the logger level
        logger.setLevel(numeric_level)
        
        # Store in session
        session['debug_level'] = level
        
        # Log at new level to verify change
        logger.debug('Debug message - should show if level is DEBUG or lower')
        logger.info('Info message - should show if level is INFO or lower')
        logger.warning('Warning message - should show if level is WARNING or lower')
        logger.error('Error message - should show if level is ERROR or lower')
        
        logger.info(f'Successfully set debug level to: {level}')
        
        return jsonify({
            'status': 'success',
            'level': level,
            'current_debug_level': level,
            'message': f'Debug level set to {level}'
        })
        
    except Exception as e:
        logger.exception('Error setting debug level')
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
        logger.debug('Loading index page...')
        models_list = get_available_models()
        logger.debug(f'Models for index page: {models_list}')
        
        # Get debug level from session or use default
        current_debug_level = session.get('debug_level', 'INFO')
        logger.setLevel(getattr(logging, current_debug_level))
        
        # Get selected model from session or use first available
        selected_model = session.get('selected_model')
        logger.debug(f'Model from session: {selected_model}')
        
        if not selected_model and models_list:
            selected_model = models_list[0]
            session['selected_model'] = selected_model
            logger.debug(f'Setting default model: {selected_model}')
        elif selected_model not in models_list and models_list:
            selected_model = models_list[0]
            session['selected_model'] = selected_model
            logger.debug(f'Previous model not found, setting to: {selected_model}')
        
        logger.debug(f'Using selected model: {selected_model}')
        
        # Get history from session
        history = session.get('history', [])
        
        return render_template('index.html',
                             models=models_list,
                             debug_levels=DEBUG_LEVELS,
                             current_debug_level=current_debug_level,
                             selected_model=selected_model,
                             history=history)
    except Exception as e:
        logger.error(f'Error rendering index: {str(e)}', exc_info=True)
        return render_template('index.html',
                             models=[],
                             debug_levels=DEBUG_LEVELS,
                             current_debug_level=current_debug_level,
                             error=str(e),
                             history=[])

@app.route('/select_model', methods=['POST'])
def select_model():
    """Set the selected model."""
    try:
        model = request.form.get('model')
        logger.info(f'Setting selected model to: {model}')
        
        if not model:
            logger.error('No model specified in request')
            return jsonify({
                'status': 'error',
                'message': 'No model specified'
            }), 400
        
        # Store in session
        session['selected_model'] = model
        logger.debug(f'Stored model in session: {model}')
        
        return jsonify({
            'status': 'success',
            'model': model,
            'message': f'Selected model: {model}'
        })
        
    except Exception as e:
        logger.exception('Error setting model')
        return jsonify({
            'status': 'error',
            'message': f'Error setting model: {str(e)}'
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
        
        # Add to history
        history = session.get('history', [])
        history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'model': model,
            'prompt': prompt,
            'result': result_with_timing,
            'duration': duration,
            'success': True
        })
        session['history'] = history
        
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
        
        # Add error to history
        history = session.get('history', [])
        history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'model': model,
            'prompt': prompt,
            'result': error_with_timing,
            'duration': duration,
            'success': False
        })
        session['history'] = history
        
        return render_template('index.html', 
                             models=get_available_models(),
                             debug_levels=DEBUG_LEVELS,
                             current_debug_level=session.get('debug_level', 'INFO'),
                             selected_model=model,
                             result=error_with_timing,
                             history=history)

def is_vision_model(model_name):
    """Check if a model is a vision model based on its name or capabilities."""
    vision_indicators = ['vision', 'llava', 'image']
    return any(indicator in model_name.lower() for indicator in vision_indicators)

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
    """Get list of available models from Ollama."""
    try:
        logger.debug('Attempting to connect to Ollama...')
        
        # Direct API call to Ollama
        response = requests.get('http://localhost:11434/api/tags')
        logger.debug(f'Raw Ollama response status: {response.status_code}')
        logger.debug(f'Raw Ollama response: {response.json()}')
        
        if response.status_code == 200:
            data = response.json()
            if 'models' in data:
                models = sorted([model['name'] for model in data['models']])
            else:
                models = sorted([model['name'] for model in data.get('models', [])])
            logger.info(f'Found {len(models)} models: {models}')
            return models
        else:
            logger.warning(f'Ollama API returned status code: {response.status_code}')
            return []
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f'Failed to connect to Ollama server: {str(e)}')
        return []
    except Exception as e:
        logger.error(f'Error fetching models: {str(e)}', exc_info=True)
        return []

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)  # Set default level to DEBUG
    app.run(debug=True)
