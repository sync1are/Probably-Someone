# ARIA Voice Assistant

A voice-enabled AI assistant with Spotify integration, screenshot analysis, messaging automation, and powerful context-aware tools.

## Features

- 🎙️ **Voice Output** - Natural TTS using Kokoro
- 🎵 **Spotify Control** - Play, pause, skip, queue songs via voice
- 💬 **Messaging Automation** - Auto-reply on WhatsApp & Discord
- 📸 **Screenshot Analysis** - AI can see and analyze your screen
- 📋 **Clipboard Management** - "Summarize what I copied", copy AI responses
- 🪟 **Window Context** - AI knows what app you're using
- 🌐 **Web Scraping** - "Summarize this article [URL]"
- 🤖 **LLM Integration** - Powered by Ollama API

## Quick Start

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the assistant
python app.py

# Start messaging system
cd messaging
python start_messaging.py
```

## New Features 🚀

### Messaging Automation
- **"Setup WhatsApp"** - Connect WhatsApp with QR code authentication
- **"Setup Discord"** - Configure Discord bot with user token
- **"Start messaging"** - Activate auto-reply for both platforms
- **"Add [name] to whitelist"** - Allow auto-reply for specific contacts
- **"Send [contact] a message"** - Proactive messaging via voice
- **Single-response mode** - Quick replies without conversation loops

### Clipboard Management
- **"What did I copy?"** - Get clipboard content
- **"Summarize what's in my clipboard"** - Analyze copied text
- **"Copy this to clipboard"** - Save AI response
- **"Fix the grammar in my clipboard"** - Edit and analyze

### Active Window Detection
- **"What app am I using?"** - Get current window/app
- **"Help me with this program"** - Context-aware assistance
- AI automatically knows your context (VS Code, Chrome, Excel, etc.)

### Web Scraping
- **"Summarize https://example.com"** - Extract and analyze web content
- **"What does this article say?"** - Read any webpage
- **"Compare these two articles"** - Multi-source research

## Project Structure

```
D:\VERISON 3\
├── app.py                     # Main ARIA entry point
├── tools.json                 # Tool definitions for LLM
├── requirements.txt           # Python dependencies
├── .env                       # API keys and configuration
│
├── src/                       # Source code
│   ├── core/                  # Core modules
│   │   ├── llm_client.py      # Ollama client wrapper
│   │   └── audio_engine.py    # TTS and audio playback
│   ├── tools/                 # Tool implementations
│   │   ├── registry.py        # Tool execution dispatcher
│   │   ├── system_tools.py    # Screenshot, clipboard, etc.
│   │   ├── spotify_tools.py   # Spotify integration
│   │   ├── web_tools.py       # Web scraping
│   │   └── messaging_tools.py # Messaging setup/control
│   ├── messaging/             # Messaging backend
│   │   ├── controller.py      # Main orchestrator
│   │   ├── whitelist.py       # Contact management
│   │   ├── response_generator.py # AI reply logic
│   │   └── http_server.py     # Flask API server
│   └── config.py              # Configuration
│
├── messaging/                 # Messaging applications
│   ├── discord_bot.py         # Discord bot
│   ├── start_messaging.py     # Messaging launcher
│   ├── messaging_whitelist.json # Contact whitelist
│   └── whatsapp_bridge/       # WhatsApp Node.js bridge
│       ├── bridge.js          # WhatsApp client
│       └── package.json       # Node dependencies
│
├── tests/                     # Testing suite
│   ├── test_suite.py          # Comprehensive tests
│   ├── test_nvidia.py         # NVIDIA API benchmark
│   └── test_report_*.json     # Test results
│
└── docs/                      # Documentation
    ├── README.md              # This file
    ├── DIRECTORY_STRUCTURE.md # Project layout guide
    ├── FEATURES_ROADMAP.md    # Future features
    └── MESSAGING_*.md         # Messaging docs
```

## Setup

### 1. Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables (`.env`)
```env
# LLM API
OLLAMA_API_KEY=your_ollama_key

# Spotify (requires Premium)
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback

# Discord (optional - for messaging)
DISCORD_USER_TOKEN=your_discord_user_token
```

### 3. Spotify Setup
- Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Create an app and get Client ID/Secret
- Add `http://127.0.0.1:8888/callback` as a Redirect URI
- **Note:** Requires Spotify Premium for playback controls

### 4. WhatsApp Setup (Optional)
```bash
# Install Node.js dependencies for WhatsApp bridge
cd messaging/whatsapp_bridge
npm install
```

### 5. Discord Setup (Optional)
- See `docs/MESSAGING_GUIDE.md` for detailed Discord token setup

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
