# Llama Vision

A web application that leverages Ollama's vision-capable models to analyze images. Built with Flask and modern web technologies, this application provides an intuitive interface for image analysis using various vision models.

## Features

- 🖼️ **Image Analysis**: Upload and analyze images using vision-capable language models
- 🤖 **Multiple Models**: Support for various vision models (llama2-vision, llama3.2-vision, etc.)
- 🔄 **Real-time Model Discovery**: Automatically discovers available models from your local Ollama installation
- 📝 **Quick Prompts**: Pre-defined prompts for common analysis tasks:
  - Describe Image
  - List Objects
  - Read Text
  - Main Subject
- 🔍 **Debug Levels**: Adjustable logging levels for debugging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ⏳ **Loading Indicators**: Visual feedback during image analysis
- 🏠 **Home Button**: Easy navigation and form reset

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.ai/) installed and running
- At least one vision-capable model installed (e.g., llama2-vision, llama3.2-vision)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd llama-vision
   ```

2. Install dependencies using `uv`:
   ```bash
   uv pip install -e .
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

3. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. **Select a Model**:
   - Choose from available models in the dropdown
   - Click the refresh button to update the model list
   - Models are automatically discovered from your Ollama installation

2. **Upload an Image**:
   - Click "Choose File" to select an image
   - Supported formats: PNG, JPEG, etc.

3. **Choose or Enter a Prompt**:
   - Select from pre-defined prompts:
     - "Describe Image": Get a general description
     - "List Objects": Identify objects in the image
     - "Read Text": Extract text from the image
     - "Main Subject": Identify the main focus
   - Or enter your custom prompt

4. **Analyze**:
   - Click "Analyze Image" to process
   - Wait for the results to appear
   - Loading indicator shows progress

5. **Debug (if needed)**:
   - Adjust the debug level using the buttons at the top
   - Check the console for detailed logs

## Project Structure

```
llama-vision/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Web interface template
├── uploads/            # Temporary image storage
├── pyproject.toml      # Project dependencies
└── README.md          # This file
```

## Dependencies

- Flask: Web framework
- Flask-WTF: Form handling and CSRF protection
- Werkzeug: WSGI utilities
- Ollama: Vision model integration
- Requests: HTTP client for API calls
- TailwindCSS: Styling (via CDN)

## Debug Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about program execution
- **WARNING**: Indicates a potential problem
- **ERROR**: Error events that might still allow the application to continue
- **CRITICAL**: Serious errors that may prevent the application from running

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.