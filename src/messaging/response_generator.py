"""
AI Response Generator
Generates AI-powered replies for messaging platforms
"""

import time
from typing import List, Dict, Optional
from src.core.llm_client import LLMClient
from src.messaging.config import AI_SYSTEM_PROMPT, MAX_HISTORY_TURNS, AI_MODEL


class ResponseGenerator:
    """Generates AI responses for messages with conversation memory."""

    def __init__(self):
        self.llm_client = LLMClient()
        self.conversation_history: Dict[str, List[Dict]] = {}

    def _get_conversation_key(self, platform: str, contact_id: str) -> str:
        """Generate unique key for conversation tracking."""
        return f"{platform}:{contact_id}"

    def _init_conversation(self, key: str):
        """Initialize conversation history for a contact."""
        if key not in self.conversation_history:
            self.conversation_history[key] = [
                {"role": "system", "content": AI_SYSTEM_PROMPT}
            ]

    def _add_to_history(self, key: str, role: str, content: str):
        """Add message to conversation history."""
        self._init_conversation(key)
        self.conversation_history[key].append({
            "role": role,
            "content": content
        })

        # Trim history to MAX_HISTORY_TURNS (keep system prompt + last N turns)
        # Each turn = user message + assistant response = 2 messages
        max_messages = 1 + (MAX_HISTORY_TURNS * 2)  # system + turns
        if len(self.conversation_history[key]) > max_messages:
            # Keep system prompt (index 0) and last messages
            system_msg = self.conversation_history[key][0]
            recent_msgs = self.conversation_history[key][-(max_messages-1):]
            self.conversation_history[key] = [system_msg] + recent_msgs

    def generate_reply(
        self,
        message: str,
        platform: str,
        contact_id: str,
        contact_name: Optional[str] = None
    ) -> str:
        """
        Generate AI reply to a message.

        Args:
            message: The incoming message text
            platform: "discord" or "whatsapp"
            contact_id: Unique identifier for the contact
            contact_name: Optional display name for the contact

        Returns:
            AI-generated reply string
        """
        conv_key = self._get_conversation_key(platform, contact_id)
        self._init_conversation(conv_key)

        # Add context about who sent the message
        if contact_name:
            context_message = f"[Message from {contact_name}]: {message}"
        else:
            context_message = message

        # Add user message to history
        self._add_to_history(conv_key, "user", context_message)

        try:
            # Generate response
            start_time = time.time()

            response = self.llm_client.chat(
                model=AI_MODEL,
                messages=self.conversation_history[conv_key],
                stream=False
            )

            latency = time.time() - start_time
            reply = response.get('message', {}).get('content', '')

            if not reply:
                reply = "Sorry, I couldn't generate a response right now."

            # Add assistant reply to history
            self._add_to_history(conv_key, "assistant", reply)

            print(f"[AI] Generated reply in {latency:.2f}s: {reply[:50]}...")

            return reply

        except Exception as e:
            print(f"[ERROR] Failed to generate reply: {e}")
            return "Sorry, I'm having trouble responding right now."

    def clear_conversation(self, platform: str, contact_id: str):
        """Clear conversation history for a contact."""
        conv_key = self._get_conversation_key(platform, contact_id)
        if conv_key in self.conversation_history:
            del self.conversation_history[conv_key]

    def get_conversation_history(self, platform: str, contact_id: str) -> List[Dict]:
        """Get conversation history for a contact."""
        conv_key = self._get_conversation_key(platform, contact_id)
        return self.conversation_history.get(conv_key, [])

    def get_active_conversations(self) -> List[str]:
        """Get list of active conversation keys."""
        return list(self.conversation_history.keys())
