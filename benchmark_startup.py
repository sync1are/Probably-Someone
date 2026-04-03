"""Quick startup benchmark to test initialization speed."""

import time
print("Starting benchmark...")

start = time.time()

from src.core.audio_engine import AudioEngine
from src.core.llm_client import LLMClient
from src.tools.registry import execute_tool
import json

with open('tools.json', 'r') as f:
    tools = json.load(f)['tools']

llm_client = LLMClient()
audio_engine = AudioEngine()

init_time = time.time() - start

print(f"\n✓ App initialized in {init_time:.2f} seconds")
print(f"  - LLM Client: Ready")
print(f"  - Audio Engine: {'Ready' if audio_engine.pipeline_ready else 'Loading in background...'}")
print(f"  - Tools Loaded: {len(tools)}")

# Wait a moment to see if TTS finishes
time.sleep(3)
print(f"  - Audio Engine: {'Ready' if audio_engine.pipeline_ready else 'Still loading...'}")

audio_engine.shutdown()
