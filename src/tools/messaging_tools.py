"""
Messaging integration tools for ARIA main app
Voice-guided setup and management for WhatsApp/Discord
"""

import os
import subprocess
import time
import threading
import requests
import difflib
import uuid
from pathlib import Path
from typing import Dict, List, Optional


import json

# Global state for running processes
_messaging_processes = {
    "whatsapp_bridge": None,
    "discord_bot": None,
    "instagram_bot": None,
    "http_server": None
}

PENDING_MESSAGES_FILE = Path(__file__).parent.parent.parent / "messaging" / "pending_user_messages.json"
CONTACT_ALIASES_FILE = Path(__file__).parent.parent.parent / "messaging" / "contact_aliases.json"
PENDING_SEND_CONFIRMATIONS_FILE = Path(__file__).parent.parent.parent / "messaging" / "pending_send_confirmations.json"


def _init_json_file(path: Path, default_data: Dict):
    """Create a JSON file with default data if missing."""
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, 'w') as f:
            json.dump(default_data, f, indent=2)


def _load_json_file(path: Path, default_data: Dict) -> Dict:
    """Load JSON from disk with fallback defaults."""
    _init_json_file(path, default_data)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        with open(path, 'w') as f:
            json.dump(default_data, f, indent=2)
        return default_data


def _save_json_file(path: Path, data: Dict):
    """Persist JSON data to disk."""
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def _normalize_contact_key(value: str) -> str:
    """Normalize contact strings for matching and alias lookups."""
    return "".join(ch for ch in value.lower().strip() if ch.isalnum())


def _load_alias_store() -> Dict:
    return _load_json_file(
        CONTACT_ALIASES_FILE,
        {"whatsapp": {}, "discord": {}, "instagram": {}}
    )


def _save_alias_mapping(platform: str, spoken_alias: str, target_id: str, target_display: str):
    alias_store = _load_alias_store()
    platform_store = alias_store.setdefault(platform, {})
    platform_store[_normalize_contact_key(spoken_alias)] = {
        "alias": spoken_alias,
        "target_id": target_id,
        "target_display": target_display
    }
    _save_json_file(CONTACT_ALIASES_FILE, alias_store)


def _get_alias_mapping(platform: str, spoken_alias: str) -> Optional[Dict]:
    alias_store = _load_alias_store()
    return alias_store.get(platform, {}).get(_normalize_contact_key(spoken_alias))


def _load_pending_confirmations() -> Dict:
    return _load_json_file(PENDING_SEND_CONFIRMATIONS_FILE, {"pending": {}})


def _create_pending_confirmation(platform: str, contact: str, message: str, target_id: str, target_display: str) -> Dict:
    data = _load_pending_confirmations()
    confirmation_id = uuid.uuid4().hex
    data.setdefault("pending", {})[confirmation_id] = {
        "platform": platform,
        "contact": contact,
        "message": message,
        "target_id": target_id,
        "target_display": target_display,
        "created_at": int(time.time())
    }
    _save_json_file(PENDING_SEND_CONFIRMATIONS_FILE, data)
    return {"confirmation_id": confirmation_id, **data["pending"][confirmation_id]}


def _pop_pending_confirmation(confirmation_id: str) -> Optional[Dict]:
    data = _load_pending_confirmations()
    pending = data.get("pending", {})
    item = pending.pop(confirmation_id, None)
    _save_json_file(PENDING_SEND_CONFIRMATIONS_FILE, data)
    return item


def _score_candidate(query: str, candidate: Dict) -> float:
    """Compute similarity score between spoken contact and candidate identity."""
    q = _normalize_contact_key(query)
    if not q:
        return 0.0
    names = [
        candidate.get("display", ""),
        candidate.get("username", ""),
        candidate.get("name", ""),
        candidate.get("id", "")
    ]
    best = 0.0
    for value in names:
        n = _normalize_contact_key(str(value))
        if not n:
            continue
        if n == q:
            return 1.0
        if q in n:
            best = max(best, 0.95)
        else:
            best = max(best, difflib.SequenceMatcher(None, q, n).ratio())
    return best


def _best_candidate(query: str, candidates: List[Dict]) -> Optional[Dict]:
    if not candidates:
        return None
    ranked = sorted(
        (
            {
                **candidate,
                "score": _score_candidate(query, candidate)
            }
            for candidate in candidates
        ),
        key=lambda item: item["score"],
        reverse=True
    )
    best = ranked[0]
    if best["score"] < 0.55:
        return None
    return best


def _fetch_whatsapp_candidates() -> List[Dict]:
    try:
        response = requests.get("http://localhost:3000/contacts", timeout=8)
        if response.status_code != 200:
            return []
        payload = response.json()
        contacts = payload.get("contacts", [])
        candidates = []
        for contact in contacts:
            target_id = contact.get("id", "")
            display = contact.get("display") or contact.get("name") or contact.get("number") or target_id
            if not target_id:
                continue
            candidates.append({
                "id": target_id,
                "display": display,
                "name": contact.get("name", ""),
                "username": contact.get("pushname", "")
            })
        return candidates
    except Exception:
        return []


def _fetch_discord_candidates() -> List[Dict]:
    token = os.getenv("DISCORD_USER_TOKEN", "").strip()
    if not token:
        return []

    headers = {
        "authorization": token,
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0"
    }
    try:
        response = requests.get("https://discord.com/api/v9/users/@me/channels", headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        channels = response.json()
        candidates = []
        for channel in channels:
            if channel.get("type") != 1:
                continue
            recipients = channel.get("recipients", [])
            if not recipients:
                continue
            user = recipients[0]
            user_id = str(user.get("id", ""))
            username = user.get("username", "")
            display = user.get("global_name") or username or user_id
            if not user_id:
                continue
            candidates.append({
                "id": user_id,
                "display": display,
                "name": display,
                "username": username
            })
        return candidates
    except Exception:
        return []


def _fetch_instagram_candidates() -> List[Dict]:
    username = os.getenv("INSTAGRAM_USERNAME", "").strip()
    password = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    if not username or not password:
        return []
    try:
        from instagrapi import Client
        client = Client()
        session_file = Path(__file__).parent.parent.parent / "instagram_session.json"
        if session_file.exists():
            client.load_settings(session_file)
        client.login(username, password)
        if session_file.exists() is False:
            client.dump_settings(session_file)
        threads = client.direct_threads(amount=20)
        seen = set()
        candidates = []
        for thread in threads:
            for user in thread.users:
                user_id = str(getattr(user, "pk", ""))
                handle = getattr(user, "username", "")
                if not user_id or user_id in seen:
                    continue
                seen.add(user_id)
                candidates.append({
                    "id": user_id,
                    "display": handle or user_id,
                    "name": handle or user_id,
                    "username": handle or ""
                })
        return candidates
    except Exception:
        return []


def _resolve_contact_candidate(platform: str, contact: str) -> Optional[Dict]:
    fetchers = {
        "whatsapp": _fetch_whatsapp_candidates,
        "discord": _fetch_discord_candidates,
        "instagram": _fetch_instagram_candidates
    }
    fetcher = fetchers.get(platform)
    if not fetcher:
        return None
    candidates = fetcher()
    return _best_candidate(contact, candidates)


def _send_whatsapp_message(target_id: str, message: str) -> Dict:
    response = requests.post(
        'http://localhost:3000/send',
        json={"contact": target_id, "message": message},
        timeout=10
    )
    if response.status_code == 200 and response.json().get("success"):
        return {"success": True}
    if response.status_code == 404:
        return {"success": False, "message": "Contact not found in WhatsApp bridge contacts."}
    return {"success": False, "message": f"WhatsApp send failed: HTTP {response.status_code}"}


def _send_discord_message(target_user_id: str, message: str) -> Dict:
    token = os.getenv("DISCORD_USER_TOKEN", "").strip()
    if not token:
        return {"success": False, "message": "DISCORD_USER_TOKEN is not configured."}

    headers = {
        "authorization": token,
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0"
    }
    channel_response = requests.post(
        "https://discord.com/api/v9/users/@me/channels",
        headers=headers,
        json={"recipient_id": target_user_id},
        timeout=10
    )
    if channel_response.status_code not in (200, 201):
        return {"success": False, "message": f"Failed to open Discord DM (HTTP {channel_response.status_code})."}
    channel_id = channel_response.json().get("id")
    if not channel_id:
        return {"success": False, "message": "Discord DM channel ID missing."}

    send_response = requests.post(
        f"https://discord.com/api/v9/channels/{channel_id}/messages",
        headers=headers,
        json={"content": message},
        timeout=10
    )
    if send_response.status_code not in (200, 201):
        return {"success": False, "message": f"Failed to send Discord DM (HTTP {send_response.status_code})."}
    return {"success": True}


def _send_instagram_message(target_user_id: str, message: str) -> Dict:
    username = os.getenv("INSTAGRAM_USERNAME", "").strip()
    password = os.getenv("INSTAGRAM_PASSWORD", "").strip()
    if not username or not password:
        return {"success": False, "message": "Instagram credentials are not configured."}
    try:
        from instagrapi import Client
        client = Client()
        session_file = Path(__file__).parent.parent.parent / "instagram_session.json"
        if session_file.exists():
            client.load_settings(session_file)
        client.login(username, password)
        if session_file.exists() is False:
            client.dump_settings(session_file)
        client.direct_send(message, user_ids=[int(target_user_id)])
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": f"Failed to send Instagram DM: {str(e)}"}


def _send_message_to_target(platform: str, target_id: str, target_display: str, message: str) -> Dict:
    if platform == "whatsapp":
        result = _send_whatsapp_message(target_id, message)
    elif platform == "discord":
        result = _send_discord_message(target_id, message)
    elif platform == "instagram":
        result = _send_instagram_message(target_id, message)
    else:
        return {"success": False, "message": "Invalid platform. Use 'whatsapp', 'discord', or 'instagram'."}

    if not result.get("success"):
        return result

    return {
        "success": True,
        "message": f"Sent to {target_display} on {platform}: '{message}'",
        "platform": platform,
        "contact_id": target_id,
        "contact": target_display
    }

def _init_pending_messages():
    """Initialize the pending messages file if it doesn't exist."""
    if not PENDING_MESSAGES_FILE.parent.exists():
        PENDING_MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not PENDING_MESSAGES_FILE.exists():
        with open(PENDING_MESSAGES_FILE, 'w') as f:
            json.dump({"pending_count": 0, "messages": []}, f, indent=2)

def store_user_message(contact_name: str, platform: str, message_content: str):
    """
    Store a message for the user.

    Args:
        contact_name (str): Name of the person leaving the message
        platform (str): Platform the message was received on
        message_content (str): The content of the message

    Returns:
        dict: Success status and confirmation
    """
    try:
        _init_pending_messages()
        with open(PENDING_MESSAGES_FILE, 'r') as f:
            data = json.load(f)

        new_message = {
            "platform": platform,
            "name": contact_name,
            "content": message_content,
            "timestamp": int(time.time())
        }

        data["messages"].append(new_message)
        data["pending_count"] = len(data["messages"])

        with open(PENDING_MESSAGES_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        return {
            "success": True,
            "message": f"Successfully saved message from {contact_name} on {platform}. I will tell the user when they return."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to store user message."
        }

def get_pending_messages(clear: bool = True):
    """
    Retrieve and optionally clear pending messages.

    Args:
        clear (bool): Whether to clear the messages after retrieving them

    Returns:
        dict: Success status and list of messages
    """
    try:
        _init_pending_messages()
        with open(PENDING_MESSAGES_FILE, 'r') as f:
            data = json.load(f)

        messages = data.get("messages", [])
        count = data.get("pending_count", 0)

        if clear and count > 0:
            with open(PENDING_MESSAGES_FILE, 'w') as f:
                json.dump({"pending_count": 0, "messages": []}, f, indent=2)

        if count == 0:
            return {
                "success": True,
                "message": "No pending messages found.",
                "messages": []
            }

        formatted_messages = "\n".join(
            [f"- From {m['name']} on {m['platform']}: '{m['content']}'" for m in messages]
        )

        return {
            "success": True,
            "message": f"You have {count} pending message(s):\n{formatted_messages}",
            "messages": messages
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve pending messages."
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

def setup_instagram():
    """
    Setup Instagram auto-reply integration.
    Guides user through adding Instagram credentials to .env.

    Returns:
        dict: Success status and instructions
    """
    try:
        ig_username = os.getenv('INSTAGRAM_USERNAME', '')
        ig_password = os.getenv('INSTAGRAM_PASSWORD', '')

        if not ig_username or not ig_password:
            instructions = """
To setup Instagram auto-reply, I need your Instagram username and password.
Please add them to your .env file as follows:
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

After adding them, say 'start Instagram messaging' to activate.
"""
            return {
                "success": False,
                "message": "Instagram credentials not configured.",
                "instructions": instructions,
                "action": "get_credentials"
            }

        return {
            "success": True,
            "message": "Instagram credentials found. Say 'start Instagram messaging' to activate auto-reply.",
            "instructions": "Make sure to add contacts to the whitelist first."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to setup Instagram."
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

        # Start Instagram bot
        if platform in ["instagram", "both"]:
            if not _messaging_processes["instagram_bot"]:
                success = _start_instagram_bot()
                if success:
                    started.append("Instagram")
                else:
                    return {
                        "success": False,
                        "message": "Failed to start Instagram. Have you added INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to your .env file?"
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

        # Stop Instagram bot
        if _messaging_processes["instagram_bot"]:
            _messaging_processes["instagram_bot"].terminate()
            _messaging_processes["instagram_bot"] = None
            stopped.append("Instagram")

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
        if _messaging_processes["instagram_bot"]:
            running.append("Instagram")
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
        elif platform == "discord":
            if contact not in whitelist["discord"]["users"]:
                whitelist["discord"]["users"].append(contact)
        elif platform == "instagram":
            if "instagram" not in whitelist:
                whitelist["instagram"] = {"users": []}
            if contact not in whitelist["instagram"]["users"]:
                whitelist["instagram"]["users"].append(contact)

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
    Get the latest message received from a contact or anyone on the given platform.
    Tries live platform access first, falls back to locally stored history.

    Args:
        platform (str): "whatsapp", "discord", or "instagram"
        contact (str, optional): Specific contact name/number, or None for most recent

    Returns:
        dict: Success status with message details
    """
    import time as _time

    def _fmt_time(ts):
        if not ts:
            return "unknown time"
        return _time.strftime("%Y-%m-%d %H:%M", _time.localtime(float(ts)))

    def _history_lookup(plat, contact_filter=None):
        """Read last message from the per-platform history file."""
        from src.messaging.history import PLATFORM_FILES
        import json as _j
        history_file = PLATFORM_FILES.get(plat)
        if not history_file or not history_file.exists():
            legacy = Path(__file__).parent.parent.parent / "messaging" / "messaging_history.json"
            if legacy.exists():
                try:
                    data = _j.loads(legacy.read_text(encoding="utf-8"))
                    contacts = data.get(plat, {})
                except Exception:
                    return None
            else:
                return None
        else:
            try:
                contacts = _j.loads(history_file.read_text(encoding="utf-8"))
            except Exception:
                return None

        if not contacts:
            return None

        if contact_filter:
            cf = contact_filter.lower()
            contacts = {
                cid: info for cid, info in contacts.items()
                if cf in info.get("name", "").lower() or cf in cid.lower()
            }
            if not contacts:
                return None

        latest_id = max(contacts, key=lambda cid: contacts[cid].get("last_interaction", 0))
        info = contacts[latest_id]
        ts = info.get("last_interaction", 0)
        return {
            "success": True,
            "contact": info.get("name", latest_id),
            "body": info.get("last_message", ""),
            "reply_sent": info.get("last_reply", ""),
            "timestamp": _fmt_time(ts),
            "source": "history",
            "message": f"[From history - bot offline] Last message from {info.get('name', latest_id)} at {_fmt_time(ts)}: \"{info.get('last_message', '')}\""
        }

    try:
        # ── WhatsApp ──────────────────────────────────────────────────────────
        if platform == "whatsapp":
            try:
                health = requests.get("http://localhost:3000/health", timeout=2)
                if health.status_code == 200:
                    params = {}
                    if contact:
                        params["contact"] = contact
                    resp = requests.get("http://localhost:3000/last_message", params=params, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("success"):
                            msg = data.get("message", {})
                            from_name = msg.get("fromName", "Unknown")
                            body = msg.get("body", "")
                            ts = msg.get("timestamp") or msg.get("date", "")
                            time_str = _fmt_time(ts) if str(ts).isdigit() else str(ts)
                            return {
                                "success": True,
                                "contact": from_name,
                                "body": body,
                                "timestamp": time_str,
                                "source": "live",
                                "message": f"Latest WhatsApp message from {from_name} at {time_str}: \"{body}\""
                            }
            except Exception:
                pass

            result = _history_lookup("whatsapp", contact)
            if result:
                return result
            return {
                "success": False,
                "message": "No WhatsApp messages found. Make sure the WhatsApp bridge is running."
            }

        # ── Discord ───────────────────────────────────────────────────────────
        elif platform == "discord":
            import os as _os
            token = _os.getenv("DISCORD_USER_TOKEN", "")
            if token:
                try:
                    from src.messaging.whitelist import WhitelistManager
                    wl = WhitelistManager()
                    users = wl.whitelist.get("discord", {}).get("users", [])
                    labels = wl.whitelist.get("discord", {}).get("labels", {})
                    headers = {
                        "authorization": token,
                        "content-type": "application/json",
                        "user-agent": "Mozilla/5.0"
                    }
                    check_users = users
                    if contact:
                        cf = contact.lower()
                        check_users = [uid for uid in users if cf in labels.get(uid, "").lower() or cf in uid.lower()] or users

                    best_msg = None
                    best_ts = 0
                    me_resp = requests.get("https://discord.com/api/v9/users/@me", headers=headers, timeout=3)
                    my_id = me_resp.json().get("id", "") if me_resp.status_code == 200 else ""

                    for uid in check_users[:5]:
                        try:
                            r = requests.post("https://discord.com/api/v9/users/@me/channels", headers=headers, json={"recipient_id": uid}, timeout=5)
                            if r.status_code not in (200, 201):
                                continue
                            ch_id = r.json().get("id")
                            if not ch_id:
                                continue
                            r2 = requests.get(f"https://discord.com/api/v9/channels/{ch_id}/messages?limit=3", headers=headers, timeout=5)
                            if r2.status_code != 200:
                                continue
                            for m in r2.json():
                                if m.get("author", {}).get("id") == my_id:
                                    continue
                                if not m.get("content"):
                                    continue
                                import datetime
                                ts_str = m.get("timestamp", "")
                                try:
                                    dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                                    ts_unix = dt.timestamp()
                                except Exception:
                                    ts_unix = 0
                                if ts_unix > best_ts:
                                    best_ts = ts_unix
                                    best_msg = {
                                        "contact": labels.get(uid, m.get("author", {}).get("username", uid)),
                                        "body": m.get("content", ""),
                                        "timestamp": _fmt_time(ts_unix),
                                        "source": "live"
                                    }
                                break  # only need the latest per user
                        except Exception:
                            continue

                    if best_msg:
                        return {
                            "success": True,
                            **best_msg,
                            "message": f"Latest Discord DM from {best_msg['contact']} at {best_msg['timestamp']}: \"{best_msg['body']}\""
                        }
                except Exception as discord_err:
                    print(f"[get_last_message] Discord live check failed: {discord_err}")

            result = _history_lookup("discord", contact)
            if result:
                return result
            return {
                "success": False,
                "message": "No Discord messages found. Make sure the Discord bot is running."
            }

        # ── Instagram ─────────────────────────────────────────────────────────
        elif platform == "instagram":
            import os as _os
            ig_user = _os.getenv("INSTAGRAM_USERNAME", "")
            ig_pass = _os.getenv("INSTAGRAM_PASSWORD", "")
            session_file = Path(__file__).parent.parent.parent / "messaging" / "instagram_session.json"

            if ig_user and ig_pass and session_file.exists():
                try:
                    from instagrapi import Client
                    cl = Client()
                    cl.load_settings(session_file)
                    cl.login(ig_user, ig_pass)
                    threads = cl.direct_threads(amount=5)
                    best_msg = None
                    best_ts = 0
                    me = str(cl.user_id)

                    for thread in threads:
                        for msg in thread.messages:
                            if str(msg.user_id) == me or not msg.text:
                                continue
                            sender_name = None
                            for u in thread.users:
                                if str(u.pk) == str(msg.user_id):
                                    sender_name = u.username
                                    break
                            sender_name = sender_name or str(msg.user_id)
                            if contact and contact.lower() not in sender_name.lower():
                                continue
                            ts_unix = msg.timestamp.timestamp() if hasattr(msg.timestamp, "timestamp") else 0
                            if ts_unix > best_ts:
                                best_ts = ts_unix
                                best_msg = {
                                    "contact": sender_name,
                                    "body": msg.text,
                                    "timestamp": _fmt_time(ts_unix),
                                    "source": "live"
                                }

                    if best_msg:
                        return {
                            "success": True,
                            **best_msg,
                            "message": f"Latest Instagram DM from {best_msg['contact']} at {best_msg['timestamp']}: \"{best_msg['body']}\""
                        }
                except Exception as ig_err:
                    print(f"[get_last_message] Instagram live check failed: {ig_err}")

            result = _history_lookup("instagram", contact)
            if result:
                return result
            return {
                "success": False,
                "message": "No Instagram DMs found. Add INSTAGRAM_USERNAME/PASSWORD to .env and ensure the Instagram bot session file exists."
            }

        else:
            return {
                "success": False,
                "message": "Invalid platform. Use 'whatsapp', 'discord', or 'instagram'."
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get message: {str(e)}"
        }


def get_all_new_messages(platform: str = "all", mark_as_read: bool = True):
    """
    Get new (unreported) messages across WhatsApp, Discord, and Instagram.
    After reporting, messages are marked so ARIA won't repeat them unless
    the user specifically asks about a person or date.

    Args:
        platform (str): "all", "discord", "whatsapp", or "instagram"
        mark_as_read (bool): Mark returned messages as reported. Default True.

    Returns:
        dict: Per-platform breakdown of new messages
    """
    try:
        from src.messaging.history import MessagingHistory, PLATFORM_FILES
        import time as _time

        history = MessagingHistory()
        platforms_to_check = list(PLATFORM_FILES.keys()) if platform == "all" else [platform]

        results = {}
        total = 0

        for plat in platforms_to_check:
            unreported = history.get_unreported(plat)
            if not unreported:
                results[plat] = []
                continue

            formatted = []
            contact_ids = []
            for entry in unreported:
                ts = entry.get("last_interaction", 0)
                time_str = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ts)) if ts else "unknown time"
                formatted.append({
                    "contact": entry.get("name", entry.get("contact_id", "Unknown")),
                    "message": entry.get("last_message", ""),
                    "time": time_str
                })
                contact_ids.append(entry["contact_id"])

            results[plat] = formatted
            total += len(formatted)

            if mark_as_read:
                history.mark_reported(plat, contact_ids)

        if total == 0:
            return {
                "success": True,
                "message": "No new messages across any platform.",
                "results": {}
            }

        lines = []
        for plat, msgs in results.items():
            if not msgs:
                lines.append(f"{plat.capitalize()}: No new messages.")
            else:
                lines.append(f"\n{plat.capitalize()} ({len(msgs)} new):")
                for m in msgs:
                    lines.append(f"  - {m['contact']} at {m['time']}: \"{m['message']}\"")

        return {
            "success": True,
            "total_new": total,
            "message": "\n".join(lines).strip(),
            "results": results,
            "marked_as_read": mark_as_read
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get new messages: {str(e)}"
        }


def send_message(platform, contact, message):
    """
    Send a message to a contact on WhatsApp, Discord, or Instagram.

    Args:
        platform (str): "whatsapp", "discord", or "instagram"
        contact (str): Contact name/number or Discord user ID
        message (str): Message to send

    Returns:
        dict: Success status and message
    """
    try:
        platform = (platform or "").lower().strip()
        if platform not in ("whatsapp", "discord", "instagram"):
            return {
                "success": False,
                "message": "Invalid platform. Use 'whatsapp', 'discord', or 'instagram'."
            }

        # Ensure WhatsApp bridge availability before any WhatsApp contact lookup/sending.
        if platform == "whatsapp":
            bridge_running = False
            try:
                health_check = requests.get('http://localhost:3000/health', timeout=3)
                if health_check.status_code == 200:
                    bridge_running = True
            except Exception:
                bridge_running = False

            if not bridge_running and not _messaging_processes["whatsapp_bridge"]:
                if not _messaging_processes["http_server"]:
                    try:
                        requests.get('http://localhost:5000/health', timeout=1)
                    except Exception:
                        _start_http_server()
                        time.sleep(2)
                _start_whatsapp_bridge()
                time.sleep(10)

            try:
                bridge_ready_check = requests.get('http://localhost:3000/health', timeout=3)
                bridge_running = bridge_ready_check.status_code == 200
            except Exception:
                bridge_running = False

            if not bridge_running:
                return {
                    "success": False,
                    "message": "WhatsApp bridge is not responding. Make sure it's running and connected."
                }

        # 1) Fast path: exact learned alias
        alias_hit = _get_alias_mapping(platform, contact)
        if alias_hit:
            send_result = _send_message_to_target(
                platform=platform,
                target_id=alias_hit["target_id"],
                target_display=alias_hit.get("target_display", alias_hit["target_id"]),
                message=message
            )
            if send_result.get("success"):
                send_result["resolved_via"] = "alias_memory"
            return send_result

        # 2) Resolve best candidate from platform contacts/DMs and ask confirmation first
        best = _resolve_contact_candidate(platform, contact)
        if not best:
            return {
                "success": False,
                "message": (
                    f"I couldn't confidently match '{contact}' in your {platform} contacts/DMs. "
                    "Please provide the exact username/ID."
                )
            }

        pending = _create_pending_confirmation(
            platform=platform,
            contact=contact,
            message=message,
            target_id=best["id"],
            target_display=best.get("display", best["id"])
        )

        return {
            "success": True,
            "confirmation_required": True,
            "confirmation_id": pending["confirmation_id"],
            "suggested_contact": pending["target_display"],
            "suggested_contact_id": pending["target_id"],
            "message": (
                f"Best match for '{contact}' is '{pending['target_display']}' on {platform}. "
                f"If this is correct, call confirm_pending_message_send with confirmation_id='{pending['confirmation_id']}' and approve=true."
            )
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send message: {str(e)}"
        }


def confirm_pending_message_send(confirmation_id: str, approve: bool = True, remember_alias: bool = True):
    """
    Confirm or cancel a previously suggested contact match, then send if approved.

    Args:
        confirmation_id (str): ID returned by send_message when confirmation is required.
        approve (bool): True to send, False to cancel.
        remember_alias (bool): Store spoken alias -> resolved contact for next time.

    Returns:
        dict: Confirmation outcome and send status when approved.
    """
    pending = _pop_pending_confirmation(confirmation_id)
    if not pending:
        return {
            "success": False,
            "message": "That confirmation request was not found or has expired."
        }

    if not approve:
        return {
            "success": True,
            "message": "Okay, cancelled. I did not send the message."
        }

    send_result = _send_message_to_target(
        platform=pending["platform"],
        target_id=pending["target_id"],
        target_display=pending["target_display"],
        message=pending["message"]
    )
    if not send_result.get("success"):
        return send_result

    if remember_alias:
        _save_alias_mapping(
            platform=pending["platform"],
            spoken_alias=pending["contact"],
            target_id=pending["target_id"],
            target_display=pending["target_display"]
        )
        send_result["alias_saved"] = {
            "alias": pending["contact"],
            "target_display": pending["target_display"],
            "platform": pending["platform"]
        }

    return send_result


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
            discord_users = whitelist.get("discord", {}).get("users", [])
            discord_channels = whitelist.get("discord", {}).get("channels", [])
            instagram_users = whitelist.get("instagram", {}).get("users", [])

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

            if instagram_users:
                message += f"\nInstagram Users ({len(instagram_users)}):\n"
                for user in instagram_users:
                    message += f"  - {user}\n"
            else:
                message += "\nInstagram Users: None\n"

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
                if contact in whitelist.get("discord", {}).get("users", []):
                    whitelist["discord"]["users"].remove(contact)
                    removed = True
            elif platform == "instagram":
                if contact in whitelist.get("instagram", {}).get("users", []):
                    whitelist["instagram"]["users"].remove(contact)
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
                count = len(whitelist.get("discord", {}).get("users", [])) + len(whitelist.get("discord", {}).get("channels", []))
                whitelist["discord"]["users"] = []
                whitelist["discord"]["channels"] = []
            elif platform == "instagram":
                count = len(whitelist.get("instagram", {}).get("users", []))
                whitelist["instagram"]["users"] = []
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
        bot_file = Path(__file__).parent.parent.parent / "messaging" / "discord_bot.py"
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

def _start_instagram_bot():
    """Start Instagram bot process."""
    try:
        import sys
        bot_file = Path(__file__).parent.parent.parent / "messaging" / "instagram_bot.py"
        process = subprocess.Popen(
            [sys.executable, str(bot_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        _messaging_processes["instagram_bot"] = process

        # Start a thread to print output
        def print_output():
            for line in process.stdout:
                print(line, end='')

        threading.Thread(target=print_output, daemon=True).start()

        return True
    except Exception as e:
        print(f"Error starting Instagram bot: {e}")
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
