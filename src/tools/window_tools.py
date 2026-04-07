"""
Window Management Tools
Control application windows (minimize, maximize, close, switch).
"""

from typing import Dict, Any
import time

try:
    import pygetwindow as gw
except ImportError:
    pass  # Handled on non-Windows/non-supported systems


def _find_window(title: str):
    """Helper to find the best matching window."""
    if not title:
        return None

    title_lower = title.lower()
    windows = gw.getAllWindows()
    best_match = None

    # Pass 1: Exact match
    for w in windows:
        if w.title and title_lower == w.title.lower():
            return w

    # Pass 2: Partial match
    for w in windows:
        if w.title and title_lower in w.title.lower():
            return w

    return None


def minimize_window(title: str = None) -> Dict[str, Any]:
    """
    Minimize a specific window or the currently active window.

    Args:
        title (str, optional): Target window title. If None, minimizes active window.

    Returns:
        dict: Success status and message
    """
    try:
        if title:
            window = _find_window(title)
            if not window:
                return {"success": False, "message": f"Could not find window matching '{title}'."}
        else:
            window = gw.getActiveWindow()
            if not window:
                return {"success": False, "message": "No active window found."}

        window.minimize()
        return {"success": True, "message": f"Minimized window: '{window.title}'"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to minimize window."}


def maximize_window(title: str = None) -> Dict[str, Any]:
    """
    Maximize a specific window or the currently active window.

    Args:
        title (str, optional): Target window title. If None, maximizes active window.

    Returns:
        dict: Success status and message
    """
    try:
        if title:
            window = _find_window(title)
            if not window:
                return {"success": False, "message": f"Could not find window matching '{title}'."}
        else:
            window = gw.getActiveWindow()
            if not window:
                return {"success": False, "message": "No active window found."}

        window.maximize()
        return {"success": True, "message": f"Maximized window: '{window.title}'"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to maximize window."}


def close_window(title: str = None) -> Dict[str, Any]:
    """
    Close a specific window or the currently active window.

    Args:
        title (str, optional): Target window title. If None, closes active window.

    Returns:
        dict: Success status and message
    """
    try:
        if title:
            window = _find_window(title)
            if not window:
                return {"success": False, "message": f"Could not find window matching '{title}'."}
        else:
            window = gw.getActiveWindow()
            if not window:
                return {"success": False, "message": "No active window found."}

        window_title = window.title
        window.close()
        return {"success": True, "message": f"Closed window: '{window_title}'"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to close window."}


def switch_to_window(title: str) -> Dict[str, Any]:
    """
    Find and focus a specific window by title.

    Args:
        title (str): Target window title to switch to.

    Returns:
        dict: Success status and message
    """
    try:
        window = _find_window(title)
        if not window:
            return {"success": False, "message": f"Could not find window matching '{title}'."}

        # Ensure it's not minimized
        if window.isMinimized:
            window.restore()
            time.sleep(0.1)

        try:
            window.activate()
        except Exception as e:
            # PyGetWindow throws a strange exception on Windows even when it succeeds
            if "The operation completed successfully" not in str(e):
                raise e

        return {"success": True, "message": f"Switched to: '{window.title}'"}
    except Exception as e:
        return {"success": False, "error": str(e), "message": f"Failed to switch to '{title}'."}


def show_desktop() -> Dict[str, Any]:
    """
    Minimize all windows to show the desktop.

    Returns:
        dict: Success status and message
    """
    try:
        # Use pygetwindow
        windows = gw.getAllWindows()
        count = 0
        for w in windows:
            if w.title and not w.isMinimized:
                try:
                    w.minimize()
                    count += 1
                except:
                    pass

        return {"success": True, "message": f"Showed desktop (minimized {count} windows)."}
    except Exception as e:
        return {"success": False, "error": str(e), "message": "Failed to show desktop."}
