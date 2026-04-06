"""System tools: screenshot capture and other system utilities."""

import pyautogui
import pyperclip
import pygetwindow as gw
import io
import base64


def take_screenshot(mode="full"):
    """
    Captures a screenshot of the entire screen.
    Returns a base64-encoded image.
    """
    try:
        screenshot = pyautogui.screenshot()
        
        # Convert to RGB (required for JPEG)
        screenshot = screenshot.convert("RGB")
        
        # Resize image to reduce base64 size for LLM (maintains aspect ratio)
        screenshot.thumbnail((1280, 720))
        
        # Convert to bytes as JPEG with lower quality
        img_buffer = io.BytesIO()
        screenshot.save(img_buffer, format='JPEG', quality=65, optimize=True)
        img_bytes = img_buffer.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return {
            'success': True,
            'image_base64': img_base64,
            'width': screenshot.width,
            'height': screenshot.height
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_clipboard():
    """
    Get current clipboard content.
    
    Returns:
        dict: Success status with clipboard content or error.
    """
    try:
        content = pyperclip.paste()
        if not content:
            return {
                "success": False, 
                "error": "Clipboard is empty"
            }
        
        return {
            "success": True,
            "content": content,
            "length": len(content),
            "message": f"Retrieved {len(content)} characters from clipboard"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_clipboard(text):
    """
    Set clipboard content.
    
    Args:
        text (str): The text to copy to clipboard
    
    Returns:
        dict: Success status and message or error.
    """
    try:
        pyperclip.copy(text)
        return {
            "success": True,
            "message": f"Copied {len(text)} characters to clipboard"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_active_window():
    """
    Get information about the currently active window.
    
    Returns:
        dict: Success status with window title and app info or error.
    """
    try:
        active_window = gw.getActiveWindow()
        
        if not active_window:
            return {
                "success": False, 
                "error": "No active window detected"
            }
        
        # Extract app name from window title (heuristic)
        title = active_window.title
        app_name = title.split('-')[-1].strip() if '-' in title else title
        
        return {
            "success": True,
            "window_title": title,
            "app_name": app_name,
            "message": f"Active window: {title}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
