"""Ollama LLM client setup and management."""

from ollama import Client
from src.config import OLLAMA_HOST, OLLAMA_API_KEY


class LLMClient:
    """Wrapper for Ollama API client."""
    
    def __init__(self):
        self.client = Client(
            host=OLLAMA_HOST,
            headers={'Authorization': f'Bearer {OLLAMA_API_KEY}'}
        )
    
    def chat(self, model, messages, tools=None, stream=False):
        """Send a chat request to the Ollama API."""
        return self.client.chat(
            model=model,
            messages=messages,
            tools=tools,
            stream=stream
        )
