"""
Messaging History Manager
Tracks interaction timestamps and context summaries for autonomous messaging.
Each platform stores its history in a separate JSON file:
  messaging/discord_history.json
  messaging/whatsapp_history.json
  messaging/instagram_history.json

Each contact entry tracks a `reported` flag so ARIA never repeats messages
it has already told the user about, unless they ask specifically.
"""

import json
import time
from typing import Dict, List, Optional
from pathlib import Path


MESSAGING_DIR = Path(__file__).parent.parent.parent / "messaging"

PLATFORM_FILES = {
    "discord":   MESSAGING_DIR / "discord_history.json",
    "whatsapp":  MESSAGING_DIR / "whatsapp_history.json",
    "instagram": MESSAGING_DIR / "instagram_history.json",
}


class MessagingHistory:
    """Manages per-platform interaction history for messaging contacts."""

    def __init__(self):
        MESSAGING_DIR.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy()
        # In-memory cache: { platform: { contact_id: {...} } }
        self.history: Dict[str, Dict] = {p: self._load(p) for p in PLATFORM_FILES}

    # ── I/O helpers ────────────────────────────────────────────────────────────

    def _platform_file(self, platform: str) -> Path:
        return PLATFORM_FILES.get(platform, MESSAGING_DIR / f"{platform}_history.json")

    def _load(self, platform: str) -> Dict:
        f = self._platform_file(platform)
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self, platform: str):
        f = self._platform_file(platform)
        f.write_text(
            json.dumps(self.history.get(platform, {}), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    # ── Migration ───────────────────────────────────────────────────────────────

    def _migrate_legacy(self):
        """One-time migration: split the old combined messaging_history.json
        into per-platform files if they don't exist yet."""
        legacy = MESSAGING_DIR / "messaging_history.json"
        if not legacy.exists():
            return

        try:
            combined = json.loads(legacy.read_text(encoding="utf-8"))
        except Exception:
            return

        migrated_any = False
        for platform, contacts in combined.items():
            target = self._platform_file(platform)
            if target.exists():
                continue  # already split — don't overwrite
            target.write_text(
                json.dumps(contacts, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            migrated_any = True
            print(f"[History] Migrated {len(contacts)} contacts -> {target.name}")

        if migrated_any:
            legacy.rename(MESSAGING_DIR / "messaging_history.json.bak")
            print("[History] Legacy messaging_history.json renamed to .bak")

    # ── Public API ──────────────────────────────────────────────────────────────

    def record_interaction(
        self,
        platform: str,
        contact_id: str,
        contact_name: str,
        message: str,
        reply: str
    ):
        """Record a new incoming message interaction. Marks as unreported."""
        if platform not in self.history:
            self.history[platform] = self._load(platform)

        self.history[platform][contact_id] = {
            "name": contact_name,
            "last_interaction": time.time(),
            "last_message": message,
            "last_reply": reply,
            "reported": False,  # will be set True after ARIA tells the user
            "interaction_count": self.history[platform].get(contact_id, {}).get("interaction_count", 0) + 1
        }

        self._save(platform)

    def get_unreported(self, platform: str) -> List[Dict]:
        """Return all unreported messages for a platform."""
        contacts = self.history.get(platform, {})
        return [
            {"contact_id": cid, **info}
            for cid, info in contacts.items()
            if not info.get("reported", False)
            and not info.get("last_message", "").startswith("[INITIATED:")
        ]

    def mark_reported(self, platform: str, contact_ids: List[str]):
        """Mark specific contacts' last message as reported."""
        if platform not in self.history:
            return
        for cid in contact_ids:
            if cid in self.history[platform]:
                self.history[platform][cid]["reported"] = True
        self._save(platform)

    def mark_all_reported(self, platform: str):
        """Mark all messages on a platform as reported."""
        if platform not in self.history:
            return
        for cid in self.history[platform]:
            self.history[platform][cid]["reported"] = True
        self._save(platform)

    def get_last_interaction(self, platform: str, contact_id: str) -> Optional[Dict]:
        """Get the last interaction data for a contact."""
        return self.history.get(platform, {}).get(contact_id)

    def get_platform_history(self, platform: str) -> Dict:
        """Get all history for a specific platform (reported or not)."""
        return self.history.get(platform, {})

    def get_all_history(self) -> Dict:
        """Get the entire interaction history across all platforms."""
        return self.history
