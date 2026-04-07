"""
System Display Tools
Controls system screen brightness.
"""

from typing import Dict, Any

try:
    import screen_brightness_control as sbc
except ImportError:
    pass


def set_system_brightness(level: int) -> Dict[str, Any]:
    """
    Set system screen brightness.

    Args:
        level (int): Brightness percentage from 0 to 100

    Returns:
        dict: Success status and message
    """
    try:
        # Clamp between 0 and 100
        level = max(0, min(100, int(level)))

        # This library applies it to all monitors by default
        sbc.set_brightness(level)

        return {
            "success": True,
            "message": f"Set screen brightness to {level}%",
            "data": {"level": level}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to set screen brightness. This feature requires a supported monitor (e.g. laptop screen or a monitor with DDC/CI enabled)."
        }


def adjust_system_brightness(amount: int, direction: str = "up") -> Dict[str, Any]:
    """
    Increase or decrease system brightness by a specific amount.

    Args:
        amount (int): Percentage to adjust (e.g., 10, 20)
        direction (str): "up" or "down"

    Returns:
        dict: Success status and message
    """
    try:
        # Get the current brightness of the primary display
        current_levels = sbc.get_brightness()
        current_level = current_levels[0] if current_levels else 50

        if direction.lower() == "up":
            new_level = min(100, current_level + amount)
        else:
            new_level = max(0, current_level - amount)

        sbc.set_brightness(new_level)

        action = "Increased" if direction == "up" else "Decreased"
        return {
            "success": True,
            "message": f"{action} brightness by {amount}%. Current brightness is {new_level}%",
            "data": {"new_level": new_level}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to {direction} system brightness."
        }
