"""Audio and TTS management using Kokoro pipeline."""

import re
import threading
import queue
import sounddevice as sd
from kokoro import KPipeline
from src.config import TTS_VOICE, TTS_SPEED, TTS_SAMPLE_RATE, AUDIO_QUEUE_SIZE, TTS_BUFFER_THRESHOLD


class AudioEngine:
    """Manages TTS generation and audio playback."""
    
    def __init__(self):
        self.pipeline = None  # Lazy load on first use
        self.audio_queue = queue.Queue(maxsize=AUDIO_QUEUE_SIZE)
        self.text_queue = queue.Queue()
        self.stop_signal = threading.Event()
        self.pipeline_ready = False
        
        # Start worker threads
        threading.Thread(target=self._audio_player, daemon=True).start()
        threading.Thread(target=self._tts_renderer, daemon=True).start()
        
        # Initialize TTS in background
        threading.Thread(target=self._lazy_init_pipeline, daemon=True).start()
    
    def _lazy_init_pipeline(self):
        """Initialize TTS pipeline in background thread."""
        try:
            print("🔊 Loading TTS engine in background...")
            self.pipeline = KPipeline(lang_code='a')
            # Pre-warm
            for _ in self.pipeline("Ready", voice=TTS_VOICE, speed=TTS_SPEED):
                pass
            self.pipeline_ready = True
            print("✓ TTS engine ready")
        except Exception as e:
            print(f"⚠️ TTS initialization warning: {e}")
            self.pipeline_ready = False
    
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
    
    def _tts_renderer(self):
        """TTS rendering worker thread."""
        while not self.stop_signal.is_set():
            try:
                text = self.text_queue.get(timeout=0.1)
                if text is None or text == "__DONE__":
                    continue
                
                # Wait for pipeline to be ready
                if not self.pipeline_ready or self.pipeline is None:
                    continue
                
                generator = self.pipeline(
                    text,
                    voice=TTS_VOICE,
                    speed=TTS_SPEED,
                    split_pattern=r'\n+'
                )
                
                for _, _, audio in generator:
                    self.audio_queue.put(audio)
            
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
        while not self.audio_queue.empty() or not self.text_queue.empty():
            sd.sleep(50)
        sd.sleep(200)
    
    def shutdown(self):
        """Shutdown audio threads."""
        self.stop_signal.set()


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
        
        sentences = re.split(r'([.!?:,]\s+)', self.text_buffer)
        
        if len(sentences) > 2 or self.char_count > TTS_BUFFER_THRESHOLD:
            complete_text = ''.join(sentences[:-1]) if len(sentences) > 2 else self.text_buffer
            self.text_buffer = sentences[-1] if len(sentences) > 2 else ""
            self.char_count = len(self.text_buffer)
            
            if complete_text.strip():
                self.audio_engine.queue_text(complete_text)
    
    def flush(self):
        """Flush remaining buffered text."""
        if self.text_buffer.strip():
            self.audio_engine.queue_text(self.text_buffer)
        self.text_buffer = ""
        self.char_count = 0
