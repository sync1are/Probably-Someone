"""
Messaging Configuration
Settings for WhatsApp and Discord auto-reply functionality
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# File used to share status between the main process and messaging subprocesses
_STATUS_FILE = Path(__file__).parent.parent.parent / "messaging" / "current_status.json"


def get_current_status() -> str:
    """Read Aze's current status from the shared status file."""
    try:
        if _STATUS_FILE.exists():
            data = json.loads(_STATUS_FILE.read_text(encoding="utf-8"))
            return data.get("status", "")
    except Exception:
        pass
    return ""


def set_current_status_file(status: str):
    """Write Aze's current status to the shared status file."""
    _STATUS_FILE.write_text(
        json.dumps({"status": status}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# Discord Configuration
DISCORD_USER_TOKEN = os.getenv('DISCORD_USER_TOKEN', '')
DISCORD_ALLOWED_USERS = os.getenv('DISCORD_ALLOWED_USERS', '').split(',')
DISCORD_ALLOWED_CHANNELS = os.getenv('DISCORD_ALLOWED_CHANNELS', '').split(',')
DISCORD_REPLY_DELAY_MS = int(os.getenv('DISCORD_REPLY_DELAY_MS', '2000'))

# WhatsApp Configuration
WHATSAPP_ALLOWED_CONTACTS = os.getenv('WHATSAPP_ALLOWED_CONTACTS', '').split(',')
WHATSAPP_REPLY_DELAY_MS = int(os.getenv('WHATSAPP_REPLY_DELAY_MS', '3000'))
WHATSAPP_BRIDGE_PORT = int(os.getenv('WHATSAPP_BRIDGE_PORT', '3000'))

# AI Configuration
AI_SYSTEM_PROMPT = """You are Alex, an AI assistant responding on behalf of Aze.

Aze is unavailable right now and you are managing his incoming messages.

## How to behave
- Be casual, friendly, and concise. Match the vibe of the person messaging.
- Do NOT over-explain who you are every single message. Introduce yourself once, naturally.
- Do NOT ask the person what Aze is doing — you don't need them to tell you that.
- If Aze has a current status set (e.g. "Aze is sleeping"), mention it briefly when relevant.
- Keep replies short unless they ask something detailed.
- Hold a real back-and-forth conversation. Don't just dump info and stop.
- Take notes if someone leaves a message for Aze and confirm you'll pass it on.
- EXTREMELY IMPORTANT: If a contact asks you to tell Aze something, or leave a message for him, DO NOT just say 'Okay'. You MUST use the `store_user_message` tool to log it so Aze actually sees it when he returns.
- If you use the `store_user_message` tool, tell the contact you have successfully saved the message for Aze.

## First message
If this is your first message to someone, briefly introduce yourself:
  "Hey! I'm Alex, Aze's assistant. He's not available right now — I can pass on a message or help you out."
Keep it short. Don't ask multiple questions at once.
"""

MAX_HISTORY_TURNS = 10  # Allow a decent conversation memory
AI_MODEL = os.getenv('AI_MESSAGING_MODEL', 'glm-5.1:cloud')

# Feature Flags
AUTO_REPLY_ENABLED = os.getenv('AUTO_REPLY_ENABLED', 'true').lower() == 'true'
VOICE_ENABLED = os.getenv('VOICE_ENABLED', 'false').lower() == 'true'
CONVERSATION_MEMORY = True  # Enabled for multi-turn conversations
CURRENT_STATUS = ""  # Legacy in-memory fallback — use get_current_status() for cross-process reads

# Logging
MESSAGING_LOG_FILE = 'logs/messaging.log'
LOG_CONVERSATIONS = os.getenv('LOG_CONVERSATIONS', 'true').lower() == 'true'
