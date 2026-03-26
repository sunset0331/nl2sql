"""
HuggingFace Inference API Client

Wrapper for HuggingFace's free Inference API for text generation.
"""

from huggingface_hub import InferenceClient
from config import HF_API_TOKEN, MODEL_NAME, MAX_NEW_TOKENS, TEMPERATURE


class HuggingFaceClient:
    """Client for HuggingFace Inference API."""
    
    def __init__(self):
        if not HF_API_TOKEN:
            raise ValueError(
                "HuggingFace API token not found!\n"
                "Please add your token to the .env file:\n"
                "HF_API_TOKEN=hf_your_token_here\n\n"
                "Get a free token at: https://huggingface.co/settings/tokens"
            )
        
        self.client = InferenceClient(token=HF_API_TOKEN)
        self.model = MODEL_NAME
    
    def generate_text(
        self,
        prompt: str,
        max_tokens: int = MAX_NEW_TOKENS,
        temperature: float = TEMPERATURE
    ) -> str:
        """
        Generate text using the HuggingFace Inference API.
        
        Args:
            prompt: The input prompt for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (lower = more deterministic)
            
        Returns:
            Generated text response
        """
        try:
            # Format as instruction for Mistral
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat_completion(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                raise ValueError(
                    "Invalid HuggingFace API token. "
                    "Please check your token in the .env file."
                )
            elif "rate" in error_msg.lower():
                raise ValueError(
                    "Rate limit exceeded. Please wait a moment and try again."
                )
            else:
                raise ValueError(f"API Error: {error_msg}")


# Singleton instance
_client = None

def get_client() -> HuggingFaceClient:
    """Get or create the HuggingFace client singleton."""
    global _client
    if _client is None:
        _client = HuggingFaceClient()
    return _client
