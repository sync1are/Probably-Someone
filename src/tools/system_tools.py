"""System tools: screenshot capture and other system utilities."""

import pyautogui
import pyperclip
import pygetwindow as gw
import io
import base64


import requests
import json

def try_cdp_screenshot():
    try:
        tabs = requests.get("http://localhost:9222/json", timeout=1).json()
        tab = next((t for t in tabs if t["type"] == "page"), None)
        if not tab: return None
        
        ws_url = tab["webSocketDebuggerUrl"]
        import websocket
        ws = websocket.create_connection(ws_url, timeout=10)
        
        ws.send(json.dumps({"id": 1, "method": "Page.captureScreenshot", "params": {"format": "jpeg", "quality": 65}}))
        result = json.loads(ws.recv())
        ws.close()
        
        if "result" in result and "data" in result["result"]:
            img_data = base64.b64decode(result["result"]["data"])
            from PIL import Image
            img = Image.open(io.BytesIO(img_data))
            actual_w, actual_h = img.size
            
            img.thumbnail((1280, 720))
            thumb_w, thumb_h = img.size
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=65, optimize=True)
            final_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            return {
                'success': True,
                'image_base64': final_b64,
                'width': thumb_w,
                'height': thumb_h,
                'actual_screen_width': actual_w,
                'actual_screen_height': actual_h,
                'source': 'cdp'
            }
    except Exception:
        pass
    return None

def take_screenshot(mode="full"):
    """
    Captures a screenshot of the entire screen, or browser viewport if a browser is active.
    Returns a base64-encoded image.
    """
    try:
        # Always try CDP first — if Edge is running with --remote-debugging-port=9222,
        # use the clean viewport screenshot. The active window check was wrong because
        # when ARIA runs in a terminal, getActiveWindow() returns the terminal, not Edge.
        cdp_result = try_cdp_screenshot()
        if cdp_result:
            return cdp_result

        # Fallback to pyautogui
        screenshot = pyautogui.screenshot()
        actual_w, actual_h = screenshot.size
        
        # Convert to RGB (required for JPEG)
        screenshot = screenshot.convert("RGB")
        
        # Resize image to reduce base64 size for LLM (maintains aspect ratio)
        screenshot.thumbnail((1280, 720))
        thumb_w, thumb_h = screenshot.size
        
        # Convert to bytes as JPEG with lower quality
        img_buffer = io.BytesIO()
        screenshot.save(img_buffer, format='JPEG', quality=65, optimize=True)
        img_bytes = img_buffer.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return {
            'success': True,
            'image_base64': img_base64,
            'width': thumb_w,
            'height': thumb_h,
            'actual_screen_width': actual_w,
            'actual_screen_height': actual_h
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


def click_at(x: int, y: int, button: str = "left", clicks: int = 1, image_width: int = 1280, image_height: int = 720) -> dict:
    """
    Click at a specific pixel coordinate on the screen or in the browser viewport. Use this after taking a screenshot to interact with a UI element. x and y must come from screenshot analysis — never guess coordinates.
    """
    try:
        # Always try CDP first — port 9222 is either open (Edge with debug flags) or not.
        # Don't check active window: ARIA runs in a terminal so getActiveWindow() is the terminal.
        try:
            import requests, json, websocket
            tabs = requests.get("http://localhost:9222/json", timeout=1).json()
            tab = next((t for t in tabs if t["type"] == "page"), None)
            if tab:
                ws_url = tab["webSocketDebuggerUrl"]
                ws = websocket.create_connection(ws_url, timeout=10)

                ws.send(json.dumps({"id": 1, "method": "Page.getLayoutMetrics"}))
                metrics = json.loads(ws.recv())

                css_w = metrics["result"]["layoutViewport"]["clientWidth"]
                css_h = metrics["result"]["layoutViewport"]["clientHeight"]

                real_x = int((x / image_width) * css_w)
                real_y = int((y / image_height) * css_h)

                for _ in range(clicks):
                    ws.send(json.dumps({
                        "id": 2,
                        "method": "Input.dispatchMouseEvent",
                        "params": {
                            "type": "mousePressed",
                            "x": real_x,
                            "y": real_y,
                            "button": button,
                            "clickCount": 1
                        }
                    }))
                    ws.recv()
                    ws.send(json.dumps({
                        "id": 3,
                        "method": "Input.dispatchMouseEvent",
                        "params": {
                            "type": "mouseReleased",
                            "x": real_x,
                            "y": real_y,
                            "button": button,
                            "clickCount": 1
                        }
                    }))
                    ws.recv()
                ws.close()
                return {"success": True, "clicked_at": [real_x, real_y], "source": "cdp"}
        except Exception:
            pass  # fallback to pyautogui

        actual_w, actual_h = pyautogui.size()
        real_x = int((x / image_width) * actual_w)
        real_y = int((y / image_height) * actual_h)
        pyautogui.click(real_x, real_y, button=button, clicks=clicks)
        return {"success": True, "clicked_at": [real_x, real_y], "source": "pyautogui"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def type_text(text: str, interval: float = 0.04) -> dict:
    """
    Type a string of text into the currently focused input field. Use this after clicking a text box to enter search queries, URLs, or any other input.
    """
    try:
        pyautogui.write(text, interval=interval)
        return {"success": True, "typed": text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def press_key(key: str) -> dict:
    """
    Press a single keyboard key such as 'enter', 'tab', or 'escape'. Use this to submit forms or confirm actions after typing.
    """
    try:
        pyautogui.press(key)
        return {"success": True, "key": key}
    except Exception as e:
        return {"success": False, "error": str(e)}


def scroll(amount: int) -> dict:
    """
    Scroll the active window vertically. Positive amount scrolls up, negative scrolls down.
    A typical scroll amount is -500 to scroll down a page, or 500 to scroll up.
    """
    try:
        pyautogui.scroll(amount)
        return {"success": True, "scrolled_amount": amount}
    except Exception as e:
        return {"success": False, "error": str(e)}


def navigate_browser(url: str) -> dict:
    """
    Navigate the current browser tab to any URL using CDP. This is the fastest
    way to open a page — no new window, no click, instant navigation.
    The LLM can construct any URL dynamically (search URLs, direct page links, etc.).
    Falls back to launching Edge if no browser is open.
    """
    try:
        import websocket
        # Ensure URL has a scheme
        if not url.startswith("http"):
            url = "https://" + url

        tabs = requests.get("http://localhost:9222/json", timeout=2).json()
        tab = next((t for t in tabs if t["type"] == "page"), None)

        if tab:
            ws_url = tab["webSocketDebuggerUrl"]
            ws = websocket.create_connection(ws_url, timeout=10)
            ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": url}}))
            result = json.loads(ws.recv())
            ws.close()
            return {"success": True, "navigated_to": url, "source": "cdp"}
    except Exception:
        pass

    # Fallback: open in Edge with CDP flags
    try:
        from src.tools.launcher_tools import launch_edge
        launch_edge(url)
        return {"success": True, "navigated_to": url, "source": "new_window"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_current_url() -> dict:
    """
    Get the URL currently loaded in the browser tab. Useful for verifying
    navigation or reading the page address before deciding next steps.
    """
    try:
        import websocket
        tabs = requests.get("http://localhost:9222/json", timeout=2).json()
        tab = next((t for t in tabs if t["type"] == "page"), None)
        if tab:
            return {
                "success": True,
                "url": tab.get("url", ""),
                "title": tab.get("title", "")
            }
        return {"success": False, "error": "No active browser tab found."}
    except Exception as e:
        return {"success": False, "error": str(e)}

