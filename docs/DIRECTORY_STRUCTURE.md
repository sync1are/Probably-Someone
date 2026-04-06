# 📁 ARIA Directory Structure

Clean, organized project structure.

```
D:\VERISON 3\
│
├── 📄 app.py                    # Main ARIA application entry point
├── 📄 tools.json                # Tool definitions for LLM
├── 📄 requirements.txt          # Python dependencies
├── 📄 .env                      # Environment variables (API keys)
├── 📄 .gitignore               # Git ignore rules
│
├── 📂 src/                      # Source code
│   ├── 📂 core/                # Core modules
│   │   ├── llm_client.py       # Ollama/LLM client
│   │   ├── audio_engine.py     # TTS and audio
│   │   └── tts_server.py       # TTS server
│   │
│   ├── 📂 tools/               # Tool implementations
│   │   ├── registry.py         # Tool dispatcher
│   │   ├── system_tools.py     # Screenshot, clipboard, etc.
│   │   ├── spotify_tools.py    # Spotify integration
│   │   ├── web_tools.py        # Web scraping
│   │   └── messaging_tools.py  # Messaging setup/control
│   │
│   ├── 📂 messaging/           # Messaging module
│   │   ├── config.py           # Messaging configuration
│   │   ├── controller.py       # Main orchestrator
│   │   ├── whitelist.py        # Contact management
│   │   ├── response_generator.py # AI reply logic
│   │   └── http_server.py      # Flask API server
│   │
│   └── config.py               # Main app configuration
│
├── 📂 messaging/               # Messaging applications
│   ├── discord_bot.py          # Discord bot
│   ├── start_messaging.py      # Messaging launcher
│   ├── messaging_whitelist.json # Contact whitelist
│   │
│   └── 📂 whatsapp_bridge/    # WhatsApp Node.js bridge
│       ├── bridge.js           # WhatsApp client
│       ├── package.json        # Node dependencies
│       └── node_modules/       # Installed packages
│
├── 📂 tests/                   # Testing files
│   ├── test_suite.py          # Comprehensive test suite
│   ├── test_nvidia.py         # NVIDIA API benchmark
│   ├── run_tests.bat          # Test launcher
│   └── test_report_*.json     # Test results
│
├── 📂 docs/                    # Documentation
│   ├── INDEX.md               # Documentation index
│   ├── README.md              # Project overview
│   ├── FEATURES_ROADMAP.md    # Feature roadmap
│   ├── TESTING_GUIDE.md       # Testing guide
│   ├── MESSAGING_*.md         # Messaging docs
│   └── ... (other docs)
│
├── 📂 venv/                    # Python virtual environment
├── 📂 venv_cuda/              # CUDA-enabled venv
│
└── 📂 .claude/                # Claude Code files
    └── CLAUDE.md              # Project instructions

```

---

## 📋 File Count Summary

| Directory | Files | Purpose |
|-----------|-------|---------|
| **Root** | 4 | Core app files |
| **src/** | 12 | Source code modules |
| **messaging/** | 5 | Messaging apps & bridge |
| **tests/** | 6 | Test suite & reports |
| **docs/** | 13 | Documentation |
| **Total** | 40+ | Clean & organized |

---

## 🎯 Quick Navigation

### Run ARIA
```bash
python app.py
```

### Run Tests
```bash
cd tests
python test_suite.py
```

### Start Messaging
```bash
cd messaging
python start_messaging.py
```

### View Docs
```bash
cd docs
cat INDEX.md
```

---

## 🧹 Cleanup Summary

### ✅ Organized
- All messaging files → `/messaging`
- All test files → `/tests`
- All docs → `/docs`
- Source code → `/src`

### ✅ Removed
- Old "testing folder"
- Scattered test reports (moved to /tests)
- Temporary files

### ✅ Clean Root
Only essential files remain in root:
- `app.py` - Main entry point
- `tools.json` - Tool definitions
- `requirements.txt` - Dependencies
- `.env` - Configuration

---

## 📦 Module Structure

### Core (`src/core/`)
- LLM client
- Audio/TTS engine
- Core utilities

### Tools (`src/tools/`)
- System tools (screenshot, clipboard)
- Spotify integration
- Messaging setup
- Web tools

### Messaging (`src/messaging/`)
- Controller logic
- AI response generator
- HTTP server
- Whitelist management

### Apps (`messaging/`)
- Discord bot
- WhatsApp bridge
- Launcher scripts

---

## 🚀 Benefits

✅ **Clean Root** - Only 4 essential files  
✅ **Organized** - Everything has its place  
✅ **Scalable** - Easy to add new features  
✅ **Maintainable** - Clear structure  
✅ **Professional** - Industry-standard layout  

---

**Directory cleaned and organized!** 🎉
