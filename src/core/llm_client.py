"""Ollama LLM client setup and management."""

from ollama import chat


class LLMClient:
    """Wrapper for Ollama API client."""

    def __init__(self):
        pass

    def chat(self, model, messages, tools=None, stream=False, think=False):
        """Send a chat request to the Ollama API."""
        return chat(
            model=model,
            messages=messages,
            tools=tools,
            stream=stream,
            think=think
        )
