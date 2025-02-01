import logging
import requests
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FetchManager:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        
    def fetch_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Fetch information about a specific model."""
        try:
            response = requests.get(f"{self.base_url}/api/show", 
                                  params={"name": model_name},
                                  timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching model info: {e}")
            return None
            
    def fetch_models_list(self) -> Optional[Dict[str, Any]]:
        """Fetch list of local models from Ollama."""
        try:
            # Use the ollama CLI to get local models
            import subprocess
            import re
            
            logger.info("Fetching local models using ollama list")
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, 
                                  text=True)
            if result.returncode != 0:
                raise Exception(f"ollama list failed: {result.stderr}")
                
            # Parse the output
            models = []
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Skip header if present
                for line in lines[1:]:
                    if line.strip():
                        # Parse space-separated columns
                        parts = re.split(r'\s{2,}', line.strip())
                        if len(parts) >= 4:
                            name, model_id, size, modified = parts[:4]
                            name = name.split(':')[0]  # Remove version tag
                            models.append({
                                'name': name,
                                'model': name,
                                'modified_at': modified,
                                'size': size,
                                'details': {
                                    'id': model_id,
                                    'size': size,
                                    'modified_at': modified
                                }
                            })
            
            logger.info(f"Transformed local models data: {models}")
            return {'models': models}
        except Exception as e:
            logger.error(f"Error fetching local models list: {e}")
            return None

    def get_library_models(self) -> Optional[Dict[str, Any]]:
        """Get available models from Ollama library."""
        try:
            # Fetch models from Ollama library API
            logger.info("Fetching models from Ollama library")
            response = requests.get("https://ollama.com/library/models")
            response.raise_for_status()
            
            # Parse response
            library_data = response.json()
            logger.info(f"Received library data: {library_data}")
            
            # Transform to our format
            models = []
            if 'models' in library_data:
                for model in library_data['models']:
                    name = model['name'].split(':')[0]  # Remove version tag
                    models.append({
                        'name': name,
                        'description': model.get('description', ''),
                        'details': {
                            'format': model.get('format', ''),
                            'family': model.get('family', ''),
                            'parameter_size': model.get('parameter_size', ''),
                            'quantization': model.get('quantization', '')
                        }
                    })
            
            logger.info(f"Transformed library models: {models}")
            return {"models": models}
        except Exception as e:
            logger.error(f"Error getting library models: {e}")
            # Fallback to curated list if API fails
            models = [
                {"name": "llama2", "description": "Meta's Llama 2 model"},
                {"name": "mistral", "description": "Mistral 7B model"},
                {"name": "codellama", "description": "Code specialized Llama model"},
                {"name": "llama2-uncensored", "description": "Uncensored version of Llama 2"},
                {"name": "neural-chat", "description": "Intel's neural chat model"},
                {"name": "starling-lm", "description": "Starling LM model"},
                {"name": "dolphin-phi", "description": "Dolphin Phi model"},
                {"name": "llava", "description": "Multimodal model supporting vision"},
                {"name": "orca-mini", "description": "Lightweight Orca model"},
                {"name": "vicuna", "description": "Vicuna model based on LLaMA"},
                {"name": "falcon", "description": "TII's Falcon model"},
                {"name": "stable-beluga", "description": "Stable Beluga model"}
            ]
            return {"models": models}

    def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull a model from Ollama library."""
        try:
            # Pull the model using Ollama API
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=None
            )
            response.raise_for_status()
            
            # Stream the response
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    # Add status field if not present
                    if 'status' not in data:
                        data['status'] = 'downloading'
                    yield data
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            raise
