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

## Future Enhancements (Planned)
- [ ] User authentication
- [ ] Save favorite prompts
- [ ] Export analysis history
- [ ] Batch processing
- [ ] API endpoint for programmatic access
- [ ] Advanced model configuration options
- [ ] Custom model integration
- [ ] Result sharing functionality
