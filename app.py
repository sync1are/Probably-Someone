"""
ARIA Voice Assistant - Main Entry Point
Refactored modular architecture with Spotify integration
"""

import json
import toml
import sys
import codecs
import time
import re
import asyncio
from src.config import SYSTEM_PROMPT, NVIDIA_SYSTEM_PROMPT, DEFAULT_MODEL, NVIDIA_MODEL, LM_STUDIO_MODEL, TOOLS_FILE
from src.core.llm_client import LLMClient

# Set standard output encoding to utf-8 to prevent charmap errors in Windows
if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
if hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'utf-8':
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
from src.core.audio_engine import AudioEngine, StreamingTextProcessor
from src.core.asr_engine import ASREngine
from src.tools.registry import execute_tool
from src.core.agent import Agent
from src.discord_bridge import init_discord


def load_tools():
    """Load tool definitions from tools.toml."""
    with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
        tools_data = toml.load(f)
        tools = tools_data.get('tools', [])
        for t in tools:
            if 'parameters' in t.get('function', {}):
                if 'properties' not in t['function']['parameters']:
                    t['function']['parameters']['properties'] = {}
        return tools


# Global components
messaging_controller = None
autonomy_engine = None

async def main():
    global messaging_controller, autonomy_engine
    global DEFAULT_MODEL

    """Main application loop."""
    print("Welcome to ARIA.")
    print("Please select your AI backend:")
    print("1. Ollama (Local - Default)")
    print("2. NVIDIA NIM (Cloud)")
    print("3. LM Studio (Local)")
    
    choice = input("\nEnter choice (1, 2, or 3): ").strip()
    if choice == '2':
        backend = "nvidia"
        DEFAULT_MODEL = NVIDIA_MODEL
        active_system_prompt = NVIDIA_SYSTEM_PROMPT
        print(f"Selected NVIDIA NIM  ({NVIDIA_MODEL}).\n")
    elif choice == '3':
        backend = "lm_studio"
        DEFAULT_MODEL = LM_STUDIO_MODEL
        active_system_prompt = SYSTEM_PROMPT
        print(f"Selected LM Studio ({LM_STUDIO_MODEL}).\n")
    else:
        backend = "ollama"
        active_system_prompt = SYSTEM_PROMPT
        print("Selected Ollama.\n")

    # Hardcoded Browser Preferences based on user request
    browser_headless = False
    browser_model = DEFAULT_MODEL
    browser_backend = backend

    # Initialize components
    audio_engine = AudioEngine()
    asr_engine = ASREngine(hotkey='ctrl+shift')
    tools = load_tools()
    
    # Initialize unified Agent
    agent = Agent(
        backend=backend,
        model=DEFAULT_MODEL,
        system_prompt=active_system_prompt,
        tools=tools,
        browser_headless=browser_headless,
        browser_backend=browser_backend,
        browser_model=browser_model
    )

    # Initialize messaging system
    from src.messaging.controller import MessagingController
    from src.messaging.autonomy_engine import AutonomyEngine

    # Start background services
    asr_engine.start_background_listener()
    messaging_controller = MessagingController()
    autonomy_engine = AutonomyEngine(messaging_controller)
    
    # Start Discord Bridge
    init_discord(backend=backend, model=DEFAULT_MODEL)

    print("🤖 ARIA Voice Assistant Started!")
    print("🎙️ Hold [Ctrl + Shift] anytime to speak")
    print("📸 Screenshot tool enabled")
    print("🎵 Spotify controls enabled")
    print("Type 'quit' or 'exit' to stop\n")

    # Check for pending messages on boot
    from src.tools.messaging_tools import get_pending_messages
    pending = get_pending_messages(clear=True)
    if pending and pending.get('success') and pending.get('messages'):
        welcome_msg = pending.get('message')
        print(f"🤖 AI: {welcome_msg}\n")
        audio_engine.queue_text(welcome_msg)
        audio_engine.signal_done()

    try:
        while True:
            # Use asyncio.to_thread for blocking input() in an async loop
            user_input = await asyncio.to_thread(input, "You: ")
            user_input = user_input.strip()

            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            # Interrupt any currently playing audio when user sends a new message
            audio_engine.interrupt()

            # --- UNIFIED AGENT PATH ---
            _t_start = time.time()
            print("⏳ AI is thinking...", end="\r", flush=True)
            
            # Setup callbacks for the agent
            processor = StreamingTextProcessor(audio_engine)
            first_chunk = True

            def output_callback(content):
                nonlocal first_chunk
                if first_chunk:
                    print("\r\033[K🤖 AI: ", end="", flush=True)
                    first_chunk = False
                print(content, end='', flush=True)
                processor.process_chunk(content)

            def tool_callback(name, args):
                print(f"\n🔧 Using tools...")
                print(f"  → Calling {name}...")

            def tool_result_callback(name, result):
                if result.get('success'):
                    print(f"  ✓ {name} completed")
                else:
                    err = result.get('error') or result.get('message') or "Unknown error"
                    print(f"  ✗ {name} failed: {err}")
                
                # Check for is_writing_code scenario
                if name == 'write_file':
                    print("\n⏳ Generating code and saving file...", end="\n", flush=True)
                else:
                    print("\n⏳ Generating response...", end="", flush=True)

            try:
                # Run the agent directly with await since we are already in the loop
                message = await agent.run(
                    user_input, 
                    output_callback, 
                    tool_callback, 
                    tool_result_callback
                )
                
                processor.flush()
                audio_engine.signal_done()
                if not first_chunk:
                    print("\n")
                
            except KeyboardInterrupt:
                print("\n[Interrupted]\n")
                continue
            except Exception as e:
                print(f"\n❌ Error in agent loop: {e}")
                continue

            _t_total = time.time() - _t_start
            
            # Print token stats if available
            p_tokens = message.get("prompt_tokens", 0)
            e_tokens = message.get("eval_tokens", 0)
            token_str = ""
            if p_tokens or e_tokens:
                token_str = f" · Tokens: {p_tokens} prompt / {e_tokens} compl"
            
            print(f"✓ Done ({_t_total:.1f}s total{token_str})\n")
    
    finally:
        audio_engine.shutdown()
        asr_engine.stop_background_listener()

        # Kill the background messaging processes cleanly when the app closes
        if messaging_controller:
            from src.tools.messaging_tools import _messaging_processes
            for name, process in _messaging_processes.items():
                if process and process != "Already running" and hasattr(process, 'terminate'):
                    try:
                        print(f"Shutting down {name}...")
                        process.terminate()
                    except Exception as e:
                        pass


if __name__ == "__main__":
    asyncio.run(main())
