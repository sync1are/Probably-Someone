"""
Instagram Bridge
Polls DMs from whitelisted users and generates AI replies via the messaging controller.
Uses the unofficial `instagrapi` library.
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Fix emoji/unicode crashing on Windows cp1252 console
if hasattr(sys.stdout, 'buffer'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

load_dotenv()
IG_USERNAME = os.getenv("INSTAGRAM_USERNAME")
IG_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

if not IG_USERNAME or not IG_PASSWORD:
    print("[Instagram] INSTAGRAM_USERNAME or INSTAGRAM_PASSWORD not found in .env. Exiting.")
    sys.exit(1)

# ── imports from the main app ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # project root (one level up from messaging/)
sys.path.insert(0, str(BASE_DIR))

from src.messaging.controller import MessagingController
from src.messaging.whitelist import WhitelistManager

try:
    from instagrapi import Client
    from instagrapi.exceptions import ClientError, LoginRequired
except ImportError:
    print("[Instagram] instagrapi not installed. Please run: pip install instagrapi")
    sys.exit(1)

POLL_INTERVAL = 10  # seconds between polls

def main():
    print("[Instagram] Starting Instagram DM polling bridge...")

    cl = Client()
    
    # Optional: Load session from file to avoid logging in every time
    session_file = BASE_DIR / "instagram_session.json"
    if session_file.exists():
        try:
            cl.load_settings(session_file)
            cl.login(IG_USERNAME, IG_PASSWORD)
            cl.get_timeline_feed() # test the session
            print("[Instagram] Loaded existing session.")
        except Exception as e:
            print(f"[Instagram] Session invalid, logging in again... {e}")
            cl.login(IG_USERNAME, IG_PASSWORD)
            cl.dump_settings(session_file)
    else:
        try:
            print("[Instagram] Logging in for the first time...")
            cl.login(IG_USERNAME, IG_PASSWORD)
            cl.dump_settings(session_file)
            print("[Instagram] Login successful!")
        except Exception as e:
            print(f"[Instagram] Login failed: {e}")
            sys.exit(1)

    controller = MessagingController()
    whitelist_manager = WhitelistManager()
    
    me = cl.user_id
    print(f"[Instagram] Authenticated as: {IG_USERNAME} (ID: {me})")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print(f"[Instagram] Polling for new DMs every {POLL_INTERVAL} seconds...")

    # Map: thread_id -> last_message_id
    last_message_seen = {}

    while True:
        try:
            # Refresh whitelist
            whitelist_manager.whitelist = whitelist_manager._load_whitelist()
            
            # Fetch recent threads
            threads = cl.direct_threads(amount=10)
            
            for thread in threads:
                thread_id = thread.id
                messages = thread.messages
                
                if not messages:
                    continue
                
                latest_msg = messages[0] # messages are newest first
                
                # Check if we've seen this thread before and if there are new messages
                if thread_id not in last_message_seen:
                    # First time seeing this thread, just mark the latest message as seen
                    # so we don't process old history
                    last_message_seen[thread_id] = latest_msg.id
                    continue
                
                if latest_msg.id <= last_message_seen[thread_id]:
                    continue # No new messages
                
                # Find all new messages
                new_msgs = []
                for msg in messages:
                    if msg.id > last_message_seen[thread_id]:
                        new_msgs.append(msg)
                    else:
                        break
                
                # Process oldest new message first
                for msg in reversed(new_msgs):
                    last_message_seen[thread_id] = max(last_message_seen[thread_id], msg.id)
                    
                    if str(msg.user_id) == str(me):
                        continue # Skip our own messages
                        
                    content = msg.text
                    if not content:
                        continue # Ignore non-text for now
                        
                    # Find user info
                    user_info = None
                    for user in thread.users:
                        if str(user.pk) == str(msg.user_id):
                            user_info = user
                            break
                            
                    username = user_info.username if user_info else str(msg.user_id)
                    
                    print(f"[Instagram] New message from {username}: {content[:80]}")
                    
                    # Pass to controller
                    reply = loop.run_until_complete(
                        controller.handle_instagram_message(
                            message_content=content,
                            user_id=str(msg.user_id),
                            user_name=username
                        )
                    )
                    
                    if reply:
                        try:
                            cl.direct_send(reply, user_ids=[int(msg.user_id)])
                            print(f"[Instagram] OK Replied to {username}: {reply[:60]}...")
                        except Exception as send_err:
                            print(f"[Instagram] FAIL Failed to send reply to {username}: {send_err}")
                
        except Exception as e:
            print(f"[Instagram] Error during polling: {e}")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
