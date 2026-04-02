
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

# ====== CONFIG ======
api_key = os.getenv('OLLAMA_API_KEY')
if not api_key:
    raise ValueError("Missing OLLAMA_API_KEY in .env")

client = Client(
    host="http://localhost:11434",  # FIXED
    headers={'Authorization': 'Bearer ' + api_key}
)

# ====== LOAD TOOLS ======
with open('tools.json', 'r') as f:
    tools_data = json.load(f)
    available_tools = tools_data['tools']

# ====== TTS INIT ======
pipeline = KPipeline(lang_code='a')

# Pre-warm TTS
try:
    for _ in pipeline("Ready", voice='af_heart', speed=1.2):
        pass
except:
    pass

print("🤖 Voice AI Assistant Started!")
print("📸 Screenshot tool enabled - try 'what's on my screen?'")
print("Type 'quit' or 'exit' to stop\n")

# ====== SYSTEM PROMPT ======
system_prompt = """You are ARIA (Adaptive Reasoning Intelligence Assistant), a local AI assistant.

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

conversation_history = [{"role": "system", "content": system_prompt}]

# ====== AUDIO SYSTEM ======
audio_queue = queue.Queue(maxsize=50)
text_queue = queue.Queue()
stop_signal = threading.Event()

def clean_text(text):
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def audio_player():
    while not stop_signal.is_set():
        try:
            audio = audio_queue.get(timeout=0.1)
            if audio is None:
                continue
            sd.play(audio, 24000)
            sd.wait()
        except queue.Empty:
            continue

def tts_renderer():
    while not stop_signal.is_set():
        try:
            text = text_queue.get(timeout=0.1)
            if text is None or text == "__DONE__":
                continue

            generator = pipeline(
                text,
                voice='af_heart',
                speed=1.2,
                split_pattern=r'\n+'
            )

            for _, _, audio in generator:
                audio_queue.put(audio)

        except queue.Empty:
            continue
        except Exception as e:
            print(f"\n⚠️ TTS Error: {e}")

# Start threads
threading.Thread(target=audio_player, daemon=True).start()
threading.Thread(target=tts_renderer, daemon=True).start()

# ====== STREAM RESPONSE ======
def stream_response(response):
    full_response = ""
    text_buffer = ""
    char_count = 0

    print("🤖 AI:", end=" ", flush=True)

    for part in response:
        chunk = part['message']['content']
        print(chunk, end='', flush=True)

        full_response += chunk
        text_buffer += chunk
        char_count += len(chunk)

        sentences = re.split(r'([.!?:,]\s+)', text_buffer)

        if len(sentences) > 2 or char_count > 50:
            complete_text = ''.join(sentences[:-1]) if len(sentences) > 2 else text_buffer
            text_buffer = sentences[-1] if len(sentences) > 2 else ""
            char_count = len(text_buffer)

            text_clean = clean_text(complete_text)
            if text_clean and len(text_clean) > 2:
                text_queue.put(text_clean)

    print("\n")

    # Flush remaining buffer
    if text_buffer.strip():
        text_clean = clean_text(text_buffer)
        if text_clean and len(text_clean) > 2:
            text_queue.put(text_clean)

    return full_response

def wait_for_audio():
    while not audio_queue.empty() or not text_queue.empty():
        sd.sleep(50)
    sd.sleep(200)

# ====== MAIN LOOP ======
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

    response = client.chat(
        model='kimi-k2.5:cloud',  # FIXED safer model
        messages=conversation_history,
        tools=available_tools,
        stream=False
    )

    message = response['message']

    # ===== TOOL HANDLING =====
    if message.get('tool_calls'):
        print("🔧 Using tools...")

        vision_used = False

        for tool_call in message['tool_calls']:
            tool_name = tool_call['function']['name']
            tool_args = tool_call['function']['arguments']

            print(f"  → Calling {tool_name}...")
            tool_result = execute_tool(tool_name, tool_args)

            if tool_result.get('success'):
                print(f"  ✓ {tool_name} completed")

                if tool_name == "take_screenshot" and 'image_base64' in tool_result:
                    vision_used = True

                    conversation_history.append(message)
                    conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps({
                            'success': True,
                            'message': f"Screenshot captured: {tool_result['width']}x{tool_result['height']}"
                        })
                    })
                    conversation_history.append({
                        'role': 'user',
                        'content': 'Analyze this screenshot.',
                        'images': [tool_result['image_base64']]
                    })
                else:
                    conversation_history.append(message)
                    conversation_history.append({
                        'role': 'tool',
                        'content': json.dumps(tool_result)
                    })

        final_model = 'kimi-k2.5:cloud'

        final_response = client.chat(
            model=final_model,
            messages=conversation_history,
            stream=True
        )

        full_response = stream_response(final_response)

        conversation_history.append({
            'role': 'assistant',
            'content': full_response
        })

        text_queue.put("__DONE__")
        print("✓ Done\n")

    else:
        streamed = client.chat(
            model='kimi-k2.5:cloud',
            messages=conversation_history,
            stream=True
        )

        full_response = stream_response(streamed)

        conversation_history.append({
            'role': 'assistant',
            'content': full_response
        })

        text_queue.put("__DONE__")
        print("✓ Done\n")

