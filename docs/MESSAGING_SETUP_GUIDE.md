# ARIA Messaging Setup Guide

Complete guide to set up WhatsApp and Discord auto-reply functionality.

---

## ⚠️ IMPORTANT WARNINGS

1. **Discord**: Using user tokens violates Discord's Terms of Service - risk of account ban
2. **WhatsApp**: Automation may trigger anti-spam measures
3. **Privacy**: Use responsibly, inform contacts if legally required
4. **Rate Limits**: Don't abuse - delays are built-in to mimic human behavior

---

## Prerequisites

### Python Dependencies
```bash
pip install flask discord.py-self python-dotenv asyncio
```

### Node.js (for WhatsApp)
- Install Node.js v18+ from: https://nodejs.org/
- Verify: `node --version` and `npm --version`

---

## Setup Steps

### 1. Get Discord User Token

1. Open Discord in your browser (not desktop app)
2. Press `F12` to open Developer Tools
3. Go to **Network** tab
4. Refresh Discord (Ctrl+R)
5. Look for any request to `discord.com/api`
6. Click on it → **Headers** → **Request Headers**
7. Find `authorization:` - copy the value
8. Paste into `.env` as `DISCORD_USER_TOKEN`

Example:
```env
DISCORD_USER_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.GaBcDe.FgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJk
```

### 2. Configure Whitelist

Edit `messaging_whitelist.json`:

```json
{
  "discord": {
    "users": ["123456789012345678"],  // Discord user IDs
    "channels": ["987654321098765432"]  // Channel IDs (optional)
  },
  "whatsapp": {
    "contacts": ["+1234567890", "John Doe"]  // Phone numbers or names
  }
}
```

**How to get Discord user/channel IDs:**
1. Enable Developer Mode: Settings → Advanced → Developer Mode
2. Right-click on user/channel → Copy ID

### 3. Install WhatsApp Bridge Dependencies

```bash
cd whatsapp_bridge
npm install
```

### 4. Update .env

```env
# Required for Discord
DISCORD_USER_TOKEN=your_token_here

# Optional - leave empty to use whitelist.json
DISCORD_ALLOWED_USERS=
DISCORD_ALLOWED_CHANNELS=

# WhatsApp settings
WHATSAPP_REPLY_DELAY_MS=3000
DISCORD_REPLY_DELAY_MS=2000

# Features
AUTO_REPLY_ENABLED=true
VOICE_ENABLED=false
CONVERSATION_MEMORY=true
AI_MESSAGING_MODEL=qwen3.5:2b
```

---

## Running the System

### Option 1: Full System (Discord + WhatsApp)
```bash
python start_messaging.py
# Choose option 3
```

1. HTTP server starts on port 5000
2. Discord bot connects
3. WhatsApp bridge starts - **SCAN QR CODE**
4. Both platforms ready!

### Option 2: Discord Only
```bash
python start_messaging.py
# Choose option 1
```

or directly:
```bash
python discord_bot.py
```

### Option 3: WhatsApp Only
```bash
python start_messaging.py
# Choose option 2
```

or manually:
```bash
# Terminal 1: Start HTTP server
python -m src.messaging.http_server

# Terminal 2: Start WhatsApp bridge
cd whatsapp_bridge
node bridge.js
```

---

## Testing

### Test Discord
1. Send a DM to yourself from a whitelisted user
2. Check console logs for AI response
3. Should reply with AI-generated message after 2s delay

### Test WhatsApp
1. Send message from whitelisted contact
2. Scan QR code if first time
3. Check console for AI response
4. Should reply after 3s delay

---

## Managing Whitelist

### Add Contact (HTTP API)

**Add WhatsApp Contact:**
```bash
curl -X POST http://localhost:5000/whitelist/whatsapp/add \
  -H "Content-Type: application/json" \
  -d '{"contact": "+1234567890"}'
```

**Add Discord User:**
```bash
curl -X POST http://localhost:5000/whitelist/discord/add_user \
  -H "Content-Type: application/json" \
  -d '{"user_id": "123456789012345678"}'
```

### View Whitelist
```bash
curl http://localhost:5000/whitelist
```

### Toggle Auto-Reply
```bash
# Disable
curl -X POST http://localhost:5000/toggle_auto_reply \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Enable
curl -X POST http://localhost:5000/toggle_auto_reply \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### View Stats
```bash
curl http://localhost:5000/stats
```

---

## Troubleshooting

### Discord Bot Won't Start
- **Error: Invalid token** → Get new token from browser
- **Error: discord.py not found** → `pip install discord.py-self`

### WhatsApp Bridge Won't Start
- **Error: node not found** → Install Node.js v18+
- **Error: npm install fails** → Delete `node_modules` and retry
- **QR code not showing** → Check console for errors

### No Replies Sent
1. Check whitelist configuration
2. Verify `AUTO_REPLY_ENABLED=true` in `.env`
3. Check console logs for errors
4. Test HTTP server: `curl http://localhost:5000/health`

### Ollama/LLM Errors
- Make sure Ollama is running
- Check `AI_MESSAGING_MODEL` is valid
- Test: `ollama list`

---

## Security Best Practices

1. **Never share your Discord token** - it's like your password
2. **Use strong whitelist** - only trusted contacts
3. **Monitor logs** - check for suspicious activity
4. **Rotate tokens** - change Discord token periodically
5. **Backup `.env`** - but keep it private

---

## File Structure

```
D:\VERISON 3\
├── src/
│   └── messaging/
│       ├── config.py              # Configuration
│       ├── controller.py          # Main orchestrator
│       ├── whitelist.py           # Whitelist manager
│       ├── response_generator.py  # AI reply generator
│       └── http_server.py         # Flask API
├── whatsapp_bridge/
│   ├── bridge.js                  # WhatsApp Node.js bridge
│   └── package.json               # Node dependencies
├── discord_bot.py                 # Discord bot
├── start_messaging.py             # Main launcher
├── messaging_whitelist.json       # Contact whitelist
└── .env                           # Credentials
```

---

## Future: Voice Integration

The system is designed for future voice integration:

```python
# In controller.py
def _voice_notify(self, platform, contact_name, message):
    """Read incoming message aloud via TTS"""
    # Will integrate with AudioEngine
    pass

def _voice_confirm_reply(self, reply):
    """Confirm sent reply via voice"""
    # Will integrate with AudioEngine
    pass
```

To enable (when ready):
```env
VOICE_ENABLED=true
```

---

## Advanced Configuration

### Custom AI Prompt

Edit `src/messaging/config.py`:
```python
AI_SYSTEM_PROMPT = """Your custom prompt here..."""
```

### Change Reply Delays

In `.env`:
```env
DISCORD_REPLY_DELAY_MS=1000  # 1 second
WHATSAPP_REPLY_DELAY_MS=5000 # 5 seconds
```

### Conversation Memory

Control how many message turns to remember:
```python
# In src/messaging/config.py
MAX_HISTORY_TURNS = 10  # Remember last 10 exchanges
```

---

## Support

For issues:
1. Check console logs
2. Verify all dependencies installed
3. Test HTTP server health endpoint
4. Check whitelist configuration
5. Review .env settings

Happy auto-replying! 🤖
