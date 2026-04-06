import sys
import os
import json
from src.config import SYSTEM_PROMPT, DEFAULT_MODEL, TOOLS_FILE, GOOGLE_API_KEY
from src.core.llm_client import LLMClient
from src.core.google_client import GoogleClient
from src.core.audio_engine import AudioEngine, StreamingTextProcessor
from src.tools.registry import execute_tool

