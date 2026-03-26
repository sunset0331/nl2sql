"""
OpenAI SDK Client for Z.AI API

Wrapper for OpenAI SDK compatible with Z.AI's API endpoint.
Uses glm-4.7-flash model via Z.AI's OpenAI-compatible API.
"""

from openai import OpenAI
from config import ZAI_API_KEY, MODEL_NAME, MAX_NEW_TOKENS, TEMPERATURE


class OpenAIClient:
    """Client for Z.AI API using OpenAI SDK."""
    
    def __init__(self):
        if not ZAI_API_KEY:
            raise ValueError(
                "Z.AI API key not found!\n"
                "Please add your API key to the .env file:\n"
                "ZAI_API_KEY=your-Z.AI-api-key\n\n"
                "Get your API key from: https://z.ai"
            )
        
        self.client = OpenAI(
            api_key=ZAI_API_KEY,
            base_url="https://api.z.ai/api/paas/v4/",
        )
        self.model = MODEL_NAME
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = MAX_NEW_TOKENS,
        temperature: float = TEMPERATURE,
        system_prompt: str = None
    ) -> str:
        """
        Generate text using the Z.AI API via OpenAI SDK.
        
        Args:
            prompt: The input prompt for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            system_prompt: Optional system prompt to set context
            
        Returns:
            Generated text response
        """
        try:
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add user prompt
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                raise ValueError(
                    "Invalid Z.AI API key. "
                    "Please check your API key in the .env file."
                )
            elif "rate" in error_msg.lower() or "429" in error_msg:
                raise ValueError(
                    "Rate limit exceeded. Please wait a moment and try again."
                )
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise ValueError(
                    f"Model '{self.model}' not found. "
                    "Please check your model name in the .env file."
                )
            else:
                raise ValueError(f"API Error: {error_msg}")


# Singleton instance
_client = None

def get_client() -> OpenAIClient:
    """Get or create the OpenAI client singleton."""
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client
