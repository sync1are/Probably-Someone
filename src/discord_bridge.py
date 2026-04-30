import os
import io
import json
import asyncio
import threading
import base64
import discord
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path

from src.core.agent import Agent
from src.config import SYSTEM_PROMPT, NVIDIA_SYSTEM_PROMPT, DEFAULT_MODEL, NVIDIA_MODEL, LM_STUDIO_MODEL
from src.utils.tool_utils import load_tools # Use centralized tool loader

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_USER_ID = os.getenv("DISCORD_USER_ID")

class PermissionView(discord.ui.View):
    def __init__(self, user_id, timeout=120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != str(self.user_id):
            await interaction.response.send_message("This isn't your prompt!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Allow ✅", style=discord.ButtonStyle.green)
    async def allow(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Deny ❌", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()

class DiscordAgentBridge:
    def __init__(self, backend="ollama", model=None):
        self.backend = backend
        self.model = model or DEFAULT_MODEL
        
        system_prompt = SYSTEM_PROMPT
        if backend == "nvidia":
            system_prompt = NVIDIA_SYSTEM_PROMPT
            self.model = model or NVIDIA_MODEL
        elif backend == "lm_studio":
            self.model = model or LM_STUDIO_MODEL

        self.tools = load_tools()
        self.agent = Agent(
            backend=self.backend,
            model=self.model,
            system_prompt=system_prompt,
            tools=self.tools
        )
        self.is_processing = False

    async def send_split(self, ctx, text, code_block=False):
        if not text:
            return
        chunk_size = 1990 if not code_block else 1980
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            if code_block:
                await ctx.send(f"```\n{chunk}\n```")
            else:
                await ctx.send(chunk)

    def _log_error(self, error):
        """Log errors with a timestamp to discord_failures.log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] Error: {str(error)}\n"
        try:
            with open("discord_failures.log", "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[Discord] Failed to write to log file: {e}")

    def _intense_log(self, event_type, data):
        """Intense logging for separate viewer."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        try:
            with open("discord_intense.log", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            pass

    async def handle_message(self, message):
        if self.is_processing:
            await message.channel.send("⏳ I'm still processing your previous request...")
            return

        self.is_processing = True
        self._intense_log("USER_QUERY", {"user_id": str(message.author.id), "content": message.content})
        
        # Timing and status tracking
        start_time = asyncio.get_event_loop().time()
        first_token_time = None
        current_tool = None
        total_prompt_tokens = 0
        total_eval_tokens = 0
        
        # Initial status embed
        embed = discord.Embed(
            title="ARIA Status",
            description="🔍 Thinking...",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Model: {self.model}")
        status_message = await message.channel.send(embed=embed)

        async def update_status(status_text, finalized=False):
            nonlocal first_token_time
            
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            
            embed.description = status_text
            embed.color = discord.Color.green() if finalized else discord.Color.blue()
            
            # Update fields
            embed.clear_fields()
            
            ttft_str = f"{first_token_time - start_time:.2f}s" if first_token_time else "..."
            metrics_str = f"⏱️ **TTFT:** {ttft_str}\n"
            metrics_str += f"⏳ **Total Elapsed:** {elapsed:.2f}s\n"
            
            if total_prompt_tokens or total_eval_tokens:
                metrics_str += f"🎟️ **Tokens:** {total_prompt_tokens}p / {total_eval_tokens}e"
            
            embed.add_field(name="Metrics", value=metrics_str, inline=False)
            
            if current_tool:
                embed.add_field(name="Active Tool", value=f"🔧 `{current_tool}`", inline=False)
            
            if finalized:
                embed.description = "✅ Completed"
            
            await status_message.edit(embed=embed)

        # We'll buffer the output to avoid too many small messages
        output_buffer = []
        last_send_time = asyncio.get_event_loop().time()
        
        async def output_callback(content):
            nonlocal last_send_time, first_token_time
            
            self._intense_log("LLM_OUTPUT_CHUNK", {"content": content})
            
            if first_token_time is None:
                first_token_time = asyncio.get_event_loop().time()
                await update_status("✍️ Generating response...")

            output_buffer.append(content)
            
            # If we have a decent amount of text or some time has passed, send it
            current_time = asyncio.get_event_loop().time()
            if len("".join(output_buffer)) > 500 or (current_time - last_send_time > 2.0):
                text_to_send = "".join(output_buffer)
                if text_to_send.strip():
                    await self.send_split(message.channel, text_to_send)
                    output_buffer.clear()
                    last_send_time = current_time

        async def tool_callback(name, args):
            nonlocal current_tool
            current_tool = name
            self._intense_log("TOOL_CALL", {"name": name, "args": args})
            await update_status(f"🔧 Executing: `{name}`")

        async def tool_result_callback(name, result):
            nonlocal current_tool
            current_tool = None
            
            self._intense_log("TOOL_RESULT", {"name": name, "result": result})
            
            if name == "take_screenshot" and result.get("success"):
                filepath = result.get("filepath")
                if filepath and os.path.exists(filepath):
                    await message.channel.send(file=discord.File(filepath))
            
            await update_status("🔍 Thinking...")

        async def permission_callback(name, args):
            # Create a descriptive embed for the permission request
            args_str = json.dumps(args, indent=2)
            perm_embed = discord.Embed(
                title="⚠️ Permission Required",
                description=f"ARIA is requesting permission to execute: `{name}`",
                color=discord.Color.orange()
            )
            
            # Format arguments for better readability
            if len(args_str) > 1000:
                args_str = args_str[:997] + "..."
            
            perm_embed.add_field(name="Arguments", value=f"```json\n{args_str}\n```", inline=False)
            
            view = PermissionView(user_id=message.author.id)
            prompt = await message.channel.send(embed=perm_embed, view=view)
            
            self._intense_log("PERMISSION_REQUEST", {"name": name})
            await update_status(f"⚠️ Awaiting permission for `{name}`...")
            
            # Wait for user interaction
            await view.wait()
            
            if view.value is True:
                self._intense_log("PERMISSION_RESULT", {"name": name, "granted": True})
                await prompt.edit(content="✅ Permission granted.", view=None)
                await update_status(f"🔧 Executing: `{name}`")
                return True
            else:
                self._intense_log("PERMISSION_RESULT", {"name": name, "granted": False})
                await prompt.edit(content="❌ Permission denied.", view=None)
                await update_status("🔍 Thinking...")
                return False

        try:
            final_msg = await self.agent.run(
                message.content, 
                output_callback, 
                tool_callback, 
                tool_result_callback,
                permission_callback
            )
            
            # Update token counts
            total_prompt_tokens = final_msg.get('prompt_tokens', 0)
            total_eval_tokens = final_msg.get('eval_tokens', 0)
            
            # Send any remaining buffer
            if output_buffer:
                text_to_send = "".join(output_buffer)
                if text_to_send.strip():
                    await self.send_split(message.channel, text_to_send)
            
            self._intense_log("RESPONSE_COMPLETE", {
                "prompt_tokens": total_prompt_tokens, 
                "eval_tokens": total_eval_tokens
            })
            await update_status("✅ Done", finalized=True)
        
        except Exception as e:
            self._intense_log("ERROR", {"error": str(e)})
            self._log_error(e)
            embed.color = discord.Color.red()
            embed.description = f"❌ Error: {e}"
            await status_message.edit(embed=embed)
            await message.channel.send(f"❌ Error: {e}")
        finally:
            self.is_processing = False

def init_discord(backend="ollama", model=None):
    if not DISCORD_TOKEN or not DISCORD_USER_ID:
        print("[Discord] Warning: Missing DISCORD_TOKEN or DISCORD_USER_ID in .env. Skipping discord bridge.")
        return

    def run_bot():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
        
        bridge = DiscordAgentBridge(backend=backend, model=model)

        @bot.event
        async def on_ready():
            print(f"[Discord] Online as {bot.user}")
            await bot.change_presence(activity=discord.Game(name="Direct Access Mode 🛠"))

        @bot.event
        async def on_message(message):
            if message.author.bot:
                return

            if str(message.author.id) != str(DISCORD_USER_ID):
                # Ignore messages from others
                return
            
            # Process all messages from the user as AI queries
            await bridge.handle_message(message)

        bot.run(DISCORD_TOKEN, log_handler=None)

    t = threading.Thread(target=run_bot, daemon=True, name="DiscordBridge")
    t.start()
