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


def stream_response(response, audio_engine, is_code=False):
    """Stream LLM response and handle TTS."""
    full_response = ""
    processor = StreamingTextProcessor(audio_engine)

    # If it's generating code/file content, show a different indicator
    if is_code:
        print("🤖 AI: ", end="", flush=True)
    else:
        # Flag to clear the "Generating text..." message on first chunk
        first_chunk = True

    for part in response:
        chunk = part.get('message', {}).get('content', '') or ''

        if not is_code and first_chunk:
            # We use \r to overwrite the "Generating text..." line, clearing the whole line
            print("\r\033[K🤖 AI: ", end="", flush=True)
            first_chunk = False

        print(chunk, end='', flush=True)

        full_response += chunk
        processor.process_chunk(chunk)

    print("\n")
    processor.flush()

    # Strip any raw XML tool_call tags the model may have leaked into its text response
    cleaned = re.sub(r'<tool_call>.*?</tool_call>', '', full_response, flags=re.DOTALL)
    cleaned = re.sub(r'<?function=.*?(?:</tool_call>|</function>)', '', cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()

    return cleaned


def stream_and_reconstruct(response_stream, audio_engine):
    """
    Consumes a streaming LLM response, printing text live to the console,
    sending text chunks to the TTS engine, and reconstructing the final
    message dictionary containing both the complete text and any tool calls.
    """
    full_content = ""
    tool_calls = []
    processor = StreamingTextProcessor(audio_engine)
    first_chunk = True

    for chunk in response_stream:
        msg = chunk.get('message', {})

        # Accumulate tool calls if they exist in the chunk
        if msg.get('tool_calls'):
            tool_calls = msg['tool_calls']

        content = msg.get('content', '')
        if content:
            if first_chunk:
                print("\r\033[K🤖 AI: ", end="", flush=True)
                first_chunk = False
            print(content, end='', flush=True)
            full_content += content
            processor.process_chunk(content)

    processor.flush()
    if full_content:
        print("\n")

    cleaned_content = full_content
    cleaned_content = re.sub(r'<tool_call>.*?</tool_call>', '', cleaned_content, flags=re.DOTALL)
    cleaned_content = re.sub(r'<?function=.*?(?:</tool_call>|</function>)', '', cleaned_content, flags=re.DOTALL)
    cleaned_content = cleaned_content.strip()

    return {
        "role": "assistant",
        "content": cleaned_content,
        "tool_calls": tool_calls if tool_calls else None
    }


def process_tool_calls(message, conversation_history, llm_client, tools, audio_engine):
    """Process tool calls and return final response or direct output."""
    print("🔧 Using tools...")
    
    # Add assistant message once before processing tool calls
    conversation_history.append(message)
    
    # Tools that should always get direct responses (no LLM needed)
    direct_response_tools = ['spotify_pause', 'spotify_skip_next', 'spotify_skip_previous',
                             'spotify_shuffle', 'spotify_repeat', 'spotify_volume',
                             'spotify_like_current', 'spotify_unlike_current', 'set_system_volume',
                             'adjust_system_volume', 'toggle_system_mute', 'smart_media_control',
                             'set_system_brightness', 'adjust_system_brightness', 'minimize_window',
                             'maximize_window', 'close_window', 'switch_to_window', 'show_desktop', 'open_application']
    
    # Tools that need LLM for natural language responses
    llm_response_tools = ['spotify_play', 'spotify_add_to_queue', 'spotify_current_track',
                          'get_important_unread_emails', 'read_specific_email']

    # We want a direct response ONLY if all tools are in the direct list
    all_direct = all(
        tool_call['function']['name'] in direct_response_tools
        for tool_call in message['tool_calls']
    )
    
    direct_responses = []
    needs_llm = False
    
    for tool_call in message['tool_calls']:
        tool_name = tool_call['function']['name']
        tool_args = tool_call['function']['arguments']

        # Look in the conversation history for any previously generated file paths
        # This handles cross-turn dependencies (ReAct loop) as well as same-turn dependencies
        if isinstance(tool_args, dict):
            for prev_msg in reversed(conversation_history):
                if prev_msg.get('role') == 'tool':
                    try:
                        prev_res = json.loads(prev_msg.get('content', '{}'))
                        if prev_res.get('success') and 'filepath' in prev_res.get('data', {}):
                            prev_path = prev_res['data']['filepath']
                            # Look for the filename inside the arguments and replace it with the path
                            for key, val in tool_args.items():
                                if isinstance(val, str) and len(val) > 2 and val in prev_path:
                                    # If the argument is just "index.html" but the full path is "C:\...\index.html", swap it!
                                    tool_args[key] = prev_path
                    except Exception:
                        pass

        print(f"  → Calling {tool_name}...")
        tool_result = execute_tool(tool_name, tool_args)
        
        if tool_result.get('success'):
            print(f"  ✓ {tool_name} completed")
            
            # Check if this needs LLM response
            if tool_name in llm_response_tools:
                needs_llm = True
            
            # Check if this can be direct response
            if tool_name in direct_response_tools and all_direct:
                # Direct response without LLM
                response_text = tool_result.get('message', 'Done')
                direct_responses.append(response_text)
                
                # Add to conversation history
                conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps(tool_result)
                })
                conversation_history.append({
                    'role': 'assistant',
                    'content': response_text
                })
            elif tool_name == "take_screenshot" and 'image_base64' in tool_result:
                needs_llm = True
                # Add tool response
                conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps({
                        'success': True,
                        'message': f"Screenshot captured: {tool_result['width']}x{tool_result['height']}"
                    })
                })
                
                # Add image for vision model
                conversation_history.append({
                    'role': 'user',
                    'content': 'Analyze this screenshot.',
                    'images': [tool_result['image_base64']]
                })
            else:
                conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps(tool_result)
                })
        else:
            # Important: Don't let it crash if 'error' key doesn't exist
            err_txt = tool_result.get('error') or tool_result.get('message') or "Unknown error"
            print(f"  ✗ {tool_name} failed: {err_txt}")

            # We always want the LLM to explain why it failed, instead of just printing a python error directly
            needs_llm = True
            conversation_history.append({
                'role': 'tool',
                'content': json.dumps(tool_result)
            })
    
    # If all were direct response tools (pause/skip/previous) and NONE failed, return direct responses
    if all_direct and direct_responses and not needs_llm:
        return None, '\n'.join(direct_responses), False
    
    # Otherwise, get final response from LLM for natural language
    # Check if this is a vision request (has images in conversation)
    has_images = any('images' in msg for msg in conversation_history if isinstance(msg, dict))

    # Check if we were asked to write code/file
    is_writing_code = any(
        tool_call['function']['name'] == 'write_file'
        for tool_call in message['tool_calls']
    )

    if is_writing_code:
        print("\n⏳ Generating code and saving file...", end="\n", flush=True)
    else:
        print("\n⏳ Generating text...", end="", flush=True)

    final_response = llm_client.chat(
        model=DEFAULT_MODEL,
        messages=conversation_history,
        stream=True
    )

    return final_response, None, is_writing_code


# Global components
messaging_controller = None
autonomy_engine = None

def main():
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

    # Initialize components
    llm_client = LLMClient(backend=backend)
    audio_engine = AudioEngine()
    asr_engine = ASREngine(hotkey='ctrl+shift')
    tools = load_tools()

    # Initialize messaging system
    from src.messaging.controller import MessagingController
    from src.messaging.autonomy_engine import AutonomyEngine

    # Start background services
    asr_engine.start_background_listener()
    messaging_controller = MessagingController()
    autonomy_engine = AutonomyEngine(messaging_controller)

    # Initialize conversation
    conversation_history = [{"role": "system", "content": active_system_prompt}]

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
            # ... (rest of the loop)
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
                print("👋 Goodbye!")
                break

            if not user_input:
                continue

            # Interrupt any currently playing audio when user sends a new message
            audio_engine.interrupt()

            # Add user message
            conversation_history.append({
                'role': 'user',
                'content': user_input
            })

            # --- TOOL-AWARE PATH (Ollama + NVIDIA) ---
            # Call is stream=True so we print the text live.
            _t_start = time.time()
            print("⏳ AI is thinking...", end="\r", flush=True)
            try:
                response_stream = llm_client.chat(
                    model=DEFAULT_MODEL,
                    messages=conversation_history,
                    tools=tools,
                    stream=True
                )
            except KeyboardInterrupt:
                print("\n[Interrupted]\n")
                conversation_history.pop()
                continue

            _t_first_token = time.time() - _t_start

            # Consume the stream, print it live, and reconstruct the final message dict
            message = stream_and_reconstruct(response_stream, audio_engine)

            # Handle tool calls in a ReAct loop
            loop_count = 0
            max_loops = 5

            while message.get('tool_calls') and loop_count < max_loops:
                loop_count += 1

                # Check if it's a direct Spotify/system command with no LLM needed
                final_response, direct_output, is_writing = process_tool_calls(
                    message,
                    conversation_history,
                    llm_client,
                    tools,
                    audio_engine
                )

                if direct_output:
                    print(f"🤖 AI: {direct_output}\n")
                    audio_engine.queue_text(direct_output)
                    audio_engine.signal_done()
                    break

                # If we need an LLM response after the tool
                full_response = stream_response(final_response, audio_engine, is_code=is_writing)
                conversation_history.append({
                    'role': 'assistant',
                    'content': full_response
                })

                # Check if the LLM wants to call another tool based on the result
                print("⏳ AI is continuing workflow...", end="\r", flush=True)
                next_response = llm_client.chat(
                    model=DEFAULT_MODEL,
                    messages=conversation_history,
                    tools=tools,
                    stream=False
                )
                message = next_response['message']

                if not message.get('tool_calls'):
                    audio_engine.signal_done()
                    break
                else:
                    print("\n  [Continuing workflow...]")

            if not message.get('tool_calls') and loop_count == 0:
                # Direct response, no tools used at all.
                # Text was already streamed and spoken live by stream_and_reconstruct above.
                conversation_history.append({
                    'role': 'assistant',
                    'content': message.get("content", "")
                })
                audio_engine.signal_done()
            
            _t_total = time.time() - _t_start
            print(f"✓ Done  ({_t_first_token:.1f}s to first response · {_t_total:.1f}s total)\n")
    
    finally:
        audio_engine.shutdown()
        asr_engine.stop_background_listener()

        # Kill the background messaging processes cleanly when the app closes
        if messaging_controller:
            from src.tools.messaging_tools import _messaging_processes
            for name, process in _messaging_processes.items():
                # Avoid attempting to terminate if it's just marked as "Already running"
                if process and process != "Already running" and hasattr(process, 'terminate'):
                    try:
                        print(f"Shutting down {name}...")
                        process.terminate()
                    except Exception as e:
                        pass


if __name__ == "__main__":
    main()
