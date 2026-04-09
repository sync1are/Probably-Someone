"""Audio and TTS management using remote TTS server."""

import re
import threading
import queue
import sounddevice as sd
import requests
import numpy as np
from src.config import TTS_VOICE, TTS_SPEED, TTS_SAMPLE_RATE, AUDIO_QUEUE_SIZE, TTS_BUFFER_THRESHOLD


class AudioEngine:
    """Manages TTS generation and audio playback."""

    def __init__(self, tts_server_url="http://127.0.0.1:8889/generate"):
        self.tts_server_url = tts_server_url
        self.audio_queue = queue.Queue(maxsize=AUDIO_QUEUE_SIZE)
        self.text_queue = queue.Queue()
        self.stop_signal = threading.Event()
        self.server_ready = False

        # Start worker threads
        threading.Thread(target=self._audio_player, daemon=True).start()
        threading.Thread(target=self._tts_renderer, daemon=True).start()

        # Check TTS server connection
        self._check_server_connection()

    def _check_server_connection(self):
        """Check if TTS server is accessible."""
        try:
            print(f"🔊 Connecting to TTS server at {self.tts_server_url}...")
            # Try a simple test request to the generate endpoint
            response = requests.post(
                self.tts_server_url,
                json={"text": "test", "voice": TTS_VOICE, "speed": TTS_SPEED},
                timeout=10
            )
            if response.status_code == 200:
                self.server_ready = True
                print("✓ Connected to TTS daemon")
            else:
                # Server is reachable but may have different API
                print(f"⚠️ TTS server responded with status {response.status_code}")
                print("   Assuming server is ready anyway...")
                self.server_ready = True  # Assume it's ready, will fail gracefully if not
        except requests.exceptions.ConnectionError:
            print(f"⚠️ Could not connect to TTS server at {self.tts_server_url}")
            print("   Make sure the TTS daemon is running")
            self.server_ready = False
        except Exception as e:
            print(f"⚠️ TTS server connection error: {e}")
            self.server_ready = False
    
    def _clean_text(self, text):
        """Clean text for TTS processing."""
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _audio_player(self):
        """Audio playback worker thread."""
        while not self.stop_signal.is_set():
            try:
                audio = self.audio_queue.get(timeout=0.1)
                if audio is None:
                    continue
                sd.play(audio, TTS_SAMPLE_RATE)
                sd.wait()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"\n⚠️ Audio playback error: {e}")
    
    def _tts_renderer(self):
        """TTS rendering worker thread."""
        while not self.stop_signal.is_set():
            try:
                text = self.text_queue.get(timeout=0.1)
                if text is None or text == "__DONE__":
                    continue

                # Wait for server to be ready
                if not self.server_ready:
                    continue

                # Send text to TTS server
                try:
                    response = requests.post(
                        self.tts_server_url,
                        json={
                            "text": text,
                            "voice": TTS_VOICE,
                            "speed": TTS_SPEED
                        },
                        timeout=10
                    )

                    if response.status_code == 200:
                        # Convert audio bytes to numpy array
                        audio_bytes = response.content
                        buffer_size = len(audio_bytes)

                        # Check if buffer size is valid
                        if buffer_size == 0:
                            continue

                        # Try different data types until one works
                        audio_data = None

                        # Try float32 (4 bytes per element)
                        if buffer_size % 4 == 0:
                            try:
                                audio_data = np.frombuffer(audio_bytes, dtype=np.float32)
                            except:
                                pass

                        # Try int16 (2 bytes per element)
                        if audio_data is None and buffer_size % 2 == 0:
                            try:
                                audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                            except:
                                pass

                        # Try uint8 (1 byte per element) as last resort
                        if audio_data is None:
                            try:
                                audio_data = np.frombuffer(audio_bytes, dtype=np.uint8).astype(np.float32) / 255.0
                            except:
                                print(f"\n⚠️ Could not parse audio buffer of size {buffer_size}")
                                continue

                        if audio_data is not None and len(audio_data) > 0:
                            self.audio_queue.put(audio_data)
                    else:
                        print(f"\n⚠️ TTS server error: {response.status_code}")

                except requests.exceptions.RequestException as e:
                    print(f"\n⚠️ TTS request failed: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"\n⚠️ TTS Error: {e}")
    
    def queue_text(self, text):
        """Queue text for TTS processing."""
        clean = self._clean_text(text)
        if clean and len(clean) > 2:
            self.text_queue.put(clean)
    
    def signal_done(self):
        """Signal that text streaming is complete."""
        self.text_queue.put("__DONE__")
    
    def wait_for_completion(self):
        """Wait for all audio to finish playing."""
        # Add a small buffer to ensure the queue isn't just momentarily empty between chunks
        empty_cycles = 0
        while empty_cycles < 5:
            if self.audio_queue.empty() and self.text_queue.empty():
                empty_cycles += 1
            else:
                empty_cycles = 0
            sd.sleep(50)
        sd.sleep(100)

    def interrupt(self):
        """Stop current playback and clear all pending audio/text."""
        # Stop currently playing audio immediately
        sd.stop()

        # Clear the text queue
        while not self.text_queue.empty():
            try:
                self.text_queue.get_nowait()
            except queue.Empty:
                break

        # Clear the audio queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def shutdown(self):
        """Shutdown audio threads."""
        self.stop_signal.set()
        self.interrupt()


class StreamingTextProcessor:
    """Processes streaming text and sends to TTS in chunks."""
    
    def __init__(self, audio_engine):
        self.audio_engine = audio_engine
        self.text_buffer = ""
        self.char_count = 0
    
    def process_chunk(self, chunk):
        """Process a text chunk from streaming response."""
        self.text_buffer += chunk
        self.char_count += len(chunk)

        # Split on sentence boundaries (.!?: or newlines)
        # Avoid splitting on commas alone as it makes speech too choppy
        # Avoid splitting on numbered list dots (e.g. "1.", "2.") by checking lookbehind
        split_pattern = r'(?<!\b\d)([.!?:\n]+[\s]+)'

        sentences = re.split(split_pattern, self.text_buffer)

        # We process ONLY if we have a full sentence (length > 2 because re.split keeps the delimiter)
        # We REMOVED the char_count threshold to prevent random mid-sentence cutoffs
        while len(sentences) > 2:
            # Recombine the first sentence with its trailing punctuation
            complete_text = sentences[0] + sentences[1]

            # Keep the rest in the buffer
            self.text_buffer = ''.join(sentences[2:])
            self.char_count = len(self.text_buffer)

            # Clean up formatting artifacts that confuse Kokoro before queueing
            cleaned_text = complete_text.strip()
            # Remove Markdown bold/italic asterisks, list dashes, and backticks
            cleaned_text = re.sub(r'[*_`~]', '', cleaned_text)
            # Remove hash symbols from headers
            cleaned_text = re.sub(r'#+\s*', '', cleaned_text)

            if cleaned_text:
                self.audio_engine.queue_text(cleaned_text)

            # Re-split the remaining buffer to see if there are more complete sentences waiting
            sentences = re.split(split_pattern, self.text_buffer)
    
    def flush(self):
        """Flush remaining buffered text."""
        cleaned_text = self.text_buffer.strip()
        cleaned_text = re.sub(r'[*_`~]', '', cleaned_text)
        cleaned_text = re.sub(r'#+\s*', '', cleaned_text)

        if cleaned_text:
            self.audio_engine.queue_text(cleaned_text)
        self.text_buffer = ""
        self.char_count = 0
