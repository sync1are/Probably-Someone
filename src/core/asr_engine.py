"""
ARIA Voice Assistant - Background Hotkey ASR Engine
Listens for a hotkey in the background, records via subprocess, and injects text.
"""
import subprocess
import keyboard
import threading
import time
import sys
import logging
import os
from src.config import NVIDIA_API_KEY, NVIDIA_FUNCTION_ID

# Set up logging
logging.basicConfig(
    filename='asr_engine.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ASREngine:
    def __init__(self, server="grpc.nvcf.nvidia.com:443", hotkey='ctrl+shift'):
        self.server = server
        self.hotkey = hotkey
        self.is_running = False
        self.listener_thread = None

        if not NVIDIA_API_KEY or not NVIDIA_FUNCTION_ID:
            print("⚠️ Warning: NVIDIA_API_KEY or NVIDIA_FUNCTION_ID missing in config. Voice mode disabled.")
            self.ready = False
        else:
            self.ready = True

    def start_background_listener(self):
        """Starts the background thread that watches for the hotkey."""
        if not self.ready:
            return

        self.is_running = True
        self.listener_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.listener_thread.start()

    def stop_background_listener(self):
        self.is_running = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1.0)

    def _hotkey_loop(self):
        """Continuously checks for the hotkey and handles recording."""
        while self.is_running:
            try:
                # Wait for the user to press the hotkey
                if keyboard.is_pressed(self.hotkey):
                    self._record_and_inject()
                    # Wait for them to fully release before allowing another trigger
                    while keyboard.is_pressed(self.hotkey):
                        time.sleep(0.1)
                time.sleep(0.05)
            except Exception as e:
                time.sleep(1)

    def _record_and_inject(self):
        """Records audio while hotkey is held, prints live transcript, then injects into terminal."""
        sys.stdout.write("\r\033[K🎙️ Listening: ...")
        sys.stdout.flush()

        command = [
            r"D:\parakeet\venv\Scripts\python.exe", "-u",
            r"D:\VERISON 3\python-clients\scripts\asr\transcribe_mic.py",
            "--server", self.server,
            "--use-ssl",
            "--metadata", "function-id", NVIDIA_FUNCTION_ID,
            "--metadata", "authorization", f"Bearer {NVIDIA_API_KEY}",
            "--language-code", "en-US",
            "--automatic-punctuation"
        ]

        process = None
        final_transcript = [""]
        committed_text = []
        interim_text = [""]

        def read_output():
            logging.debug("Started stdout reader thread")
            buffer = b""

            def process_buffer(b):
                try:
                    clean = b.decode('utf-8', errors='ignore').strip()
                except:
                    return

                if clean and not clean.startswith("INFO:") and not clean.startswith("WARNING:") and not clean.startswith("ERROR:") and "grpc_tools" not in clean:
                    if clean.startswith(">>"):
                        interim_text[0] = clean[2:].strip()
                    else:
                        if clean.startswith("##"):
                            clean = clean.lstrip("#").strip()
                        if clean:
                            committed_text.append(clean)
                            interim_text[0] = ""

                    full_text = " ".join(committed_text + ([interim_text[0]] if interim_text[0] else []))
                    if full_text:
                        final_transcript[0] = full_text.strip()
                        logging.debug(f"Transcript updated: {final_transcript[0]}")
                        # We use \r to return to the start of the line, and \033[K to clear it
                        # but we should ensure we are flushing correctly so it doesn't duplicate
                        sys.stdout.write(f"\r\033[K🎙️ Listening: {final_transcript[0]}")
                        sys.stdout.flush()

            while process.poll() is None:
                try:
                    char = process.stdout.read(1)
                    if not char:
                        break

                    if char in (b'\r', b'\n'):
                        if buffer:
                            logging.debug(f"Buffer flushed: {buffer}")
                            process_buffer(buffer)
                        buffer = b""
                    else:
                        buffer += char
                except Exception as e:
                    logging.error(f"Read error: {e}")
                    break

            if buffer:
                logging.debug(f"Final buffer flush on exit: {buffer}")
                process_buffer(buffer)
            logging.debug("Exiting reader thread")

        try:
            # Start recording subprocess
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0, # Unbuffered bytes
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # Start the reader thread
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()

            # Wait while key is held
            while keyboard.is_pressed(self.hotkey):
                time.sleep(0.05)

            # Key released, kill process
            process.terminate()
            reader_thread.join(timeout=1.0)

            try:
                process.kill()
            except:
                pass

        except Exception as e:
            print(f"\n⚠️ ASR Error: {e}")
            if process:
                try: process.kill()
                except: pass

        # Clean up the console line
        sys.stdout.write("\r\033[KYou: ")
        sys.stdout.flush()

        if final_transcript[0]:
            # Inject the transcript into the console input buffer and press Enter
            keyboard.write(final_transcript[0])
            keyboard.send("enter")
