"""
ARIA Autonomy Engine
Triggers proactive messaging based on interaction history and user-defined goals
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional
from src.messaging.controller import MessagingController
from src.messaging.history import MessagingHistory


class AutonomyEngine:
    """Manages proactive and autonomous messaging behavior."""

    def __init__(self, controller: MessagingController):
        self.controller = controller
        self.history_manager = controller.history_manager
        self.is_running = False
        self._thread = None
        
        # Configuration for proactive check-ins
        self.checkin_threshold_hours = 24
        self.max_proactive_per_day = 1
        
        # Track proactive messages sent today to avoid spamming
        self.proactive_sent_today = {} # {contact_id: count}
        self.last_reset_time = time.time()

    def start(self):
        """Start the autonomy engine in a background thread."""
        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._run_sync, daemon=True)
        self._thread.start()
        print("[Autonomy Engine] Started")

    def stop(self):
        """Stop the autonomy engine."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("[Autonomy Engine] Stopped")

    def _run_sync(self):
        """Synchronous wrapper for the async run loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._run_loop())
        loop.close()

    async def _run_loop(self):
        """Main background loop for checking proactive triggers."""
        while self.is_running:
            try:
                # Reset daily counts if needed
                self._check_daily_reset()
                
                # Check for stale conversations that need a check-in
                await self._check_for_proactive_initiations()
                
                # Wait for next check (e.g., every 30 minutes)
                await asyncio.sleep(1800) 
            except Exception as e:
                print(f"[Autonomy Engine] Error in loop: {e}")
                await asyncio.sleep(60)

    def _check_daily_reset(self):
        """Reset daily proactive counts every 24 hours."""
        current_time = time.time()
        if current_time - self.last_reset_time > 86400:
            self.proactive_sent_today = {}
            self.last_reset_time = current_time
            print("[Autonomy Engine] Daily proactive counts reset")

    async def _check_for_proactive_initiations(self):
        """Check history and initiate messages for stale interactions."""
        history = self.history_manager.get_all_history()
        threshold_seconds = self.checkin_threshold_hours * 3600
        current_time = time.time()

        for platform, contacts in history.items():
            for contact_id, data in contacts.items():
                last_interaction = data.get("last_interaction", 0)

                # Skip if we have no valid previous interaction
                if last_interaction == 0:
                    continue

                time_since_last = current_time - last_interaction

                # If conversation is stale but not ancient history (between 24h and 48h ago)
                if (threshold_seconds < time_since_last <= threshold_seconds * 2 and
                    self.proactive_sent_today.get(contact_id, 0) < self.max_proactive_per_day):

                    contact_name = data.get("name", "Unknown")
                    last_message = data.get("last_message", "nothing")

                    # Context for initiation
                    context = f"Following up after a while. Last we spoke, the user said: {last_message}"

                    print(f"[Autonomy Engine] Triggered proactive check-in for {contact_name}")
                    # Track that we sent it BEFORE initiating to prevent infinite loops if it fails
                    self.proactive_sent_today[contact_id] = self.proactive_sent_today.get(contact_id, 0) + 1

                    # This is where the magic happens
                    try:
                        await self.controller.initiate_conversation(
                            platform=platform,
                            contact_id=contact_id,
                            contact_name=contact_name,
                            context=context
                        )
                    except Exception as e:
                        print(f"[Autonomy Engine] Failed to send proactive message to {contact_name}: {e}")
