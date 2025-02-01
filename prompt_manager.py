import json
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class PromptManager:
    default_prompt: str
    prompt_suggestions: List[str]
    
    @classmethod
    def load_prompts(cls, model_type: str = 'text') -> 'PromptManager':
        """Load prompts from the prompts.json file based on model type."""
        try:
            with open('prompts.json', 'r') as f:
                prompts_data = json.load(f)
                
            model_key = f"{model_type}_models"
            if model_key in prompts_data:
                return cls(
                    default_prompt=prompts_data[model_key].get('default', ''),
                    prompt_suggestions=prompts_data[model_key].get('suggestions', [])
                )
            else:
                return cls(default_prompt='', prompt_suggestions=[])
        except (FileNotFoundError, json.JSONDecodeError):
            return cls(default_prompt='', prompt_suggestions=[])

    def get_default_prompt(self) -> str:
        """Get the default prompt."""
        return self.default_prompt

    def get_prompt_suggestions(self) -> List[str]:
        """Get the list of prompt suggestions."""
        return self.prompt_suggestions

    def validate_prompt(self, prompt: str) -> Optional[str]:
        """
        Validate a prompt string.
        Returns None if valid, error message if invalid.
        """
        if not prompt or not prompt.strip():
            return "Prompt cannot be empty"
        if len(prompt) > 2000:  # Example limit
            return "Prompt is too long (max 2000 characters)"
        return None
