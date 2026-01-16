import os
import time
import logging
import requests
from typing import Tuple

logger = logging.getLogger(__name__)

class MistralLLMService:
    """Mistral API Service адаптирован из твоего test_llm_apis.py"""
    
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY")
        self.endpoint = "https://api.mistral.ai/v1/chat/completions"
        self.model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        
        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY not set. Export: export MISTRAL_API_KEY='9o53IMvQriQhygYjnnGy068D8ZRiv3TO'"
            )
        
        logger.info(f"OK Инициализирован Mistral LLM (model: {self.model})")
    
    def call_mistral_api(
        self,
        prompt: str,
        max_retries: int = 3,
        temperature: float = 0.3
    ) -> Tuple[str, bool]:

        # с логикой retry
        # Returns: (response_text, success)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2500
        }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Mistral API call (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result['choices'][0]['message']['content']
                    logger.info(f"OK Mistral ответ получен ({len(text)} chars)")
                    return text, True
                
                elif response.status_code == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limit hit. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    error_text = response.text[:200]
                    logger.error(f"Mistral error {response.status_code}: {error_text}")
                    return f"Error {response.status_code}: {error_text}", False
            
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"Timeout. Retrying...")
                    time.sleep(2 ** attempt)
                    continue
                return "Timeout error", False
            
            except Exception as e:
                logger.error(f"Exception: {str(e)}")
                return f"Exception: {str(e)[:100]}", False
        
        return "Max retries exceeded", False
