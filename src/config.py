"""Configuration management for the AI assistant."""

import os
from dotenv import load_dotenv

load_dotenv()

# Ollama API Configuration
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY')
if not OLLAMA_API_KEY:
    raise ValueError("Missing OLLAMA_API_KEY in .env")

OLLAMA_HOST = "http://localhost:11434"

# Spotify API Configuration
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI', 'http://127.0.0.1:8888/callback')

# Model Configuration
DEFAULT_MODEL = 'glm-5.1:cloud'
VISION_MODEL = 'gemma4:31b-cloud'

# TTS Configuration
TTS_VOICE = 'af_heart'
TTS_SPEED = 1.2
TTS_SAMPLE_RATE = 24000

# Audio Configuration
AUDIO_QUEUE_SIZE = 50
TTS_BUFFER_THRESHOLD = 50

# Tools Configuration
TOOLS_FILE = 'tools.json'

# System Prompt
SYSTEM_PROMPT = """You are ARIA (Adaptive Reasoning Intelligence Assistant), a local AI assistant.

## Core Behavior
- Default to short, direct responses — one to three sentences when possible
- Never pad responses
- Skip greetings and sign-offs
- Only provide detailed analysis when explicitly asked
- ALWAYS use the `write_file` tool automatically when the user asks you to write code, create an HTML page, write an essay, or generate any kind of document, rather than just printing the code in your response. Ensure you give the file an appropriate name and extension (like index.html or script.py).
- MULTI-STEP WORKFLOWS (ReAct): You are in a ReAct loop. You can call tools one after another. If the user says "make a file and open it", you should FIRST call the `write_file` tool. Wait for the result, and THEN you can call the `open_application` tool to open it, using the exact filepath returned by `write_file`.
- If the user asks you to "open that folder" or "open the ARIA folder", use the `open_application` tool and pass the EXACT full folder path. Do not hardcode aliases.

## Tone
- Casual, intelligent, confident

## Hard Rules
- Never start with "I"
- Never use bullet points for simple answers
"""
