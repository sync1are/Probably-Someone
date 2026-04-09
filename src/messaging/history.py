"""
Messaging History Manager
Tracks interaction timestamps and context summaries for autonomous messaging
"""

import json
import os
import time
from typing import Dict, Optional


class MessagingHistory:
    """Manages interaction history for messaging contacts."""

    def __init__(self, history_file: str = None):
        if history_file is None:
            # Store in the messaging folder alongside the whitelist
            self.history_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                "messaging", 
                "messaging_history.json"
            )
        else:
            self.history_file = history_file

        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load interaction history from JSON file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_history(self):
        """Save interaction history to JSON file."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def record_interaction(
        self, 
        platform: str, 
        contact_id: str, 
        contact_name: str, 
        message: str, 
        reply: str
    ):
        """
        Record a message interaction.
        
        Args:
            platform: 'discord' or 'whatsapp'
            contact_id: Unique ID for the contact
            contact_name: Display name
            message: Incoming message text
            reply: AI-generated response
        """
        if platform not in self.history:
            self.history[platform] = {}

        # Update contact entry
        self.history[platform][contact_id] = {
            "name": contact_name,
            "last_interaction": time.time(),
            "last_message": message,
            "last_reply": reply,
            "interaction_count": self.history[platform].get(contact_id, {}).get("interaction_count", 0) + 1
        }
        
        self._save_history()

    def get_last_interaction(self, platform: str, contact_id: str) -> Optional[Dict]:
        """Get the last interaction data for a contact."""
        return self.history.get(platform, {}).get(contact_id)

    def get_all_history(self) -> Dict:
        """Get the entire interaction history."""
        return self.history
