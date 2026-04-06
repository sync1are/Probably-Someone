"""
ARIA Messaging System Launcher
Starts Discord bot, WhatsApp bridge, and HTTP server
"""

import os
import sys
import subprocess
import time
import threading
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header():
    """Print startup header."""
    print("=" * 70)
    print("ARIA MESSAGING SYSTEM")
    print("Auto-reply for WhatsApp and Discord")
    print("=" * 70)
    print()


def check_environment():
    """Check if required environment variables are set."""
    print("[Setup] Checking environment variables...")

    warnings = []

    discord_token = os.getenv('DISCORD_USER_TOKEN')
    if not discord_token:
        warnings.append("DISCORD_USER_TOKEN not set - Discord bot will not work")

    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    print("[Setup] ✓ Environment check complete\n")


def start_http_server():
    """Start the Flask HTTP server for WhatsApp bridge."""
    print("[HTTP Server] Starting...")

    from src.messaging.http_server import run_server

    try:
        run_server(host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"[HTTP Server] ERROR: {e}")


def start_discord_bot():
    """Start the Discord bot."""
    print("[Discord] Starting bot...")

    try:
        import discord_bot
        discord_bot.main()
    except ImportError as e:
        print(f"[Discord] ERROR: Missing dependency - {e}")
        print("[Discord] Run: pip install discord.py-self")
    except Exception as e:
        print(f"[Discord] ERROR: {e}")


def start_whatsapp_bridge():
    """Start the WhatsApp Node.js bridge."""
    print("[WhatsApp] Starting bridge...")
    print("[WhatsApp] Make sure Node.js is installed (v18+)")

    bridge_dir = os.path.join(os.path.dirname(__file__), 'whatsapp_bridge')

    # Check if node_modules exists
    if not os.path.exists(os.path.join(bridge_dir, 'node_modules')):
        print("[WhatsApp] Installing dependencies (this may take a while)...")
        try:
            subprocess.run(['npm', 'install'], cwd=bridge_dir, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[WhatsApp] ERROR: Failed to install dependencies - {e}")
            return
        except FileNotFoundError:
            print("[WhatsApp] ERROR: Node.js/npm not found. Install Node.js first.")
            return

    # Start the bridge
    try:
        subprocess.run(['node', 'bridge.js'], cwd=bridge_dir)
    except FileNotFoundError:
        print("[WhatsApp] ERROR: Node.js not found. Install Node.js first.")
    except Exception as e:
        print(f"[WhatsApp] ERROR: {e}")


def show_menu():
    """Show startup menu."""
    print("\n" + "=" * 70)
    print("Select components to start:")
    print("=" * 70)
    print("1. Discord bot only")
    print("2. WhatsApp bridge only (requires HTTP server)")
    print("3. Both Discord and WhatsApp (full system)")
    print("4. HTTP server only (for WhatsApp bridge)")
    print("5. Exit")
    print("=" * 70)

    choice = input("\nEnter choice (1-5): ").strip()
    return choice


def main():
    """Main entry point."""
    print_header()
    check_environment()

    choice = show_menu()

    if choice == '1':
        # Discord only
        print("\n[Launcher] Starting Discord bot...\n")
        start_discord_bot()

    elif choice == '2':
        # WhatsApp only (needs HTTP server)
        print("\n[Launcher] Starting HTTP server and WhatsApp bridge...\n")

        # Start HTTP server in separate thread
        server_thread = threading.Thread(target=start_http_server, daemon=True)
        server_thread.start()

        time.sleep(2)  # Give server time to start

        # Start WhatsApp bridge (blocking)
        start_whatsapp_bridge()

    elif choice == '3':
        # Full system
        print("\n[Launcher] Starting full messaging system...\n")
        print("⚠️  Note: This will start multiple processes")
        print("⚠️  Discord bot and HTTP server run in background")
        print("⚠️  WhatsApp bridge runs in foreground\n")

        time.sleep(2)

        # Start HTTP server in thread
        server_thread = threading.Thread(target=start_http_server, daemon=True)
        server_thread.start()

        # Start Discord bot in thread
        discord_thread = threading.Thread(target=start_discord_bot, daemon=True)
        discord_thread.start()

        time.sleep(3)  # Give services time to start

        # Start WhatsApp bridge (blocking)
        start_whatsapp_bridge()

    elif choice == '4':
        # HTTP server only
        print("\n[Launcher] Starting HTTP server...\n")
        start_http_server()

    elif choice == '5':
        print("\n[Launcher] Exiting...")
        return

    else:
        print("\n[Launcher] Invalid choice. Exiting...")
        return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Launcher] Shutting down...")
        sys.exit(0)
