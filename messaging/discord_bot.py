"""
Discord Self-Bot Bridge
Polls DMs from whitelisted users and generates AI replies via the messaging controller.

NOTE: Using a user token (self-bot) violates Discord ToS. Use at your own risk.
"""

import os
import sys
import time
import json
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

# Fix emoji/unicode crashing on Windows cp1252 console
if hasattr(sys.stdout, 'buffer'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

load_dotenv()
TOKEN = os.getenv("DISCORD_USER_TOKEN")

if not TOKEN:
    print("[Discord] DISCORD_USER_TOKEN not found in .env. Exiting.")
    sys.exit(1)

# ── imports from the main app ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # project root (one level up from messaging/)
sys.path.insert(0, str(BASE_DIR))

from src.messaging.controller import MessagingController
from src.messaging.whitelist import WhitelistManager

# ── Discord API helpers ────────────────────────────────────────────────────────
DISCORD_API = "https://discord.com/api/v9"
HEADERS = {
    "authorization": TOKEN,
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0"
}

POLL_INTERVAL = 2          # seconds between polls — lower = faster replies, more API calls
WHITELIST_RELOAD = 60      # seconds between whitelist reloads


def _api_get(path: str):
    try:
        r = requests.get(f"{DISCORD_API}{path}", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        print(f"[Discord] GET {path} → HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"[Discord] GET {path} error: {e}")
    return None


def _api_post(path: str, payload: dict):
    try:
        r = requests.post(f"{DISCORD_API}{path}", headers=HEADERS, json=payload, timeout=10)
        if r.status_code in (200, 201):
            return r.json()
        print(f"[Discord] POST {path} → HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"[Discord] POST {path} error: {e}")
    return None


def open_dm_channel(user_id: str) -> str | None:
    """Open (or retrieve) a DM channel with a user. Returns the channel ID."""
    result = _api_post("/users/@me/channels", {"recipient_id": user_id})
    if result and "id" in result:
        return result["id"]
    return None


def fetch_messages(channel_id: str, after_id: str | None = None, limit: int = 10):
    """Fetch messages from a DM channel, optionally after a given message ID."""
    path = f"/channels/{channel_id}/messages?limit={limit}"
    if after_id:
        path += f"&after={after_id}"
    return _api_get(path) or []


def send_dm(channel_id: str, content: str):
    """Send a message to a DM channel."""
    return _api_post(f"/channels/{channel_id}/messages", {"content": content})


def get_me() -> dict | None:
    """Get the authenticated user's own profile."""
    return _api_get("/users/@me")


# ── Main polling loop ──────────────────────────────────────────────────────────

def main():
    print("[Discord] Starting Discord DM polling bridge...")

    # Verify token
    me = get_me()
    if not me:
        print("[Discord] Failed to authenticate. Check DISCORD_USER_TOKEN.")
        sys.exit(1)
    my_id = me["id"]
    print(f"[Discord] Authenticated as: {me.get('username')} (ID: {my_id})")

    controller = MessagingController()
    whitelist_manager = WhitelistManager()

    # Map: user_id → { channel_id, last_message_id, username }
    tracked: dict[str, dict] = {}

    def reload_whitelist():
        """Open DM channels for any newly whitelisted users."""
        whitelist_manager.whitelist = whitelist_manager._load_whitelist()
        users = whitelist_manager.whitelist.get("discord", {}).get("users", [])
        labels = whitelist_manager.whitelist.get("discord", {}).get("labels", {})

        for uid in users:
            if uid in tracked:
                continue
            print(f"[Discord] Opening DM channel for user {uid} ({labels.get(uid, 'unknown')})...")
            ch_id = open_dm_channel(uid)
            if ch_id:
                # Fetch the most recent message ID so we don't replay old history
                msgs = fetch_messages(ch_id, limit=1)
                last_id = msgs[0]["id"] if msgs else None
                tracked[uid] = {
                    "channel_id": ch_id,
                    "last_message_id": last_id,
                    "username": labels.get(uid, uid)
                }
                print(f"[Discord] OK Tracking DMs with {tracked[uid]['username']} (channel {ch_id})")
            else:
                print(f"[Discord] FAIL Could not open DM channel for user {uid}")

    reload_whitelist()

    last_whitelist_reload = time.time()

    print("[Discord] Polling for new DMs every", POLL_INTERVAL, "seconds...")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        # Periodically reload whitelist to pick up newly added contacts
        if time.time() - last_whitelist_reload > WHITELIST_RELOAD:
            reload_whitelist()
            last_whitelist_reload = time.time()

        for uid, info in list(tracked.items()):
            ch_id = info["channel_id"]
            last_id = info["last_message_id"]

            messages = fetch_messages(ch_id, after_id=last_id, limit=20)

            # Discord returns messages newest-first; reverse so we process oldest first
            for msg in reversed(messages):
                msg_id = msg["id"]
                author_id = msg.get("author", {}).get("id", "")
                content = msg.get("content", "").strip()
                msg_type = msg.get("type", 0)

                # Update pointer regardless
                if msg_id > (last_id or "0"):
                    tracked[uid]["last_message_id"] = msg_id
                    last_id = msg_id

                # Skip our own messages
                if author_id == my_id:
                    continue

                # Detect voice call (type 3 = CALL)
                if msg_type == 3:
                    username = info["username"]
                    print(f"[Discord] Incoming call from {username} — sending text response")

                    # Build call reply using current status if set
                    from src.messaging.config import get_current_status
                    status = get_current_status()
                    if status:
                        call_reply = f"Hey! I'm Alex, Aze's assistant — {status}, so he can't pick up right now. Can I help or take a message?"
                    else:
                        call_reply = f"Hey! I'm Alex, Aze's assistant — he's not available to call right now. Can I help or take a message?"

                    result = send_dm(ch_id, call_reply)
                    if result:
                        print(f"[Discord] OK Sent call response to {username}")
                    else:
                        print(f"[Discord] FAIL Could not send call response to {username}")
                    continue

                # Skip empty text messages
                if not content:
                    continue

                username = info["username"]
                print(f"[Discord] New message from {username}: {content[:80]}")

                # Route through the controller (handles whitelist check + AI reply)
                reply = loop.run_until_complete(
                    controller.handle_discord_message(
                        message_content=content,
                        user_id=uid,
                        user_name=username
                    )
                )

                if reply:
                    result = send_dm(ch_id, reply)
                    if result:
                        print(f"[Discord] OK Replied to {username}: {reply[:60]}...")
                    else:
                        print(f"[Discord] FAIL Failed to send reply to {username}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
