"""
Messaging integration tools for ARIA main app
Voice-guided setup and management for WhatsApp/Discord
"""

import os
import subprocess
import time
import threading
import requests
from pathlib import Path


# Global state for running processes
_messaging_processes = {
    "whatsapp_bridge": None,
    "discord_bot": None,
    "http_server": None
}


def setup_whatsapp():
    """
    Setup WhatsApp auto-reply integration.
    Starts the bridge and displays QR code for authentication.

    Returns:
        dict: Success status and instructions
    """
    try:
        # Check if Node.js is installed
        try:
            subprocess.run(['node', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {
                "success": False,
                "error": "Node.js not found",
                "message": "Node.js is required for WhatsApp. Please install Node.js version 18 or higher from nodejs.org, then try again."
            }

        # Check if dependencies are installed
        bridge_dir = Path(__file__).parent.parent.parent / "messaging" / "whatsapp_bridge"
        node_modules = bridge_dir / "node_modules"

        if not node_modules.exists():
            return {
                "success": False,
                "message": "WhatsApp dependencies need to be installed first. Please run: cd messaging/whatsapp_bridge && npm install",
                "action": "install_deps",
                "instructions": f"Run: cd {bridge_dir} && npm install"
            }

        # Start HTTP server first (required for WhatsApp bridge)
        if not _messaging_processes["http_server"]:
            _start_http_server()
            time.sleep(2)  # Give server time to start

        # Start WhatsApp bridge (this will show QR code in a new window)
        print("\n" + "="*60)
        print("STARTING WHATSAPP SETUP")
        print("="*60)
        print("Opening a new terminal window with the QR code...")
        print("1. A new command window will open")
        print("2. The QR code will appear in that window")
        print("3. Open WhatsApp on your phone")
        print("4. Go to Settings → Linked Devices")
        print("5. Tap 'Link a Device'")
        print("6. Scan the QR code from the new window")
        print("="*60 + "\n")

        success = _start_whatsapp_bridge()

        if success:
            return {
                "success": True,
                "message": "WhatsApp bridge started in a new terminal window. Look for the popup window with the QR code!",
                "action": "qr_showing",
                "instructions": "A new command window should have opened. The QR code will appear there. Scan it with WhatsApp on your phone."
            }
        else:
            return {
                "success": False,
                "message": "Failed to start WhatsApp bridge. Check the terminal for errors.",
                "error": "Bridge startup failed"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to setup WhatsApp: {str(e)}"
        }


def setup_discord():
    """
    Setup Discord auto-reply integration.
    Guides user through getting Discord token.

    Returns:
        dict: Success status and instructions
    """
    try:
        # Check if token is already set
        discord_token = os.getenv('DISCORD_USER_TOKEN', '')

        if not discord_token:
            instructions = """
To setup Discord auto-reply, I need your Discord user token. Here's how to get it:

1. Open Discord in your web browser (not the app)
2. Press F12 to open Developer Tools
3. Go to the Network tab
4. Refresh the page (Ctrl+R)
5. Look for any request to 'discord.com/api'
6. Click on it, then go to Request Headers
7. Find 'authorization' and copy the value
8. Add it to your .env file as: DISCORD_USER_TOKEN=your_token_here

WARNING: Using user tokens violates Discord's Terms of Service and may result in account ban.

After adding the token, say 'start Discord messaging' to activate.
"""
            return {
                "success": False,
                "message": "Discord token not configured.",
                "instructions": instructions,
                "action": "get_token"
            }

        return {
            "success": True,
            "message": "Discord token found. Say 'start Discord messaging' to activate auto-reply.",
            "instructions": "Make sure to add contacts to the whitelist first."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to setup Discord."
        }


def start_messaging(platform="both"):
    """
    Start the messaging system.

    Args:
        platform (str): "whatsapp", "discord", or "both"

    Returns:
        dict: Success status and message
    """
    try:
        started = []

        # Start HTTP server if not running (needed for WhatsApp)
        if platform in ["whatsapp", "both"]:
            if not _messaging_processes["http_server"]:
                _start_http_server()
                time.sleep(2)
            started.append("HTTP server")

        # Start WhatsApp bridge
        if platform in ["whatsapp", "both"]:
            if not _messaging_processes["whatsapp_bridge"]:
                success = _start_whatsapp_bridge()
                if success:
                    started.append("WhatsApp")
                else:
                    return {
                        "success": False,
                        "message": "Failed to start WhatsApp. Run 'setup WhatsApp' first."
                    }

        # Start Discord bot
        if platform in ["discord", "both"]:
            if not _messaging_processes["discord_bot"]:
                success = _start_discord_bot()
                if success:
                    started.append("Discord")
                else:
                    return {
                        "success": False,
                        "message": "Failed to start Discord. Have you added DISCORD_USER_TOKEN to your .env file?"
                    }

        if started:
            return {
                "success": True,
                "message": f"Messaging started for: {', '.join(started)}. Auto-reply is now active for whitelisted contacts.",
                "started": started
            }
        else:
            return {
                "success": False,
                "message": "Messaging services already running or failed to start."
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to start messaging."
        }


def stop_messaging():
    """
    Stop the messaging system.

    Returns:
        dict: Success status and message
    """
    try:
        stopped = []

        # Stop WhatsApp bridge
        if _messaging_processes["whatsapp_bridge"]:
            _messaging_processes["whatsapp_bridge"].terminate()
            _messaging_processes["whatsapp_bridge"] = None
            stopped.append("WhatsApp")

        # Stop Discord bot
        if _messaging_processes["discord_bot"]:
            _messaging_processes["discord_bot"].terminate()
            _messaging_processes["discord_bot"] = None
            stopped.append("Discord")

        # Stop HTTP server
        if _messaging_processes["http_server"]:
            # HTTP server is in a thread, we'll just set it to None
            # The thread will be daemon and die when app exits
            _messaging_processes["http_server"] = None
            stopped.append("HTTP server")

        if stopped:
            return {
                "success": True,
                "message": f"Stopped: {', '.join(stopped)}. Auto-reply is now inactive.",
                "stopped": stopped
            }
        else:
            return {
                "success": True,
                "message": "No messaging services were running."
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to stop messaging."
        }


def messaging_status():
    """
    Get messaging system status and statistics.

    Returns:
        dict: Status information
    """
    try:
        # Check which services are running
        running = []
        if _messaging_processes["whatsapp_bridge"]:
            running.append("WhatsApp")
        if _messaging_processes["discord_bot"]:
            running.append("Discord")
        if _messaging_processes["http_server"]:
            running.append("HTTP server")

        # Try to get stats from HTTP server
        stats = {}
        try:
            response = requests.get('http://localhost:5000/stats', timeout=2)
            if response.status_code == 200:
                stats = response.json()
        except:
            pass

        return {
            "success": True,
            "running": running,
            "active": len(running) > 0,
            "stats": stats,
            "message": f"Messaging is {'active' if running else 'inactive'}. Running: {', '.join(running) if running else 'None'}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get messaging status."
        }


def add_messaging_contact(platform, contact):
    """
    Add a contact to the messaging whitelist.

    Args:
        platform (str): "whatsapp" or "discord"
        contact (str): Phone number or Discord user ID

    Returns:
        dict: Success status and message
    """
    try:
        # Try to add via HTTP API
        if platform == "whatsapp":
            endpoint = "http://localhost:5000/whitelist/whatsapp/add"
            data = {"contact": contact}
        elif platform == "discord":
            endpoint = "http://localhost:5000/whitelist/discord/add_user"
            data = {"user_id": contact}
        else:
            return {
                "success": False,
                "error": "Invalid platform",
                "message": "Platform must be 'whatsapp' or 'discord'"
            }

        # If HTTP server is running, use API
        if _messaging_processes["http_server"]:
            try:
                response = requests.post(endpoint, json=data, timeout=2)
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Added {contact} to {platform} whitelist. They will now receive auto-replies.",
                        "contact": contact,
                        "platform": platform
                    }
            except:
                pass

        # Otherwise, add directly to JSON file
        import json
        whitelist_file = Path(__file__).parent.parent.parent / "messaging" / "messaging_whitelist.json"

        with open(whitelist_file, 'r') as f:
            whitelist = json.load(f)

        if platform == "whatsapp":
            if contact not in whitelist["whatsapp"]["contacts"]:
                whitelist["whatsapp"]["contacts"].append(contact)
        else:  # discord
            if contact not in whitelist["discord"]["users"]:
                whitelist["discord"]["users"].append(contact)

        with open(whitelist_file, 'w') as f:
            json.dump(whitelist, f, indent=2)

        return {
            "success": True,
            "message": f"Added {contact} to {platform} whitelist.",
            "contact": contact,
            "platform": platform
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to add contact."
        }

def get_last_message(platform, contact=None):
    """
    Get the last message received from a contact or from any contact.

    Args:
        platform (str): "whatsapp" or "discord"
        contact (str, optional): Specific contact name/number, or None for last from anyone

    Returns:
        dict: Success status with message details
    """
    import json as _json
    import os as _os
    import time as _time

    def _history_lookup(platform_key, contact_filter=None):
        """Read last message from the shared messaging_history.json file."""
        history_file = Path(__file__).parent.parent.parent / "messaging" / "messaging_history.json"
        if not history_file.exists():
            return None
        try:
            data = _json.loads(history_file.read_text(encoding="utf-8"))
            contacts = data.get(platform_key, {})
            if not contacts:
                return None

            if contact_filter:
                cf = contact_filter.lower()
                # Match by name or ID substring
                matched = {
                    cid: info for cid, info in contacts.items()
                    if cf in info.get("name", "").lower() or cf in cid.lower()
                }
                if not matched:
                    return None
                contacts = matched

            # Return the most recently interacted contact
            latest_id = max(contacts, key=lambda cid: contacts[cid].get("last_interaction", 0))
            info = contacts[latest_id]
            ts = info.get("last_interaction", 0)
            time_str = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ts)) if ts else "unknown time"
            return {
                "success": True,
                "contact": info.get("name", latest_id),
                "body": info.get("last_message", ""),
                "reply_sent": info.get("last_reply", ""),
                "timestamp": time_str,
                "message": f"Last message from {info.get('name', latest_id)} at {time_str}: \"{info.get('last_message', '')}\""
            }
        except Exception:
            return None

    try:
        if platform == "whatsapp":
            # Try live bridge first (has real-time messages)
            try:
                health_check = requests.get('http://localhost:3000/health', timeout=2)
                if health_check.status_code == 200:
                    params = {}
                    if contact:
                        params['contact'] = contact
                    response = requests.get(
                        'http://localhost:3000/last_message',
                        params=params,
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            msg_data = data.get('message', {})
                            from_name = msg_data.get('fromName', 'Unknown')
                            body = msg_data.get('body', '')
                            date = msg_data.get('date', '')
                            return {
                                "success": True,
                                "message": f"Last message from {from_name}: \"{body}\"",
                                "contact": from_name,
                                "body": body,
                                "timestamp": date
                            }
            except Exception:
                pass

            # Fall back to history file
            result = _history_lookup("whatsapp", contact)
            if result:
                return result
            return {
                "success": False,
                "message": "No WhatsApp messages found yet. The bridge may not have received any messages since it started."
            }

        elif platform == "discord":
            # Discord uses the shared history file written by discord_bot.py
            result = _history_lookup("discord", contact)
            if result:
                return result
            return {
                "success": False,
                "message": "No Discord messages found yet. Either no one has messaged, or the bot hasn't started."
            }

        else:
            return {
                "success": False,
                "message": "Invalid platform. Use 'whatsapp' or 'discord'."
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get message: {str(e)}"
        }


def send_message(platform, contact, message):
    """
    Send a message to a contact on WhatsApp or Discord.

    Args:
        platform (str): "whatsapp" or "discord"
        contact (str): Contact name/number or Discord user ID
        message (str): Message to send

    Returns:
        dict: Success status and message
    """
    try:
        if platform == "whatsapp":
            # Check if WhatsApp bridge is responding (might be running but not tracked)
            bridge_running = False
            try:
                health_check = requests.get('http://localhost:3000/health', timeout=3)
                if health_check.status_code == 200:
                    bridge_running = True
                    health_data = health_check.json()
                    print(f"[Messaging] WhatsApp bridge status: {health_data}")
            except Exception as e:
                print(f"[Messaging] Health check failed: {e}")

            # Auto-start WhatsApp bridge if not running
            if not bridge_running and not _messaging_processes["whatsapp_bridge"]:
                print("[Messaging] WhatsApp not running, starting automatically...")

                # Start HTTP server first
                if not _messaging_processes["http_server"]:
                    try:
                        requests.get('http://localhost:5000/health', timeout=1)
                        print("[Messaging] HTTP server already running")
                    except:
                        _start_http_server()
                        time.sleep(2)

                # Start WhatsApp bridge
                _start_whatsapp_bridge()

                # Give it more time to connect
                print("[Messaging] Waiting for WhatsApp to connect (15s)...")
                time.sleep(15)

                # Check if it's ready now
                try:
                    health_check = requests.get('http://localhost:3000/health', timeout=3)
                    if health_check.status_code == 200:
                        bridge_running = True
                        print("[Messaging] WhatsApp bridge is now ready")
                except:
                    return {
                        "success": False,
                        "message": "WhatsApp bridge started but not responding. Check the terminal window that opened. You might need to scan the QR code if this is the first time."
                    }

            if not bridge_running:
                return {
                    "success": False,
                    "message": "WhatsApp bridge is not responding. Make sure it's running and connected."
                }

            try:
                # Call WhatsApp bridge's send endpoint
                print(f"[Messaging] Sending message to {contact}: {message}")
                response = requests.post(
                    'http://localhost:3000/send',
                    json={"contact": contact, "message": message},
                    timeout=10
                )

                print(f"[Messaging] Response status: {response.status_code}")
                print(f"[Messaging] Response body: {response.text}")

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        return {
                            "success": True,
                            "message": f"Sent to {contact} on WhatsApp: '{message}'",
                            "platform": platform,
                            "contact": contact
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Failed: {data.get('error', 'Unknown error')}"
                        }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "message": f"Contact '{contact}' not found in WhatsApp. Make sure you have an active chat with them. Open WhatsApp and send them a message first, then try again."
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to send: HTTP {response.status_code} - {response.text[:200]}"
                    }

            except requests.exceptions.ConnectionError:
                return {
                    "success": False,
                    "message": "WhatsApp bridge isn't responding. Check if the terminal window is still open."
                }
            except requests.exceptions.Timeout:
                return {
                    "success": False,
                    "message": "Request timed out. WhatsApp might be busy."
                }
            except requests.exceptions.RequestException as e:
                return {
                    "success": False,
                    "message": f"Connection error: {str(e)}"
                }

        elif platform == "discord":
            return {
                "success": False,
                "message": "Sending Discord messages not yet implemented. Currently only auto-reply is supported."
            }

        else:
            return {
                "success": False,
                "message": "Invalid platform. Use 'whatsapp' or 'discord'."
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send message: {str(e)}"
        }


def manage_whitelist(action, platform=None, contact=None):
    """
    Manage messaging whitelist with natural language.

    Args:
        action (str): "add", "remove", "list", or "clear"
        platform (str): "whatsapp" or "discord" (optional for "list")
        contact (str): Contact to add/remove (phone/ID/name)

    Returns:
        dict: Success status and message
    """
    try:
        import json
        whitelist_file = Path(__file__).parent.parent.parent / "messaging" / "messaging_whitelist.json"

        # Initialize default if it doesn't exist
        if not whitelist_file.exists():
            default = {
                "discord": {"users": [], "channels": []},
                "whatsapp": {"contacts": []}
            }
            with open(whitelist_file, 'w') as f:
                json.dump(default, f, indent=2)

        # Load current whitelist
        with open(whitelist_file, 'r') as f:
            whitelist = json.load(f)

        if action == "list":
            # List all contacts
            wa_contacts = whitelist["whatsapp"]["contacts"]
            discord_users = whitelist["discord"]["users"]
            discord_channels = whitelist["discord"]["channels"]

            message = "Current whitelist:\n\n"

            if wa_contacts:
                message += f"WhatsApp ({len(wa_contacts)}):\n"
                for contact in wa_contacts:
                    message += f"  - {contact}\n"
            else:
                message += "WhatsApp: None\n"

            if discord_users:
                message += f"\nDiscord Users ({len(discord_users)}):\n"
                for user in discord_users:
                    message += f"  - {user}\n"
            else:
                message += "\nDiscord Users: None\n"

            if discord_channels:
                message += f"\nDiscord Channels ({len(discord_channels)}):\n"
                for channel in discord_channels:
                    message += f"  - {channel}\n"

            return {
                "success": True,
                "message": message.strip(),
                "whitelist": whitelist
            }

        elif action == "add":
            if not platform or not contact:
                return {
                    "success": False,
                    "message": "Need both platform and contact to add. Example: 'Add John to WhatsApp'"
                }

            return add_messaging_contact(platform, contact)

        elif action == "remove":
            if not platform or not contact:
                return {
                    "success": False,
                    "message": "Need both platform and contact to remove."
                }

            # Remove contact
            removed = False

            # Using updated path
            whitelist_file = Path(__file__).parent.parent.parent / "messaging" / "messaging_whitelist.json"

            if platform == "whatsapp":
                if contact in whitelist["whatsapp"]["contacts"]:
                    whitelist["whatsapp"]["contacts"].remove(contact)
                    removed = True
            elif platform == "discord":
                if contact in whitelist["discord"]["users"]:
                    whitelist["discord"]["users"].remove(contact)
                    removed = True

            if removed:
                with open(whitelist_file, 'w') as f:
                    json.dump(whitelist, f, indent=2)

                # Also update via API if server running
                if _messaging_processes["http_server"]:
                    # (No remove endpoint in current API, file update is enough)
                    pass

                return {
                    "success": True,
                    "message": f"Removed {contact} from {platform} whitelist.",
                    "contact": contact,
                    "platform": platform
                }
            else:
                return {
                    "success": False,
                    "message": f"{contact} not found in {platform} whitelist."
                }

        elif action == "clear":
            if not platform:
                return {
                    "success": False,
                    "message": "Specify platform to clear (whatsapp or discord)."
                }

            if platform == "whatsapp":
                count = len(whitelist["whatsapp"]["contacts"])
                whitelist["whatsapp"]["contacts"] = []
            elif platform == "discord":
                count = len(whitelist["discord"]["users"]) + len(whitelist["discord"]["channels"])
                whitelist["discord"]["users"] = []
                whitelist["discord"]["channels"] = []
            else:
                return {
                    "success": False,
                    "message": "Invalid platform. Use 'whatsapp' or 'discord'."
                }

            with open(whitelist_file, 'w') as f:
                json.dump(whitelist, f, indent=2)

            return {
                "success": True,
                "message": f"Cleared {count} contacts from {platform} whitelist.",
                "platform": platform,
                "count": count
            }

        else:
            return {
                "success": False,
                "message": "Invalid action. Use: add, remove, list, or clear."
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to manage whitelist."
        }


# Helper functions to start services

def _start_http_server():
    """Start HTTP server in background thread."""
    def run_server():
        from src.messaging.http_server import run_server
        run_server(host='0.0.0.0', port=5000)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    _messaging_processes["http_server"] = thread
    return True


def _start_whatsapp_bridge():
    """Start WhatsApp bridge process in a new terminal window."""
    try:
        # Check if the bridge is already running on port 3000 by attempting to reach the health endpoint
        try:
            res = requests.get("http://127.0.0.1:3000/health", timeout=1)
            if res.status_code == 200:
                print("WhatsApp bridge is already running in the background. Skipping startup.")
                _messaging_processes["whatsapp_bridge"] = "Already running"
                return True
        except requests.exceptions.RequestException:
            pass  # Not running, proceed with startup

        bridge_dir = Path(__file__).parent.parent.parent / "messaging" / "whatsapp_bridge"

        # Start in a new terminal window so QR code displays properly
        if os.name == 'nt':  # Windows
            process = subprocess.Popen(
                ['cmd', '/c', 'start', 'cmd', '/k', 'node', 'bridge.js'],
                cwd=str(bridge_dir),
                shell=True
            )
        else:  # Linux/Mac
            process = subprocess.Popen(
                ['gnome-terminal', '--', 'node', 'bridge.js'],
                cwd=str(bridge_dir)
            )

        _messaging_processes["whatsapp_bridge"] = process
        return True
    except Exception as e:
        print(f"Error starting WhatsApp bridge: {e}")
        return False


def _start_discord_bot():
    """Start Discord bot process."""
    try:
        import sys
        bot_file = Path(__file__).parent.parent.parent / "discord_bot.py"
        # Run using the same python executable that the main app is using
        process = subprocess.Popen(
            [sys.executable, str(bot_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        _messaging_processes["discord_bot"] = process

        # Start a thread to print output
        def print_output():
            for line in process.stdout:
                print(line, end='')

        threading.Thread(target=print_output, daemon=True).start()

        return True
    except Exception as e:
        print(f"Error starting Discord bot: {e}")
        return False

def set_autonomous_mode(enabled: bool, checkin_threshold_hours: int = 24):
    """
    Enable or disable ARIA's autonomous messaging mode for proactive check-ins.

    Args:
        enabled (bool): Whether to enable autonomous mode
        checkin_threshold_hours (int): Hours of silence before ARIA checks in

    Returns:
        dict: Success status and message
    """
    import sys
    try:
        import __main__ as app

        # Access the global autonomy_engine directly from app
        if hasattr(app, 'autonomy_engine') and app.autonomy_engine:
            if enabled:
                app.autonomy_engine.checkin_threshold_hours = checkin_threshold_hours
                app.autonomy_engine.start()

                # Auto-start messaging if it isn't running
                start_msg = start_messaging(platform="both")

                return {
                    "success": True,
                    "message": f"Autonomous mode ENABLED. Will check in after {checkin_threshold_hours} hours of silence. Messaging systems started: {start_msg['message']}"
                }
            else:
                app.autonomy_engine.stop()
                return {
                    "success": True,
                    "message": "Autonomous mode DISABLED."
                }
        else:
            return {
                "success": False,
                "message": "autonomy_engine is not yet initialized in the main app."
            }
    except ImportError:
        # Fallback if we can't import app directly
        return {
            "success": False,
            "message": "Could not access the main app module. It may not be initialized yet."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to change autonomous mode: {str(e)}"
        }

def send_proactive_message(platform: str, contact_id: str, context: str):
    """
    Proactively message a whitelisted contact with a specific goal.

    Args:
        platform (str): "whatsapp" or "discord"
        contact_id (str): The ID of the contact to message
        context (str): The reason or goal for the message

    Returns:
        dict: Success status and message
    """
    try:
        import __main__ as app
        import asyncio

        if not hasattr(app, 'messaging_controller') or not app.messaging_controller:
            return {
                "success": False,
                "message": "messaging_controller is not yet initialized in the main app."
            }

        # Need to run the async function in a new event loop or the current one
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                app.messaging_controller.initiate_conversation(
                    platform=platform,
                    contact_id=contact_id,
                    contact_name=contact_id, # Fallback name
                    context=context
                )
            )
            # We don't wait for it, just let it run
        except RuntimeError:
            # No running event loop
            asyncio.run(
                app.messaging_controller.initiate_conversation(
                    platform=platform,
                    contact_id=contact_id,
                    contact_name=contact_id, # Fallback name
                    context=context
                )
            )

        return {
            "success": True,
            "message": f"Successfully initiated proactive message to {contact_id} on {platform}."
        }
    except ImportError:
        return {
            "success": False,
            "message": "Could not access the main app module."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send proactive message: {str(e)}"
        }

def set_current_status(status: str):
    """
    Update the user's current status so the AI can inform contacts.
    Persists to a shared file so the discord/whatsapp bot subprocess
    picks it up immediately without needing a restart.

    Args:
        status (str): The status description (e.g. "Aze is on a coffee break")

    Returns:
        dict: Success status and message
    """
    try:
        from src.messaging.config import set_current_status_file
        set_current_status_file(status)

        return {
            "success": True,
            "message": f"Status updated to: '{status}'. The messaging bot will mention this to anyone who asks.",
            "data": {"status": status}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update status: {str(e)}"
        }