import pyautogui
import base64
from io import BytesIO
from PIL import Image
import os


def take_screenshot(mode="full"):
    """
    Captures a screenshot of the screen.
    
    Args:
        mode: Either "full" for full screen or "active_window" for active window only
        
    Returns:
        dict: Contains base64 encoded image and metadata
    """
    try:
        # Take the screenshot
        if mode == "active_window":
            # For active window, we'll use full screen for now
            # (proper active window capture requires platform-specific code)
            screenshot = pyautogui.screenshot()
        else:  # full screen
            screenshot = pyautogui.screenshot()
        
        # Convert to bytes for base64 encoding
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return {
            "success": True,
            "image_base64": img_base64,
            "width": screenshot.width,
            "height": screenshot.height,
            "format": "PNG"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Tool registry - maps tool names to their handler functions
TOOL_HANDLERS = {
    "take_screenshot": take_screenshot
}


def execute_tool(tool_name, arguments):
    """
    Executes a tool by name with the given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Dictionary of arguments to pass to the tool
        
    Returns:
        Result from the tool execution
    """
    if tool_name not in TOOL_HANDLERS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }
    
    handler = TOOL_HANDLERS[tool_name]
    
    try:
        result = handler(**arguments)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Error executing {tool_name}: {str(e)}"
        }
