"""
System Audio Control Tools
Controls system volume, mute state, and smart media routing (Spotify vs Browser vs System).
"""

import math
from typing import Dict, Any
from ctypes import cast, POINTER

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    import keyboard
except ImportError:
    pass  # Handled gracefully if not available on non-Windows systems

# Import Spotify tools to handle smart routing
from src.tools.spotify_tools import (
    spotify_play,
    spotify_pause,
    spotify_skip_next,
    spotify_skip_previous
)


def _get_volume_interface():
    """Helper to get the Windows Audio Endpoint Volume interface."""
    devices = AudioUtilities.GetSpeakers()
    interface = devices.EndpointVolume
    return interface


def set_system_volume(level: int) -> Dict[str, Any]:
    """
    Set system master volume.

    Args:
        level (int): Volume level from 0 to 100

    Returns:
        dict: Success status and message
    """
    try:
        # Clamp between 0 and 100
        level = max(0, min(100, int(level)))

        volume = _get_volume_interface()

        # Pycaw works in decibels, usually -65.25 (mute) to 0.0 (max)
        # We map 0-100 linearly to the scalar volume 0.0-1.0
        scalar_vol = float(level) / 100.0
        volume.SetMasterVolumeLevelScalar(scalar_vol, None)

        return {
            "success": True,
            "message": f"Set system volume to {level}%",
            "data": {"level": level}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to set system volume."
        }


def adjust_system_volume(amount: int, direction: str = "up") -> Dict[str, Any]:
    """
    Increase or decrease system volume by a specific amount.

    Args:
        amount (int): Percentage to adjust (e.g., 10, 20)
        direction (str): "up" or "down"

    Returns:
        dict: Success status and message
    """
    try:
        volume = _get_volume_interface()
        current_scalar = volume.GetMasterVolumeLevelScalar()
        current_level = int(round(current_scalar * 100))

        if direction.lower() == "up":
            new_level = min(100, current_level + amount)
        else:
            new_level = max(0, current_level - amount)

        volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)

        action = "Increased" if direction == "up" else "Decreased"
        return {
            "success": True,
            "message": f"{action} volume by {amount}%. Current volume is {new_level}%",
            "data": {"new_level": new_level}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to {direction} system volume."
        }


def toggle_system_mute(state: str = "toggle") -> Dict[str, Any]:
    """
    Mute, unmute, or toggle system audio.

    Args:
        state (str): "mute", "unmute", or "toggle"

    Returns:
        dict: Success status and message
    """
    try:
        volume = _get_volume_interface()
        current_mute = volume.GetMute()

        if state == "mute":
            new_mute = 1
        elif state == "unmute":
            new_mute = 0
        else: # toggle
            new_mute = 0 if current_mute else 1

        volume.SetMute(new_mute, None)

        action = "Muted" if new_mute else "Unmuted"
        return {
            "success": True,
            "message": f"{action} system audio.",
            "data": {"muted": bool(new_mute)}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to toggle system mute."
        }


def smart_media_control(action: str, target: str = None) -> Dict[str, Any]:
    """
    Smart routing for media playback controls.
    Priority: Explicit target > Spotify > System Media Keys

    Args:
        action (str): "play", "pause", "next", "previous"
        target (str, optional): Explicit target app (e.g., "spotify", "youtube")

    Returns:
        dict: Success status and message
    """
    action = action.lower()
    target = target.lower() if target else None

    # 1. Explicit Target: Spotify
    if target == "spotify":
        if action == "play": return spotify_play()
        elif action == "pause": return spotify_pause()
        elif action == "next": return spotify_skip_next()
        elif action == "previous": return spotify_skip_previous()
        else: return {"success": False, "message": f"Unknown Spotify action: {action}"}

    # 2. Implicit / General Media Control
    try:
        # Check if Spotify is active/playing by calling current track endpoint
        # We import here to avoid circular imports if any
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        from src.config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI

        has_spotify = bool(SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET)
        spotify_is_playing = False

        if has_spotify:
            try:
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=SPOTIPY_CLIENT_ID,
                    client_secret=SPOTIPY_CLIENT_SECRET,
                    redirect_uri=SPOTIPY_REDIRECT_URI,
                    scope="user-read-playback-state"
                ))
                current = sp.current_playback()
                spotify_is_playing = current is not None and current.get('is_playing', False)
            except:
                pass

        # Smart Routing Logic
        if spotify_is_playing:
            # If Spotify is actively playing, route controls to Spotify API
            if action == "play": return spotify_play()
            elif action == "pause": return spotify_pause()
            elif action == "next": return spotify_skip_next()
            elif action == "previous": return spotify_skip_previous()

        else:
            # Fallback to Windows System Media Keys (controls YouTube, Media Player, etc)
            if action == "play" or action == "pause":
                keyboard.send("play/pause media")
                return {"success": True, "message": f"Sent system {action} media key."}
            elif action == "next":
                keyboard.send("next track")
                return {"success": True, "message": "Sent system next track key."}
            elif action == "previous":
                keyboard.send("previous track")
                return {"success": True, "message": "Sent system previous track key."}
            else:
                return {"success": False, "message": f"Unknown system media action: {action}"}

    except Exception as e:
        return {"success": False, "error": str(e), "message": f"Failed to execute smart media control."}
