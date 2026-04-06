# ARIA Messaging Integration

WhatsApp and Discord auto-reply functionality using AI.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  ARIA Core (Python)                 │
│  ┌──────────────────────────────────────────────┐  │
│  │         LLM Client (Ollama/NVIDIA)           │  │
│  └──────────────────────────────────────────────┘  │
│                        ▲                            │
│                        │                            │
│  ┌──────────────────────────────────────────────┐  │
│  │      Messaging Controller (Python)           │  │
│  │  - Message queue                             │  │
│  │  - Response generator                        │  │
│  │  - Whitelist manager                         │  │
│  │  - [Future: Voice integration hooks]         │  │
│  └──────────────────────────────────────────────┘  │
│           ▲                           ▲             │
└───────────┼───────────────────────────┼─────────────┘
            │                           │
    ┌───────┴────────┐         ┌────────┴────────┐
    │  WhatsApp Bot  │         │   Discord Bot   │
    │   (Node.js)    │         │    (Python)     │
    │ whatsapp-web.js│         │   discord.py    │
    └────────────────┘         └─────────────────┘
```

## Implementation Options

### Option 1: Hybrid (Recommended)
- **Discord**: Native Python (`discord.py`)
- **WhatsApp**: Node.js bridge → Python via HTTP/WebSocket
- **Pros**: Best of both worlds, native libraries
- **Cons**: Two processes to manage

### Option 2: Full Python
- **Discord**: `discord.py`
- **WhatsApp**: `pywhatkit` or `yowsup` (limited, less stable)
- **Pros**: Single Python process
- **Cons**: WhatsApp support is hacky

### Option 3: Full Node.js Bridge
- **Discord**: `discord.js-selfbot-v13`
- **WhatsApp**: `whatsapp-web.js`
- **Python ARIA**: Expose HTTP API for LLM calls
- **Pros**: Reference bot's exact setup
- **Cons**: Node.js dependency

## Recommended: **Option 1 (Hybrid)**

---

## Components to Build

### 1. Python Messaging Controller (`src/messaging/`)
- `controller.py` - Main orchestrator
- `whitelist.py` - Contact management
- `message_queue.py` - Queue handler
- `response_generator.py` - AI reply logic
- `config.py` - Messaging settings

### 2. Discord Bot (Python)
- `discord_bot.py` - Discord integration
- Uses `discord.py` library

### 3. WhatsApp Bridge (Node.js)
- `whatsapp_bridge.js` - WhatsApp handler
- HTTP server to communicate with Python
- Based on reference bot's code

### 4. Configuration
- `.env` - Discord tokens, WhatsApp session
- `messaging_config.json` - Whitelists, settings

---

## Installation Steps

### Python Dependencies
```bash
pip install discord.py-self flask asyncio
```

### Node.js Dependencies (for WhatsApp)
```bash
cd whatsapp_bridge
npm install whatsapp-web.js qrcode-terminal express
```

---

## Configuration Structure

```json
{
  "discord": {
    "user_token": "YOUR_DISCORD_USER_TOKEN",
    "allowed_users": ["user_id_1", "user_id_2"],
    "allowed_channels": ["channel_id_1"],
    "reply_delay_ms": 2000
  },
  "whatsapp": {
    "allowed_contacts": ["+1234567890", "Contact Name"],
    "reply_delay_ms": 3000
  },
  "ai": {
    "system_prompt": "You are ARIA, a helpful assistant...",
    "max_history_turns": 5,
    "model": "qwen3.5:2b"
  },
  "features": {
    "auto_reply": true,
    "voice_enabled": false,
    "conversation_memory": true
  }
}
```

---

## Safety & Warnings

⚠️ **IMPORTANT:**
1. **Discord**: Using user tokens violates Discord ToS - risk of ban
2. **WhatsApp**: Automation may trigger anti-spam measures
3. **Rate Limiting**: Add delays to avoid detection
4. **Privacy**: Conversation data stored locally for memory

---

## Future Voice Integration

Architecture is designed for future voice features:
- `voice_hooks.py` - TTS message reading
- `voice_input.py` - STT for voice replies
- Contact-level voice preferences
- Priority voice alerts for VIP contacts

---

## Files to Create

1. `src/messaging/controller.py`
2. `src/messaging/whitelist.py`
3. `src/messaging/response_generator.py`
4. `discord_bot.py`
5. `whatsapp_bridge/bridge.js`
6. `whatsapp_bridge/package.json`
7. `messaging_config.json`
8. `start_messaging.py` - Main launcher

---

## Next Steps

1. Review architecture
2. I'll create all components
3. Setup configuration files
4. Test Discord bot first (easier)
5. Add WhatsApp bridge
6. Add voice hooks for future upgrade
