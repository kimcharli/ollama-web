import logging
import subprocess
import json
from typing import Dict, Any, Optional, Generator
from config import Config

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self):
        self.base_url = Config.OLLAMA_HOST

    def pull_model(self, model_name: str) -> Generator[Dict[str, Any], None, None]:
        """Pull a model from Ollama library using ollama CLI.
        
        Args:
            model_name: Name of the model to pull
            
        Yields:
            Dictionary containing progress information:
            {
                'status': str,  # Current status (downloading, verifying, etc.)
                'progress': float,  # Progress percentage (0-100)
                'total': int,  # Total size in bytes
                'completed': int,  # Completed size in bytes
                'error': str,  # Error message if any
            }
        """
        try:
            # Run ollama pull command
            process = subprocess.Popen(
                ['ollama', 'pull', model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Process output line by line
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    try:
                        # Parse JSON progress output
                        data = json.loads(line)
                        status = data.get('status', '')
                        
                        if 'error' in data:
                            yield {
                                'status': 'error',
                                'error': data['error']
                            }
                            break
                            
                        if status == 'downloading manifest':
                            yield {
                                'status': 'downloading manifest',
                                'progress': 0
                            }
                        elif status == 'downloading' or status == 'verifying':
                            total = int(data.get('total', 0))
                            completed = int(data.get('completed', 0))
                            progress = (completed / total * 100) if total > 0 else 0
                            
                            yield {
                                'status': status,
                                'progress': progress,
                                'total': total,
                                'completed': completed
                            }
                        elif status == 'done':
                            yield {
                                'status': 'done',
                                'progress': 100
                            }
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse line as JSON: {line}")
                        continue

            # Check for any errors
            if process.poll() != 0:
                error = process.stderr.read()
                yield {
                    'status': 'error',
                    'error': error or 'Unknown error occurred'
                }
                
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            yield {
                'status': 'error',
                'error': str(e)
            }
