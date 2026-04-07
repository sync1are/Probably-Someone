# Implementation Plan: Push-to-Talk (PTT) with Whisper

This document outlines the technical strategy for integrating a local, high-performance Push-to-Talk (PTT) system into the ARIA Voice Assistant using `faster-whisper` for Speech-to-Text (STT).

## 1. Objectives
*   **Hardware Agnostic:** Optimized for the standard `venv` environment (CPU/Auto detection).
*   **Low Latency:** Use `faster-whisper` (CTranslate2) for near-instant transcription.
*   **Global Hotkey:** Implement a keyboard listener that works even when the terminal isn't focused.
*   **Hands-free Flow:** Replace the manual `input()` loop with a voice-driven event loop.

## 2. New Dependencies
Add the following to `requirements.txt`:
*   `faster-whisper`: The fastest local Whisper implementation.
*   `pynput`: Global keyboard/mouse listener for hotkey detection.
*   `pyaudio`: For high-quality, real-time microphone stream capture.
*   `wave`: To handle temporary audio file generation.

## 3. Architecture & File Structure

We will introduce two new core modules to maintain a clean, refactored project:

```text
src/core/
├── stt_engine.py    # Whisper model loading & transcription logic
└── recorder.py      # Audio capture, buffering, and .wav export
```

### Module Responsibilities:

#### A. `src/core/stt_engine.py`
*   **Model Loading:** Initialize `WhisperModel("base.en")` or `"small.en"` on startup.
*   **Compute Settings:** Set `device="cpu"` and `compute_type="int8"` (optimized for standard venv/CPU).
*   **Transcription:** A `transcribe(file_path)` method that returns the text string and clears the temp file.

#### B. `src/core/recorder.py`
*   **Audio Stream:** Open a 16kHz, mono PyAudio stream (Whisper's native format).
*   **Buffer Management:** Use a `threading.Event` to start/stop the recording loop.
*   **File Export:** Save the raw bytes into a temporary `.wav` file for the STT engine.

## 4. Integration Strategy (`app.py`)

### The PTT Event Loop
We will refactor the `while True` loop in `app.py` to be event-driven:

1.  **Hotkey Listener:** Initialize `pynput.keyboard.Listener` in a background thread.
2.  **Hotkey Assignment:** Choose a key (e.g., `Right Ctrl` or `Alt`).
    *   **On Press:** Trigger `recorder.start()`.
    *   **On Release:** Trigger `recorder.stop()` -> `stt.transcribe()` -> `process_prompt()`.
3.  **Visual Indicators:**
    *   `[READY]` - Waiting for hotkey.
    *   `[RECORDING...]` - Capturing audio.
    *   `[PROCESSING...]` - Transcribing and generating AI response.

## 5. Implementation Roadmap

### Phase 1: Foundation
1.  Install new dependencies.
2.  Create `src/core/stt_engine.py` and verify model download/loading.

### Phase 2: Audio Capture
1.  Implement `src/core/recorder.py`.
2.  Test microphone levels and verify `.wav` file integrity.

### Phase 3: Hotkey Logic
1.  Implement the `pynput` listener in a standalone test script.
2.  Ensure key-release triggers the transcription process.

### Phase 4: Full Integration
1.  Refactor `app.py` to remove the blocking `input()`.
2.  Connect the Recorder -> STT Engine -> LLM Client pipeline.
3.  Add audio feedback (blips) for "Start/Stop Recording" using the existing `audio_engine`.

## 6. Success Criteria
*   Pressing the hotkey instantly starts recording.
*   Releasing the hotkey triggers the AI response within <2 seconds (transcription time).
*   No "echo" or feedback loops between the AI's voice and the microphone.
