# Llama Vision

A web application that leverages Ollama's models to analyze both images and documents. Built with Flask and modern web technologies, this application provides an intuitive interface for AI-powered analysis using various models.

## Features

- 🖼️ **Universal Analysis**: Support for both images and documents
  - Vision models: Analyze images with state-of-the-art vision capabilities
  - Text models: Process documents and text with advanced language models
- 🤖 **Multiple Models**: Support for various models (llama2, llava, etc.)
- 🔄 **Real-time Model Discovery**: Automatically discovers available models from your local Ollama installation
- 📝 **Dynamic Prompts**: Context-aware prompts based on model type
- 🔍 **Debug Levels**: Adjustable logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- 📊 **Analysis History**: 
  - Persistent storage in query_history.json
  - Complete history of all analyses
  - Reuse previous prompts
  - Clear history option
  - Timestamps and duration tracking
  - Success/Error status
  - Collapsible results view
- 💾 **Session Persistence**: 
  - Selected model persists across refreshes
  - Debug level settings are maintained
- ⏳ **Progress Indication**: 
  - Analyze button shows active state
  - Context-aware loading messages
  - Visual loading spinner
  - Button disabled during analysis
- 🏠 **Home Navigation**: Easy navigation with modern UI

## Prerequisites

- Python 3.10 (managed by pyenv)
- [Ollama](https://ollama.ai/) installed and running
- At least one model installed (e.g., llama2, llava)
- [uv](https://astral.sh/uv) package manager

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd llama-vision
   ```

2. Ensure correct Python version:
   ```bash
   # Verify Python version matches .python-version
   python --version  # Should show Python 3.10.x
   ```

3. Install dependencies using `uv`:
   ```bash
   uv install
   ```

## Running the Application

1. Ensure Ollama is running:
   ```bash
   ollama list  # Should show your installed models
   ```

2. Start the Flask application:
   ```bash
   uv run app.py
   ```
   The application will be available at http://127.0.0.1:5000

## Usage

1. **Select a Model**:
   - Choose from available models in the dropdown
   - Click the refresh button to update the model list
   - Models are automatically discovered from your Ollama installation

2. **Upload a File** (if needed):
   - For vision models:
     - Required file upload
     - Supported formats: JPG, PNG, GIF, BMP, WebP
   - For text models:
     - Optional file upload
     - Supported formats: TXT, MD, PDF, DOC, DOCX, CSV, JSON

3. **Enter or Select a Prompt**:
   - Dynamic prompt suggestions based on model type
   - Custom prompt input available
   - Clear prompt guidance based on model capabilities

4. **Analyze**:
   - Click "Analyze" to process
   - View progress with loading indicator
   - See timing information in results

5. **View History**:
   - Scroll through previous analyses
   - Expand/collapse results as needed
   - See timing and model information
   - Track success/error status

6. **Debug Settings**:
   - Adjust debug level via dropdown
   - Settings persist across sessions
   - Clear visual feedback for current level

## Configuration

The application can be configured using environment variables or a `.env` file. Copy the example `.env` file and modify as needed:

```bash
cp .env.example .env
```

Available configuration options:

```ini
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here    # Secret key for session management
FLASK_DEBUG=True                         # Enable/disable debug mode

# File Storage
UPLOAD_FOLDER=uploads                    # Directory for uploaded files
HISTORY_FILE=query_history.json          # File to store analysis history
MAX_HISTORY_ENTRIES=100                  # Maximum number of history entries to keep

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434       # Ollama API host

# Prompts Configuration
PROMPTS_FILE=prompts.json                # File containing model prompts
```

All configuration values have sensible defaults in `config.py` if not specified in the environment.

### Customizing Prompts

The application loads model prompts from a JSON file specified by `PROMPTS_FILE`. The file should have the following structure:

```json
{
  "vision_models": {
    "default": "Default prompt for vision models",
    "suggestions": [
      "Prompt suggestion 1",
      "Prompt suggestion 2",
      ...
    ]
  },
  "text_models": {
    "default": "Default prompt for text models",
    "suggestions": [
      "Prompt suggestion 1",
      "Prompt suggestion 2",
      ...
    ]
  }
}
```

To customize the prompts:
1. Copy the default `prompts.json` file
2. Modify the prompts as needed
3. Update `PROMPTS_FILE` in your `.env` file if using a different filename

## Project Structure

```
llama-vision/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Web interface template
├── design.md           # Design documentation
├── uploads/            # Temporary file storage
├── pyproject.toml      # Project dependencies
└── README.md          # This file
```

## Dependencies

- Flask: Web framework
- Flask-WTF: Form handling and CSRF protection
- Werkzeug: WSGI utilities
- Ollama: Model integration
- Requests: HTTP client for API calls
- Tailwind CSS: Styling and UI components

## Security Features

- CSRF protection enabled
- Secure file handling with cleanup
- File type validation
- File size limits
- Session-based persistence

## Contributing

Please see our [design document](design.md) for current features and planned enhancements. Contributions are welcome!