"""System tools: screenshot capture and other system utilities."""

import pyautogui
import pyperclip
import pygetwindow as gw
import io
import base64
import subprocess


import os
import time

def take_screenshot(mode="full", save_to_disk=True):
    """
    Captures a screenshot of the entire screen.
    Returns a base64-encoded image and optionally a file path.
    """
    try:
        screenshot = pyautogui.screenshot()
        
        # Convert to RGB (required for JPEG)
        screenshot = screenshot.convert("RGB")
        
        # Save a high-quality version to disk if requested
        filepath = None
        if save_to_disk:
            os.makedirs("temp", exist_ok=True)
            filepath = os.path.abspath(f"temp/screenshot_{int(time.time())}.jpg")
            screenshot.save(filepath, format='JPEG', quality=95)

        # Resize image to reduce base64 size for LLM (maintains aspect ratio)
        # We use a copy for the thumbnail to not affect the saved file
        llm_screenshot = screenshot.copy()
        llm_screenshot.thumbnail((1280, 720))
        
        # Convert to bytes as JPEG with lower quality for LLM
        img_buffer = io.BytesIO()
        llm_screenshot.save(img_buffer, format='JPEG', quality=65, optimize=True)
        img_bytes = img_buffer.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return {
            'success': True,
            'image_base64': img_base64,
            'filepath': filepath,
            'width': screenshot.width,
            'height': screenshot.height,
            'message': f"Screenshot captured and saved to {filepath}" if filepath else "Screenshot captured"
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

def run_terminal_command(command: str):
    """
    Executes a powershell command and returns the output.

    Args:
        command: The command to execute in PowerShell.

    Returns:
        dict: Success status, return code, stdout, and stderr.
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
