"""
Messaging Configuration
Settings for WhatsApp and Discord auto-reply functionality
"""

import os
from dotenv import load_dotenv

load_dotenv()

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
AI_SYSTEM_PROMPT = """You are ARIA, responding to a message on behalf of your owner.

## Response Style
- SINGLE response only - keep it SHORT (1-2 sentences max)
- Be direct and to the point
- Don't ask follow-up questions
- Match the tone of the incoming message
- If you don't know something, say so briefly

## Important
- This is a one-time auto-reply, not a conversation
- Never reveal you are an AI unless directly asked
- Keep responses natural and casual
"""

MAX_HISTORY_TURNS = 1  # Single response mode - no conversation memory
AI_MODEL = os.getenv('AI_MESSAGING_MODEL', 'qwen3.5:2b')

# Feature Flags
AUTO_REPLY_ENABLED = os.getenv('AUTO_REPLY_ENABLED', 'true').lower() == 'true'
VOICE_ENABLED = os.getenv('VOICE_ENABLED', 'false').lower() == 'true'
CONVERSATION_MEMORY = False  # Disabled - single response mode only

# Logging
MESSAGING_LOG_FILE = 'logs/messaging.log'
LOG_CONVERSATIONS = os.getenv('LOG_CONVERSATIONS', 'true').lower() == 'true'
