# ARIA Messaging Integration - Quick Reference

## What Was Built

### WhatsApp + Discord Auto-Reply Bot
Based on the reference bot architecture, ARIA can now:
- ✅ Auto-reply to WhatsApp messages with AI
- ✅ Auto-reply to Discord DMs/channels with AI
- ✅ Whitelist contacts for auto-reply
- ✅ Conversation memory (5 turns default)
- ✅ Human-like delays (2-3 seconds)
- ✅ HTTP API for management
- 🔮 Future: Voice integration ready

---

## Architecture

```
WhatsApp (Node.js) ←→ HTTP Server (Flask) ←→ Messaging Controller (Python)
                                                        ↓
Discord (Python) ←――――――――――――――――――――――→ Messaging Controller
                                                        ↓
                                                   LLM Client (Ollama/NVIDIA)
```

---

## Quick Start

### 1. Install Dependencies

**Python:**
```bash
pip install flask discord.py-self
```

**Node.js (for WhatsApp):**
```bash
cd whatsapp_bridge
npm install
```

### 2. Configure

**Get Discord Token:**
- Browser F12 → Network → Find authorization header
- Add to `.env`: `DISCORD_USER_TOKEN=your_token`

**Set Whitelist:**
Edit `messaging_whitelist.json`:
```json
{
  "discord": {"users": ["user_id_here"]},
  "whatsapp": {"contacts": ["+1234567890"]}
}
```

### 3. Run

```bash
python start_messaging.py
# Choose option 3 for full system
```

---

## Files Created

### Python (src/messaging/)
- `config.py` - Configuration & settings
- `controller.py` - Main orchestrator  
- `whitelist.py` - Contact management
- `response_generator.py` - AI reply logic
- `http_server.py` - Flask API

### Bots
- `discord_bot.py` - Discord integration
- `whatsapp_bridge/bridge.js` - WhatsApp integration
- `start_messaging.py` - Launcher

### Config
- `messaging_whitelist.json` - Allowed contacts
- `.env` - Credentials (updated)
- `requirements.txt` - Dependencies (updated)

### Docs
- `MESSAGING_SETUP_GUIDE.md` - Complete setup
- `MESSAGING_INTEGRATION_PLAN.md` - Architecture
- `MESSAGING_QUICK_REFERENCE.md` - This file

---

## HTTP API

**Base URL:** `http://localhost:5000`

### Endpoints

```bash
# Health check
GET /health

# Get stats
GET /stats

# Get whitelist
GET /whitelist

# Add WhatsApp contact
POST /whitelist/whatsapp/add
{"contact": "+1234567890"}

# Add Discord user
POST /whitelist/discord/add_user
{"user_id": "123456789"}

# Toggle auto-reply
POST /toggle_auto_reply
{"enabled": true}
```

---

## Features

### ✅ Implemented
- Auto-reply to whitelisted contacts
- AI-generated responses (Ollama)
- Conversation memory (5 turns)
- Human-like delays
- Discord DMs & channels
- WhatsApp messages
- HTTP management API
- Statistics tracking

### 🔮 Future (Architecture Ready)
- Voice notifications (TTS)
- Voice input for replies (STT)
- Per-contact voice preferences
- Priority alerts for VIPs
- Sentiment analysis
- Auto-categorization

---

## Safety & Warnings

⚠️ **CRITICAL:**
1. **Discord user tokens violate ToS** - risk of ban
2. **WhatsApp automation** - may trigger anti-spam
3. **Use responsibly** - inform contacts if required
4. **Don't abuse rate limits** - delays are built-in

---

## Testing Checklist

- [ ] Python dependencies installed
- [ ] Node.js installed (v18+)
- [ ] Discord token configured
- [ ] Whitelist contacts added
- [ ] HTTP server starts (port 5000)
- [ ] Discord bot connects
- [ ] WhatsApp QR scanned
- [ ] Test message → AI reply received
- [ ] Delays working (2-3s)
- [ ] Conversation memory working

---

## Troubleshooting

**Discord won't connect:**
- Get fresh token from browser
- Check `DISCORD_USER_TOKEN` in .env

**WhatsApp QR not showing:**
- Install Node.js v18+
- `cd whatsapp_bridge && npm install`

**No replies sent:**
- Check `AUTO_REPLY_ENABLED=true`
- Verify whitelist has contacts
- Check Ollama is running

**HTTP errors:**
- Port 5000 in use? Change in code
- Check Flask installed: `pip install flask`

---

## Next Steps

1. **Test Discord:**
   ```bash
   python discord_bot.py
   ```

2. **Test WhatsApp:**
   ```bash
   # Terminal 1
   python -m src.messaging.http_server
   
   # Terminal 2
   cd whatsapp_bridge && node bridge.js
   ```

3. **Full System:**
   ```bash
   python start_messaging.py
   ```

4. **Add Voice (Later):**
   - Set `VOICE_ENABLED=true`
   - Integrate with AudioEngine
   - Per-contact voice preferences

---

## Performance

Expected metrics:
- **AI Generation:** 0.5-3s (depends on model)
- **Discord Delay:** 2s (configurable)
- **WhatsApp Delay:** 3s (configurable)
- **Memory:** ~5 conversations @ 5 turns each
- **HTTP Latency:** <100ms

---

## Security Checklist

- [x] Discord token in .env (not hardcoded)
- [x] Whitelist-only auto-reply
- [x] Conversation logging optional
- [x] No external data sent (local Ollama)
- [ ] Rotate Discord token monthly
- [ ] Review conversation logs regularly
- [ ] Monitor for suspicious activity

---

Ready to deploy! 🚀
