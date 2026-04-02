from ollama import Client
from kokoro import KPipeline
import sounddevice as sd
import os
from dotenv import load_dotenv
import re
import threading
import queue
import numpy as np
import json
from tool_handlers import execute_tool


load_dotenv()

# Init client
client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.getenv('OLLAMA_API_KEY')}
)

# Load tools from tools.json
with open('tools.json', 'r') as f:
    tools_data = json.load(f)
    available_tools = tools_data['tools']

pipeline = KPipeline(lang_code='a')

print("🤖 Voice AI Assistant Started!")
print("📸 Screenshot tool enabled - try 'what's on my screen?'")
print("Type 'quit' or 'exit' to stop\n")

conversation_history = []

while True:
    user_input = input("You: ").strip()

    if user_input.lower() in ['quit', 'exit', 'bye', 'q']:
        print("👋 Goodbye!")
        break

    if not user_input:
        continue

    conversation_history.append({
        'role': 'user',
        'content': user_input
    })

    # Call LLM with tools
    response = client.chat(
        model='qwen3-vl:235b-instruct-cloud',
        messages=conversation_history,
        tools=available_tools,
        stream=False
    )

    message = response['message']
    
    # Check if LLM wants to use a tool
    if message.get('tool_calls'):
        print("🔧 Using tools...")
        
        # Process all tool calls
        for tool_call in message['tool_calls']:
            tool_name = tool_call['function']['name']
            tool_args = tool_call['function']['arguments']
            
            print(f"  → Calling {tool_name}...")
            
            # Execute the tool
            tool_result = execute_tool(tool_name, tool_args)
            
            if tool_result.get('success'):
                print(f"  ✓ {tool_name} completed")
                
                # For screenshot, prepare the image for the LLM
                if tool_name == "take_screenshot" and 'image_base64' in tool_result:
                    # Add tool response to conversation
                    conversation_history.append(message)
                    conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps({
                            'success': True,
                            'message': f"Screenshot captured: {tool_result['width']}x{tool_result['height']}"
                        })
                    })
                    
                    # Now ask LLM to analyze the screenshot with vision
                    conversation_history.append({
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': 'Here is the screenshot. Please analyze it and answer my question.'
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f"data:image/png;base64,{tool_result['image_base64']}"
                                }
                            }
                        ]
                    })
                else:
                    # Regular tool response
                    conversation_history.append(message)
                    conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result)
                    })
            else:
                print(f"  ✗ {tool_name} failed: {tool_result.get('error')}")
                conversation_history.append(message)
                conversation_history.append({
                    'role': 'tool',
                    'content': json.dumps(tool_result)
                })
        
        # Get final response from LLM after tool execution
        response = client.chat(
            model='gpt-oss:120b-cloud',
            messages=conversation_history,
            stream=True
        )
        
        # Stream the response with TTS
        full_response = ""
        text_buffer = ""
        
        text_queue = queue.Queue()
        audio_queue = queue.Queue()
        playback_done = threading.Event()
        
        print("🤖 AI:", end=" ", flush=True)
        
        def audio_player():
            """Plays audio chunks as they become available"""
            while True:
                audio = audio_queue.get()
                if audio is None:
                    break
                sd.play(audio, 24000)
                sd.wait()
            playback_done.set()
        
        def tts_renderer():
            """Renders text chunks to audio as they arrive"""
            while True:
                text = text_queue.get()
                if text is None:
                    break
                
                try:
                    generator = pipeline(
                        text,
                        voice='af_heart',
                        speed=1,
                        split_pattern=r'\n+'
                    )
                    for _, _, audio in generator:
                        audio_queue.put(audio)
                except Exception as e:
                    print(f"\n⚠️ TTS Error: {e}")
            
            audio_queue.put(None)
        
        player_thread = threading.Thread(target=audio_player, daemon=True)
        renderer_thread = threading.Thread(target=tts_renderer, daemon=True)
        player_thread.start()
        renderer_thread.start()
        
        for part in response:
            chunk = part['message']['content']
            print(chunk, end='', flush=True)
            full_response += chunk
            text_buffer += chunk
            
            sentences = re.split(r'([.!?]\s+)', text_buffer)
            
            if len(sentences) > 2:
                complete_text = ''.join(sentences[:-1])
                text_buffer = sentences[-1]
                
                text_clean = re.sub(r'[^\x00-\x7F]+', '', complete_text)
                text_clean = re.sub(r'\s+', ' ', text_clean).strip()
                text_clean = re.sub(r'\s*['']\s*', "'", text_clean)
                
                if text_clean and len(text_clean) > 3:
                    text_queue.put(text_clean)
        
        print("\n")
        
        if text_buffer.strip():
            text_clean = re.sub(r'[^\x00-\x7F]+', '', text_buffer)
            text_clean = re.sub(r'\s+', ' ', text_clean).strip()
            text_clean = re.sub(r'\s*['']\s*', "'", text_clean)
            if text_clean and len(text_clean) > 3:
                text_queue.put(text_clean)
        
        conversation_history.append({
            'role': 'assistant',
            'content': full_response
        })
        
        text_queue.put(None)
        playback_done.wait()
        
        print("✓ Done\n")
        
    else:
        # No tool calls - regular response with streaming TTS
        full_response = ""
        text_buffer = ""
        
        text_queue = queue.Queue()
        audio_queue = queue.Queue()
        playback_done = threading.Event()
        
        print("🤖 AI:", end=" ", flush=True)
        
        def audio_player():
            """Plays audio chunks as they become available"""
            while True:
                audio = audio_queue.get()
                if audio is None:
                    break
                sd.play(audio, 24000)
                sd.wait()
            playback_done.set()
        
        def tts_renderer():
            """Renders text chunks to audio as they arrive"""
            while True:
                text = text_queue.get()
                if text is None:
                    break
                
                try:
                    generator = pipeline(
                        text,
                        voice='af_heart',
                        speed=1,
                        split_pattern=r'\n+'
                    )
                    for _, _, audio in generator:
                        audio_queue.put(audio)
                except Exception as e:
                    print(f"\n⚠️ TTS Error: {e}")
            
            audio_queue.put(None)
        
        player_thread = threading.Thread(target=audio_player, daemon=True)
        renderer_thread = threading.Thread(target=tts_renderer, daemon=True)
        player_thread.start()
        renderer_thread.start()
        
        # Stream AI response
        for part in client.chat(
            model='gpt-oss:120b-cloud',
            messages=conversation_history,
            stream=True
        ):
            chunk = part['message']['content']
            print(chunk, end='', flush=True)
            full_response += chunk
            text_buffer += chunk
            
            sentences = re.split(r'([.!?]\s+)', text_buffer)
            
            if len(sentences) > 2:
                complete_text = ''.join(sentences[:-1])
                text_buffer = sentences[-1]
                
                text_clean = re.sub(r'[^\x00-\x7F]+', '', complete_text)
                text_clean = re.sub(r'\s+', ' ', text_clean).strip()
                text_clean = re.sub(r'\s*['']\s*', "'", text_clean)
                
                if text_clean and len(text_clean) > 3:
                    text_queue.put(text_clean)

        print("\n")
        
        if text_buffer.strip():
            text_clean = re.sub(r'[^\x00-\x7F]+', '', text_buffer)
            text_clean = re.sub(r'\s+', ' ', text_clean).strip()
            text_clean = re.sub(r'\s*['']\s*', "'", text_clean)
            if text_clean and len(text_clean) > 3:
                text_queue.put(text_clean)
        
        conversation_history.append({
            'role': 'assistant',
            'content': full_response
        })
        
        text_queue.put(None)
        playback_done.wait()
        
        print("✓ Done\n")
