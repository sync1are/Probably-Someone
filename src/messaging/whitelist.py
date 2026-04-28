"""
Contact Whitelist Manager
Manages allowed contacts for auto-reply on WhatsApp and Discord
"""

import json
import os
from typing import List, Dict, Set


class WhitelistManager:
    """Manages whitelisted contacts for messaging platforms."""

    def __init__(self, config_file: str = None):
        if config_file is None:
            # Point to the correct new location in the messaging folder
            self.config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "messaging", "messaging_whitelist.json")
        else:
            self.config_file = config_file

        self.whitelist = self._load_whitelist()

    def _load_whitelist(self) -> Dict:
        """Load whitelist from JSON file."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Create default whitelist
            default = {
                "discord": {
                    "users": [],
                    "channels": []
                },
                "whatsapp": {
                    "contacts": []
                },
                "instagram": {
                    "users": []
                }
            }
            self._save_whitelist(default)
            return default

    def _save_whitelist(self, data: Dict = None):
        """Save whitelist to JSON file."""
        if data is None:
            data = self.whitelist

        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)

    # Discord Methods
    def is_discord_user_allowed(self, user_id: str) -> bool:
        """Check if Discord user is whitelisted."""
        return user_id in self.whitelist['discord']['users']

    def is_discord_channel_allowed(self, channel_id: str) -> bool:
        """Check if Discord channel is whitelisted."""
        return channel_id in self.whitelist['discord']['channels']

    def add_discord_user(self, user_id: str):
        """Add Discord user to whitelist."""
        if user_id not in self.whitelist['discord']['users']:
            self.whitelist['discord']['users'].append(user_id)
            self._save_whitelist()

    def add_discord_channel(self, channel_id: str):
        """Add Discord channel to whitelist."""
        if channel_id not in self.whitelist['discord']['channels']:
            self.whitelist['discord']['channels'].append(channel_id)
            self._save_whitelist()

    def remove_discord_user(self, user_id: str):
        """Remove Discord user from whitelist."""
        if user_id in self.whitelist['discord']['users']:
            self.whitelist['discord']['users'].remove(user_id)
            self._save_whitelist()

    def remove_discord_channel(self, channel_id: str):
        """Remove Discord channel from whitelist."""
        if channel_id in self.whitelist['discord']['channels']:
            self.whitelist['discord']['channels'].remove(channel_id)
            self._save_whitelist()

    # WhatsApp Methods
    def is_whatsapp_contact_allowed(self, contact: str) -> bool:
        """
        Check if WhatsApp contact is whitelisted.
        Contact can be phone number or contact name.
        """
        return contact in self.whitelist['whatsapp']['contacts']

    def add_whatsapp_contact(self, contact: str):
        """Add WhatsApp contact to whitelist."""
        if contact not in self.whitelist['whatsapp']['contacts']:
            self.whitelist['whatsapp']['contacts'].append(contact)
            self._save_whitelist()

    def remove_whatsapp_contact(self, contact: str):
        """Remove WhatsApp contact from whitelist."""
        if contact in self.whitelist['whatsapp']['contacts']:
            self.whitelist['whatsapp']['contacts'].remove(contact)
            self._save_whitelist()

    # Instagram Methods
    def is_instagram_user_allowed(self, user_id_or_username: str) -> bool:
        """Check if Instagram user is whitelisted."""
        if 'instagram' not in self.whitelist:
            self.whitelist['instagram'] = {'users': []}
            self._save_whitelist()
        return user_id_or_username in self.whitelist['instagram']['users']

    def add_instagram_user(self, user_id_or_username: str):
        """Add Instagram user to whitelist."""
        if 'instagram' not in self.whitelist:
            self.whitelist['instagram'] = {'users': []}
        if user_id_or_username not in self.whitelist['instagram']['users']:
            self.whitelist['instagram']['users'].append(user_id_or_username)
            self._save_whitelist()

    def remove_instagram_user(self, user_id_or_username: str):
        """Remove Instagram user from whitelist."""
        if 'instagram' in self.whitelist and user_id_or_username in self.whitelist['instagram']['users']:
            self.whitelist['instagram']['users'].remove(user_id_or_username)
            self._save_whitelist()

    # General Methods
    def get_all_whitelisted(self) -> Dict:
        """Get all whitelisted contacts."""
        return self.whitelist

    def clear_platform(self, platform: str):
        """Clear all whitelisted contacts for a platform."""
        if platform == "discord":
            self.whitelist['discord']['users'] = []
            self.whitelist['discord']['channels'] = []
        elif platform == "whatsapp":
            self.whitelist['whatsapp']['contacts'] = []
        elif platform == "instagram":
            if 'instagram' in self.whitelist:
                self.whitelist['instagram']['users'] = []

        self._save_whitelist()
