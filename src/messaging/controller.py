"""
Messaging Controller
Main orchestrator for WhatsApp and Discord auto-reply functionality
"""

import asyncio
import time
from typing import Dict, Optional
from src.messaging.whitelist import WhitelistManager
from src.messaging.response_generator import ResponseGenerator
from src.messaging.history import MessagingHistory
from src.messaging.config import (
    AUTO_REPLY_ENABLED,
    VOICE_ENABLED,
    CONVERSATION_MEMORY,
    DISCORD_REPLY_DELAY_MS,
    WHATSAPP_REPLY_DELAY_MS
)


class MessagingController:
    """Central controller for messaging platforms."""

    def __init__(self):
        self.whitelist_manager = WhitelistManager()
        self.response_generator = ResponseGenerator()
        self.history_manager = MessagingHistory()
        self.auto_reply_enabled = AUTO_REPLY_ENABLED
        self.voice_enabled = VOICE_ENABLED
        self.pending_timers = {} # Store asyncio tasks

        # Statistics
        self.stats = {
            "discord_messages_received": 0,
            "discord_messages_sent": 0,
            "whatsapp_messages_received": 0,
            "whatsapp_messages_sent": 0,
            "total_ai_calls": 0
        }

    async def _follow_up_timer(self, platform: str, contact_id: str, contact_name: str, delay_seconds: int = 600):
        """Wait for a certain time and then proactively message the user if they haven't replied."""
        try:
            await asyncio.sleep(delay_seconds)
            # If we wake up and haven't been cancelled, it means the user hasn't replied!
            print(f"[Proactive] User {contact_name} hasn't replied in {delay_seconds} seconds. Following up.")
            await self.initiate_conversation(
                platform=platform,
                contact_id=contact_id,
                contact_name=contact_name,
                context="The user hasn't responded to your previous question for a while. Send a short, casual follow-up message to check if they're still there."
            )
        except asyncio.CancelledError:
            # The timer was cancelled because the user replied.
            pass
        finally:
            timer_key = f"{platform}:{contact_id}"
            if timer_key in self.pending_timers:
                del self.pending_timers[timer_key]

    def _cancel_timer(self, platform: str, contact_id: str):
        """Cancel an existing follow-up timer for a contact."""
        timer_key = f"{platform}:{contact_id}"
        if timer_key in self.pending_timers:
            self.pending_timers[timer_key].cancel()
            del self.pending_timers[timer_key]

    def _check_and_start_timer(self, reply: str, platform: str, contact_id: str, contact_name: str):
        """Check if the reply warrants a follow-up (e.g., ends in a question) and start timer."""
        # Cancel any existing timer first
        self._cancel_timer(platform, contact_id)

        # Simple heuristic: if the AI asked a question, expect a response
        if reply.strip().endswith('?'):
            timer_key = f"{platform}:{contact_id}"
            # Start a 10 minute (600s) timer, you can lower this to 10s for testing
            task = asyncio.create_task(self._follow_up_timer(platform, contact_id, contact_name, 600))
            self.pending_timers[timer_key] = task

    async def handle_discord_message(
        self,
        message_content: str,
        user_id: str,
        user_name: str,
        channel_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Handle incoming Discord message.

        Args:
            message_content: The message text
            user_id: Discord user ID
            user_name: Discord username
            channel_id: Channel ID (for channel messages)

        Returns:
            AI-generated reply or None if not whitelisted
        """
        self.stats["discord_messages_received"] += 1

        # Check whitelist
        is_dm = channel_id is None
        if is_dm:
            if not self.whitelist_manager.is_discord_user_allowed(user_id):
                print(f"[Discord] Ignored message from non-whitelisted user: {user_name}")
                return None
        else:
            if not self.whitelist_manager.is_discord_channel_allowed(channel_id):
                print(f"[Discord] Ignored message from non-whitelisted channel: {channel_id}")
                return None

        # Check if auto-reply is enabled
        if not self.auto_reply_enabled:
            print(f"[Discord] Auto-reply disabled, skipping message from {user_name}")
            return None

        print(f"[Discord] Received message from {user_name}: {message_content[:50]}...")
        # Cancel any pending follow-up timers for this user
        self._cancel_timer("discord", user_id)

        # Generate AI response
        self.stats["total_ai_calls"] += 1
        reply = self.response_generator.generate_reply(
            message=message_content,
            platform="discord",
            contact_id=user_id,
            contact_name=user_name
        )

        # Record interaction for autonomous mode
        self.history_manager.record_interaction(
            platform="discord",
            contact_id=user_id,
            contact_name=user_name,
            message=message_content,
            reply=reply
        )

        # Start a follow-up timer if we expect a reply
        self._check_and_start_timer(reply, "discord", user_id, user_name)

        # Simulate human-like delay
        delay_seconds = DISCORD_REPLY_DELAY_MS / 1000
        await asyncio.sleep(delay_seconds)

        self.stats["discord_messages_sent"] += 1
        return reply

    async def handle_whatsapp_message(
        self,
        message_content: str,
        contact_id: str,
        contact_name: str
    ) -> Optional[str]:
        """
        Handle incoming WhatsApp message.

        Args:
            message_content: The message text
            contact_id: WhatsApp contact ID (phone number or ID)
            contact_name: Contact display name

        Returns:
            AI-generated reply or None if not whitelisted
        """
        self.stats["whatsapp_messages_received"] += 1

        # Check whitelist (by name or ID)
        if not (self.whitelist_manager.is_whatsapp_contact_allowed(contact_id) or
                self.whitelist_manager.is_whatsapp_contact_allowed(contact_name)):
            print(f"[WhatsApp] Ignored message from non-whitelisted contact: {contact_name}")
            return None

        # Check if auto-reply is enabled
        if not self.auto_reply_enabled:
            print(f"[WhatsApp] Auto-reply disabled, skipping message from {contact_name}")
            return None

        print(f"[WhatsApp] Received message from {contact_name}: {message_content[:50]}...")
        # Cancel any pending follow-up timers for this user
        self._cancel_timer("whatsapp", contact_id)

        # Generate AI response
        self.stats["total_ai_calls"] += 1
        reply = self.response_generator.generate_reply(
            message=message_content,
            platform="whatsapp",
            contact_id=contact_id,
            contact_name=contact_name
        )

        # Record interaction for autonomous mode
        self.history_manager.record_interaction(
            platform="whatsapp",
            contact_id=contact_id,
            contact_name=contact_name,
            message=message_content,
            reply=reply
        )

        # Start a follow-up timer if we expect a reply
        self._check_and_start_timer(reply, "whatsapp", contact_id, contact_name)

        # Simulate human-like delay
        delay_seconds = WHATSAPP_REPLY_DELAY_MS / 1000
        await asyncio.sleep(delay_seconds)

        self.stats["whatsapp_messages_sent"] += 1
        return reply

    async def initiate_conversation(
        self, 
        platform: str, 
        contact_id: str, 
        contact_name: str, 
        context: str
    ) -> Optional[str]:
        """
        Proactively initiate a conversation with a contact.
        
        Args:
            platform: 'discord' or 'whatsapp'
            contact_id: Contact ID
            contact_name: Contact name
            context: The reason or context for initiation
            
        Returns:
            The proactive message sent
        """
        print(f"[Controller] Initiating proactive message to {contact_name} on {platform}...")
        
        # Generate a proactive message based on context
        prompt = f"Proactively reach out to {contact_name}. Context: {context}"
        message = self.response_generator.generate_reply(
            message=prompt,
            platform=platform,
            contact_id=contact_id,
            contact_name=contact_name
        )
        
        # Record this initiation as an interaction
        self.history_manager.record_interaction(
            platform=platform,
            contact_id=contact_id,
            contact_name=contact_name,
            message=f"[INITIATED: {context}]",
            reply=message
        )
        
        return message

    def toggle_auto_reply(self, enabled: bool):
        """Enable or disable auto-reply."""
        self.auto_reply_enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"[Controller] Auto-reply {status}")

    def get_stats(self) -> Dict:
        """Get messaging statistics."""
        return self.stats

    def clear_conversation(self, platform: str, contact_id: str):
        """Clear conversation history for a contact."""
        self.response_generator.clear_conversation(platform, contact_id)

    # Future: Voice integration hooks
    def _voice_notify(self, platform: str, contact_name: str, message: str):
        """
        [Future] Voice notification for incoming message.
        Will use TTS to read the message aloud.
        """
        if not self.voice_enabled:
            return

        # TODO: Implement voice notification
        # audio_engine.queue_text(f"New message from {contact_name} on {platform}")
        # audio_engine.queue_text(message)
        pass

    def _voice_confirm_reply(self, reply: str):
        """
        [Future] Voice confirmation of sent reply.
        """
        if not self.voice_enabled:
            return

        # TODO: Implement voice confirmation
        # audio_engine.queue_text(f"Sent: {reply}")
        pass
