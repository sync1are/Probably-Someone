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
DEFAULT_MODEL = 'gemma4:e2b'
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

## Tone
- Casual, intelligent, confident

## Hard Rules
- Never start with "I"
- Never use bullet points for simple answers
"""
