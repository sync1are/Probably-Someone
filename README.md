# ARIA Voice Assistant

A voice-enabled AI assistant with Spotify integration and screenshot analysis capabilities.

## Features

- 🎙️ **Voice Output** - Natural TTS using Kokoro
- 🎵 **Spotify Control** - Play, pause, skip, queue songs via voice
- 📸 **Screenshot Analysis** - AI can see and analyze your screen
- 🤖 **LLM Integration** - Powered by Ollama API

## Project Structure

```
D:\VERISON 3\
├── src\
│   ├── core\
│   │   ├── llm_client.py      # Ollama client wrapper
│   │   └── audio_engine.py    # TTS and audio playback
│   ├── tools\
│   │   ├── registry.py        # Tool execution dispatcher
│   │   ├── system_tools.py    # Screenshot and system utilities
│   │   └── spotify_tools.py   # Spotify playback controls
│   └── config.py              # Configuration and environment variables
├── app.py                     # Main entry point
├── tools.json                 # Tool schemas for LLM
├── requirements.txt           # Python dependencies
└── .env                       # API keys and credentials
```

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables** (`.env`)
   ```env
   OLLAMA_API_KEY=your_ollama_key
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   ```

3. **Spotify Setup**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create an app and get Client ID/Secret
   - Add `http://127.0.0.1:8888/callback` as a Redirect URI
   - **Note:** Requires Spotify Premium for playback controls

## Usage

```bash
python app.py
```

### Example Commands

- **Music Control:**
  - "Play some jazz"
  - "Pause the music"
  - "Skip to next song"
  - "What's playing?"
  - "Add Bohemian Rhapsody to queue"

- **Screenshot:**
  - "What's on my screen?"
  - "Take a screenshot and analyze it"

- **General:**
  - "Hello"
  - "What's the weather like?"
  - Any general questions

## Architecture

- **Modular Design** - Clean separation of concerns
- **Tool Registry Pattern** - Easy to add new capabilities
- **Streaming TTS** - Low-latency audio output
- **Multi-threaded Audio** - Non-blocking playback

## Requirements

- Python 3.8+
- Spotify Premium account
- Ollama API access
- PyTorch with CUDA (optional, for faster TTS)
