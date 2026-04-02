from ollama import Client
from kokoro import KPipeline
import sounddevice as sd
import os
from dotenv import load_dotenv
import re
import threading
import queue
import numpy as np


load_dotenv()
# Init client
client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.getenv('OLLAMA_API_KEY')}
)

pipeline = KPipeline(lang_code='a')

print("🤖 Voice AI Assistant Started!")
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

    # 🔥 STREAM RESPONSE + COLLECT TEXT + PARALLEL TTS
    full_response = ""
    text_buffer = ""
    
    # Queue for text chunks ready for TTS
    text_queue = queue.Queue()
    audio_queue = queue.Queue()
    streaming_done = threading.Event()
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
        
        audio_queue.put(None)  # Signal audio player to stop
    
    # Start threads
    player_thread = threading.Thread(target=audio_player, daemon=True)
    renderer_thread = threading.Thread(target=tts_renderer, daemon=True)
    player_thread.start()
    renderer_thread.start()
    
    # Stream AI response and queue text for TTS
    for part in client.chat(
        model='gpt-oss:120b-cloud',
        messages=conversation_history,
        stream=True
    ):
        chunk = part['message']['content']
        print(chunk, end='', flush=True)
        full_response += chunk
        text_buffer += chunk
        
        # Check for sentence boundaries
        sentences = re.split(r'([.!?]\s+)', text_buffer)
        
        # If we have complete sentences, send them for TTS
        if len(sentences) > 2:
            complete_text = ''.join(sentences[:-1])
            text_buffer = sentences[-1]
            
            # Clean and queue for TTS
            # Remove emojis but preserve apostrophes and basic punctuation
            text_clean = re.sub(r'[^\x00-\x7F]+', '', complete_text)
            # Normalize whitespace
            text_clean = re.sub(r'\s+', ' ', text_clean).strip()
            # Ensure contractions are preserved (there's, I'm, etc.)
            text_clean = re.sub(r'\s*['']\s*', "'", text_clean)  # Normalize fancy apostrophes
            
            if text_clean and len(text_clean) > 3:
                text_queue.put(text_clean)

    print("\n")
    
    # Process any remaining text
    if text_buffer.strip():
        # Remove emojis but preserve apostrophes and basic punctuation
        text_clean = re.sub(r'[^\x00-\x7F]+', '', text_buffer)
        # Normalize whitespace
        text_clean = re.sub(r'\s+', ' ', text_clean).strip()
        # Ensure contractions are preserved (there's, I'm, etc.)
        text_clean = re.sub(r'\s*['']\s*', "'", text_clean)  # Normalize fancy apostrophes
        if text_clean and len(text_clean) > 3:
            text_queue.put(text_clean)
    
    # Save assistant response
    conversation_history.append({
        'role': 'assistant',
        'content': full_response
    })
    
    # Signal TTS renderer to stop and wait for completion
    text_queue.put(None)
    playback_done.wait()
    
    print("✓ Done\n")