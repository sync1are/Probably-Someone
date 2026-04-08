# ARIA Voice Assistant

A voice-enabled AI assistant with Spotify integration, screenshot analysis, messaging automation, and powerful context-aware tools.

## Features

- 🎙️ **Voice Output** - Natural TTS using Kokoro
- 🎵 **Spotify Control** - Play, pause, skip, queue songs via voice
- 💬 **Messaging Automation** - Auto-reply on WhatsApp & Discord
- 📧 **Gmail Integration** - AI can read your important unread emails
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

### Gmail Integration
- **"Do I have any important emails?"** - Read summary of new important emails
- **"Read me the email from John"** - Read full email content
- Secure local authentication (OAuth 2.0)
- Read-only access by default

### Clipboard Management
- **"What did I copy?"** - Get clipboard content
- **"Summarize what's in my clipboard"** - Analyze copied text
- **"Copy this to clipboard"** - Save AI response
- **"Fix the grammar in my clipboard"** - Edit and analyze

### Active Window Detection
- **"What app am I using?"** - Get current window/app
- **"Help me with this program"** - Context-aware assistance
- AI automatically knows your context (VS Code, Chrome, Excel, etc.)

### Window & App Control
- **"Open File Explorer"** - Launch local applications by name
- **"Go to YouTube"** - Open specific websites
- **"Minimize Chrome" / "Maximize VS Code"** - Control window state
- **"Switch to Discord"** - Bring specific apps to the foreground
- **"Show my desktop"** - Minimize everything

### System & Audio Control
- **"Set volume to 50%" / "Mute"** - Control master volume
- **"Set brightness to 20%"** - Control monitor brightness
- **"Pause the video"** - Smart routing pauses system media if Spotify isn't playing

### File Management & Multi-Step Workflows
- **"Create a file called notes.txt"** - AI can save text files
- **"Save this as data.json"** - Properly formats and saves JSON
- **"Create an HTML file and open it"** - AI can chain tools to write a file and instantly launch it
- **"Append this to grocery.txt"** - Add to existing files
- **"What did I write in my notes?"** - AI can read your saved files
- **"List my saved files"** - See what files are available

### News & Information
- **"What's the latest news?"** - Get top global headlines
- **"Any news on AI?"** - Fetch headlines for specific topics

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
│   │   ├── news_tools.py      # Google News RSS integration
│   │   ├── gmail_tools.py     # Gmail API integration
│   │   ├── launcher_tools.py  # App/website opening
│   │   ├── window_tools.py    # Minimize/maximize/switch
│   │   ├── audio_tools.py     # Volume & media control
│   │   ├── display_tools.py   # Screen brightness
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

### 6. Gmail Setup (Optional)
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a project and enable the **Gmail API**
- Create OAuth Client ID credentials (Desktop app)
- Download the JSON and save it as `credentials.json` in the root folder
- First time you ask to read emails, ARIA will open a browser to authenticate

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

- **Messaging:**
  - "Do I have any important emails?"
  - "Read me the email from John"
  - "Send a message to Mom on WhatsApp"
  - "Start auto-reply"

- **System Control:**
  - "Set volume to 50%"
  - "Dim my screen by 20%"
  - "Minimize Chrome"
  - "Open my downloads folder"
  - "Switch to VS Code"

- **Screenshot:**
  - "What's on my screen?"
  - "Take a screenshot and analyze it"

- **General:**
  - "Hello"
  - "What's the weather like?"
  - Any general questions

## Architecture

- **ReAct Tool Chaining** - ARIA can automatically call multiple tools sequentially in a single turn (e.g., generate a file, read its path, then automatically open it in your browser).
- **Modular Design** - Clean separation of concerns
- **Tool Registry Pattern** - Easy to add new capabilities
- **Streaming TTS** - Low-latency audio output
- **Multi-threaded Audio** - Non-blocking playback

## Requirements

- Python 3.8+
- Spotify Premium account
- Ollama API access
- PyTorch with CUDA (optional, for faster TTS)
