# Llama Vision Web Application Design

## Overview
A web application built with Flask and the Ollama API for image and document analysis, providing an intuitive interface for users to interact with various AI models.

## Core Features

### Model Management
- [x] Dynamic model discovery from Ollama
- [x] Persistent model selection across sessions
- [x] Model refresh functionality
- [x] Universal file handling for all models

### File Handling
- [x] Optional file upload for all models
- [x] Base64 image encoding for API requests
- [x] Automatic file cleanup after processing
- [x] Secure file handling with validation

### Prompt Management
- [x] Universal prompt suggestions
- [x] Quick prompt suggestions
- [x] Custom prompt input
- [x] Persistent prompt history
- [x] History-based prompt suggestions

### Debug Features
- [x] Configurable debug levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [x] Persistent debug level selection
- [x] Visual feedback for current debug state
- [x] Dropdown menu for easy level switching

### Analysis History
- [x] Persistent file storage of analysis history in `query_history.json`
- [x] Chronological history of analyses
- [x] Success/Error status indication
- [x] Timestamp tracking
- [x] Duration tracking
- [x] Collapsible result view
- [x] Model used for each analysis
- [x] Prompt used for each analysis
- [x] History survives server restarts
- [x] Reuse prompts from history
- [x] Clear history functionality

### User Interface
- [x] Clean, modern design using Tailwind CSS
- [x] Responsive layout
- [x] Analysis progress indication:
  - Analyze button shows "Analyzing..." state
  - Animated loading spinner during analysis
  - Context-aware loading messages based on input type
  - Button disabled during analysis
  - Abort button for long-running analyses
  - Visual feedback for request cancellation
- [x] Home navigation with icon
- [x] Clear error messages and validation feedback
- [x] Collapsible sections for better space management
- [x] Consistent file upload section for all models

### API Integration
- [x] Streaming response handling
- [x] Response concatenation for complete output
- [x] Error handling for partial responses
- [x] JSON parsing for each response chunk
- [x] Accurate timing information
- [x] Request cancellation support
- [x] Active request tracking
- [x] Session-based request management

### Security
- [x] CSRF protection
- [x] File type validation
- [x] File size limits
- [x] Secure file handling with cleanup

### Configuration Management
- [x] Environment-based configuration using `.env` file
- [x] Configurable settings:
  - Flask configuration (secret key, debug mode)
  - File storage paths (uploads, history file)
  - History management (max entries)
  - Ollama host configuration
  - Port configuration
- [x] Default values for all settings
- [x] Easy deployment configuration
- [x] Centralized config management in `config.py`

### Testing
- [x] Unit tests for core functionality
- [x] Integration tests for API endpoints
- [x] Mock testing for external services
- [x] Test cases for:
  - Text analysis
  - Image analysis
  - Error handling
  - Request cancellation
  - Streaming responses
  - History management

## Technical Requirements

### Backend
- Flask web framework
- Ollama API integration
- Session management
- File upload handling
- Logging system
- Streaming response handling

### Frontend
- Tailwind CSS for styling
- JavaScript for dynamic UI updates
- CSRF token handling
- Async operations for analysis
- Real-time UI feedback

### Dependencies
- Flask
- Flask-WTF (for CSRF)
- Ollama API
- Werkzeug (for file handling)
- Python standard library

## Development Environment

### Prerequisites
- Python 3.10 (managed by pyenv)
- Ollama server running locally
- uv package manager

### Setup and Running
1. Clone the repository
2. Ensure Python 3.10 is active:
   ```bash
   # Check .python-version file
   cat .python-version  # Should show 3.10
   
   # Verify Python version
   python --version    # Should show Python 3.10.x
   ```

3. Run the application:
   ```bash
   # Start the development server
   uv run app.py
   ```
   The application will be available at http://127.0.0.1:5000

### Development Notes
- The application uses Flask's development server with debug mode enabled
- File uploads are stored temporarily in the `uploads` directory
- Query history is stored in `query_history.json`
- CSRF protection is enabled for all form submissions

### Troubleshooting
- If `uv` command is not found, install it using:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Ensure Ollama server is running locally before starting the application
- Check the Flask debug output for any errors (debug PIN is shown in console)

## TODO List

### Results Management
- [ ] Clear results section when starting new analysis
  - Automatically clear previous results
  - Show placeholder text indicating new analysis started
  - Maintain history section intact

### Analysis Progress
- [ ] Enhanced timing information
  - Display analysis start time
  - Show real-time progress in seconds
  - Update progress counter dynamically
  - Format timestamps in user's local timezone

### Ollama Process Status
- [ ] Add Ollama process monitoring
  - Show if Ollama is running or stopped
  - Display current Ollama process status
  - Show number of active Ollama processes
  - Add visual indicator for Ollama health
  - Show warning if Ollama is not running
  - Add auto-refresh for status updates

### Implementation Details

#### Results Clearing
```javascript
// Clear results when starting new analysis
function clearResults() {
    const resultsDiv = document.querySelector('.results-section');
    resultsDiv.innerHTML = '<div class="analyzing-placeholder">Starting new analysis...</div>';
}
```

#### Progress Display
```javascript
// Track and display analysis progress
let analysisStartTime = null;
let progressInterval = null;

function startProgressTracking() {
    analysisStartTime = new Date();
    const progressDiv = document.getElementById('progress');
    progressDiv.innerHTML = `Started at ${analysisStartTime.toLocaleTimeString()}`;
    
    progressInterval = setInterval(() => {
        const elapsed = Math.floor((new Date() - analysisStartTime) / 1000);
        progressDiv.innerHTML += `<br>Elapsed: ${elapsed} seconds`;
    }, 1000);
}
```

#### Ollama Status
```python
@app.route('/ollama/status')
def get_ollama_status():
    """Get Ollama process status."""
    try:
        response = requests.get(f"{Config.OLLAMA_HOST}/api/status")
        processes = subprocess.check_output(['pgrep', '-f', 'ollama']).decode().strip().split('\n')
        return jsonify({
            'status': 'running' if response.status_code == 200 else 'error',
            'processes': len(processes),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'stopped',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
```

### Priority
1. Results Management (High)
   - Critical for UX clarity
   - Prevents confusion with old results
   - Immediate user feedback

2. Analysis Progress (Medium)
   - Enhances user experience
   - Better progress visibility
   - Helps with long-running analyses

3. Ollama Status (Low)
   - Nice to have for debugging
   - Helps with troubleshooting
   - System health monitoring

### Notes
- All features should maintain existing UI consistency
- Progress updates should be efficient and not impact performance
- Status checks should be non-blocking and handle errors gracefully
- Consider adding configuration options for refresh intervals

## Future Enhancements (Planned)
- [ ] User authentication
- [ ] Save favorite prompts
- [ ] Export analysis history
- [ ] Batch processing
- [ ] API endpoint for programmatic access
- [ ] Advanced model configuration options
- [ ] Custom model integration
- [ ] Result sharing functionality

## Architecture

### Components

1. **Flask Backend**
   - Handles HTTP requests and responses
   - Manages model selection and analysis
   - Provides Server-Sent Events (SSE) for streaming responses
   - Manages history and configuration

2. **Frontend**
   - HTML/CSS/JavaScript implementation
   - Real-time response display
   - Interactive UI elements
   - Responsive design with Tailwind CSS

3. **Managers**
   - `FetchManager`: Handles Ollama API interactions
   - `HistoryManager`: Manages prompt history and suggestions

### Data Flow

1. **Model Selection**
   - Frontend fetches available models
   - User selects a model
   - Selection stored for the session

2. **Prompt Handling**
   - User enters prompt or selects from suggestions
   - Prompt sent to backend
   - Backend processes with selected model
   - Response streamed back to frontend

3. **History Management**
   - Successful prompts stored in history
   - History used for prompt suggestions
   - Configurable history limits

## Features

### Implemented

1. **Model Management**
   - List available models
   - Model selection and persistence
   - Model type detection (text/vision)

2. **Prompt System**
   - Default prompts by model type
   - Prompt suggestions from history
   - Customizable suggestions

3. **Analysis**
   - Text analysis with streaming response
   - Image analysis with file upload
   - Real-time response display
   - Abort functionality

4. **History**
   - Configurable history storage
   - History-based suggestions
   - Clear history option

5. **UI/UX**
   - Responsive design
   - Loading indicators
   - Error handling
   - Debug logging

### Planned

1. **Enhanced Model Management**
   - Model tags and filtering
   - Model details display
   - Model performance metrics

2. **Advanced Prompt Features**
   - Prompt templates
   - Parameter customization
   - Batch processing

3. **History Enhancements**
   - Search and filter history
   - Export/import history
   - History analytics

4. **UI Improvements**
   - Dark mode support
   - Mobile optimization
   - Keyboard shortcuts
   - Customizable layout

## Technical Details

### API Endpoints

1. **Model Management**
   - `GET /`: Main application page
   - `POST /fetch/models`: Get available models
   - `POST /select_model`: Select active model

2. **Analysis**
   - `POST /analyze`: Process prompt with model
   - `POST /abort`: Abort current analysis

3. **History**
   - `POST /clear_history`: Clear history
   - History stored in JSON file

### Configuration

1. **Environment Variables**
   - `FLASK_PORT`: Application port
   - `OLLAMA_HOST`: Ollama API host
   - `HISTORY_FILE`: History storage path
   - `MAX_HISTORY_ENTRIES`: History limit
   - `HISTORY_PROMPT_LIMIT`: Suggestion limit

2. **File Structure**
   - `app.py`: Main application
   - `fetch_manager.py`: API handling
   - `history_manager.py`: History management
   - `prompts.json`: Default prompts
   - `config.py`: Configuration

## Testing

1. **Unit Tests**
   - Manager functionality
   - Route handling
   - Configuration loading

2. **Integration Tests**
   - API interactions
   - History management
   - Model selection

3. **UI Tests**
   - Component rendering
   - User interactions
   - Response handling

## Security

1. **Implemented**
   - CSRF protection
   - Input validation
   - Error handling
   - File upload restrictions

2. **Planned**
   - Authentication
   - Rate limiting
   - API key management
   - Session management

## Contributing

1. **Guidelines**
   - Follow Python style guide
   - Write tests for new features
   - Update documentation
   - Use descriptive commit messages

2. **Process**
   - Fork repository
   - Create feature branch
   - Submit pull request
   - Review and merge

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Ollama API Documentation](https://github.com/jmorganca/ollama/blob/main/docs/api.md)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
