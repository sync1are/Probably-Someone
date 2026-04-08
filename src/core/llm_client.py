"""Ollama LLM client setup and management."""

from ollama import chat


class LLMClient:
    """Wrapper for Ollama API client."""

    def __init__(self):
        pass

    def chat(self, model, messages, tools=None, stream=False):
        """Send a chat request to the Ollama API."""
        # Note: Do not pass think=True to Ollama when using tools,
        # as it causes a 400 ResponseError with Gemini models
        return chat(
            model=model,
            messages=messages,
            tools=tools,
            stream=stream
        )
