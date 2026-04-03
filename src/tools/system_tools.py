"""System tools: screenshot capture and other system utilities."""

import pyautogui
import io
import base64


def take_screenshot():
    """
    Captures a screenshot of the entire screen.
    Returns a base64-encoded image.
    """
    try:
        screenshot = pyautogui.screenshot()
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        screenshot.save(img_buffer, format='PNG')
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
