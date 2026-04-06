"""
Discord Auto-Reply Bot for ARIA
Responds to DMs and whitelisted channels with AI-generated replies
"""

import asyncio
import discord
from discord.ext import commands
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.messaging.controller import MessagingController
from src.messaging.config import DISCORD_USER_TOKEN


class DiscordBot:
    """Discord self-bot for auto-reply functionality."""

    def __init__(self):
        # Initialize messaging controller
        self.controller = MessagingController()

        # Create Discord client
        self.client = discord.Client()

        # Setup event handlers
        self.setup_events()

        print("[Discord Bot] Initialized")

    def setup_events(self):
        """Setup Discord event handlers."""

        @self.client.event
        async def on_ready():
            print(f"[Discord Bot] Logged in as {self.client.user}")
            print(f"[Discord Bot] User ID: {self.client.user.id}")
            print(f"[Discord Bot] Auto-reply active for whitelisted contacts")

        @self.client.event
        async def on_message(message):
            # Ignore own messages
            if message.author.id == self.client.user.id:
                return

            # Only handle DMs and text channels
            if not isinstance(message.channel, (discord.DMChannel, discord.TextChannel)):
                return

            # Get channel ID (None for DMs)
            channel_id = None if isinstance(message.channel, discord.DMChannel) else str(message.channel.id)

            # Handle message through controller
            reply = await self.controller.handle_discord_message(
                message_content=message.content,
                user_id=str(message.author.id),
                user_name=str(message.author),
                channel_id=channel_id
            )

            # Send reply if generated
            if reply:
                try:
                    await message.reply(reply)
                    print(f"[Discord Bot] Sent reply to {message.author}: {reply[:50]}...")
                except Exception as e:
                    print(f"[Discord Bot] Error sending reply: {e}")

        @self.client.event
        async def on_error(event, *args, **kwargs):
            print(f"[Discord Bot] Error in {event}: {args}")

    def run(self):
        """Start the Discord bot."""
        if not DISCORD_USER_TOKEN:
            print("[Discord Bot] ERROR: DISCORD_USER_TOKEN not set in .env")
            print("[Discord Bot] Get your token from Discord Developer Console")
            return

        print("[Discord Bot] Starting...")
        print("[Discord Bot] ⚠️  WARNING: Using user tokens violates Discord ToS")
        print("[Discord Bot] ⚠️  Your account may be banned")

        try:
            self.client.run(DISCORD_USER_TOKEN, bot=False)
        except discord.LoginFailure:
            print("[Discord Bot] ERROR: Invalid Discord token")
        except Exception as e:
            print(f"[Discord Bot] ERROR: {e}")


def main():
    """Main entry point."""
    bot = DiscordBot()
    bot.run()


if __name__ == "__main__":
    main()
