"""
ARIA Voice Assistant - Main Entry Point
Refactored modular architecture with Spotify integration
"""

import json
from src.config import SYSTEM_PROMPT, DEFAULT_MODEL, TOOLS_FILE
from src.core.llm_client import LLMClient
from src.core.audio_engine import AudioEngine, StreamingTextProcessor
from src.tools.registry import execute_tool


def load_tools():
    """Load tool definitions from tools.json."""
    with open(TOOLS_FILE, 'r') as f:
        tools_data = json.load(f)
        return tools_data['tools']


def stream_response(response, audio_engine):
    """Stream LLM response and handle TTS."""
    full_response = ""
    processor = StreamingTextProcessor(audio_engine)
    
    print("🤖 AI:", end=" ", flush=True)
    
    for part in response:
        chunk = part['message']['content']
        print(chunk, end='', flush=True)
        
        full_response += chunk
        processor.process_chunk(chunk)
    
    print("\n")
    processor.flush()
    
    return full_response


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
        return None, '\n'.join(direct_responses)
    
    # Otherwise, get final response from LLM for natural language
    # Check if this is a vision request (has images in conversation)
    has_images = any('images' in msg for msg in conversation_history if isinstance(msg, dict))

    final_response = llm_client.chat(
        model=DEFAULT_MODEL,
        messages=conversation_history,
        stream=True,
        think=has_images  # Enable thinking for vision analysis
    )
    
    return final_response, None


def main():
    """Main application loop."""
    # Initialize components
    llm_client = LLMClient()
    audio_engine = AudioEngine()
    tools = load_tools()
    
    # Initialize conversation
    conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    print("🤖 ARIA Voice Assistant Started!")
    print("📸 Screenshot tool enabled")
    print("🎵 Spotify controls enabled - try 'play some jazz' or 'pause music'")
    print("Type 'quit' or 'exit' to stop\n")
    
    try:
        while True:
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
            
            # Get initial response (check for tool calls)
            response = llm_client.chat(
                model=DEFAULT_MODEL,
                messages=conversation_history,
                tools=tools,
                stream=False
            )
            
            message = response['message']
            
            # Handle tool calls or direct response
            if message.get('tool_calls'):
                final_response, direct_output = process_tool_calls(
                    message, 
                    conversation_history, 
                    llm_client, 
                    tools,
                    audio_engine
                )
                
                if direct_output:
                    # Direct Spotify response - no LLM needed
                    print(f"🤖 AI: {direct_output}\n")
                    audio_engine.queue_text(direct_output)
                    audio_engine.signal_done()
                else:
                    # Stream LLM response
                    full_response = stream_response(final_response, audio_engine)
                    conversation_history.append({
                        'role': 'assistant',
                        'content': full_response
                    })
                    audio_engine.signal_done()
            else:
                # Direct response, no tools
                streamed = llm_client.chat(
                    model=DEFAULT_MODEL,
                    messages=conversation_history,
                    stream=True
                )
                full_response = stream_response(streamed, audio_engine)
                conversation_history.append({
                    'role': 'assistant',
                    'content': full_response
                })
                audio_engine.signal_done()
            
            print("✓ Done\n")
    
    finally:
        audio_engine.shutdown()


if __name__ == "__main__":
    main()
