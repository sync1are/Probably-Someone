"""System tools: screenshot capture and other system utilities."""

import pyautogui
import pyperclip
import pygetwindow as gw
import io
import json
import base64
import subprocess
import urllib.request
from PIL import Image

import os
import time

# Keywords that identify browser windows by title
_BROWSER_KEYWORDS = ["edge", "chrome", "firefox", "brave", "opera", "vivaldi", "arc"]

# CDP port — matches what browser_use_tools uses
_CDP_PORT = int(os.getenv("EDGE_CDP_PORT", "9222"))


def _cdp_screenshot_sync(port: int = _CDP_PORT) -> str | None:
    """
    Capture the active browser tab's viewport via Chrome DevTools Protocol.
    Returns a base64-encoded JPEG string, or None on failure.
    Works even when the browser is behind other windows or minimized.
    Uses `websockets` (already in requirements) via a thread so it's safe
    to call from inside a running asyncio event loop.
    """
    import asyncio
    import concurrent.futures

    async def _grab():
        import websockets
        # Get list of debuggable targets
        with urllib.request.urlopen(f"http://localhost:{port}/json", timeout=3) as resp:
            targets = json.loads(resp.read())

        page_target = next(
            (t for t in targets if t.get("type") == "page" and "webSocketDebuggerUrl" in t),
            None
        )
        if not page_target:
            print("[screenshot] CDP: no debuggable page tab found.")
            return None

        ws_url = page_target["webSocketDebuggerUrl"]
        print(f"[screenshot] CDP: capturing tab '{page_target.get('title', '?')}'")

        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({
                "id": 1,
                "method": "Page.captureScreenshot",
                "params": {"format": "jpeg", "quality": 92, "captureBeyondViewport": False}
            }))
            result = json.loads(await ws.recv())

        if "result" in result and "data" in result["result"]:
            return result["result"]["data"]  # base64 JPEG

        print(f"[screenshot] CDP: unexpected result keys: {list(result.keys())}")
        return None

    try:
        # Always run in a fresh thread with its own event loop —
        # safe even when called from inside ARIA's running asyncio loop
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _grab())
            return future.result(timeout=15)
    except Exception as e:
        print(f"[screenshot] CDP screenshot failed: {e}")
        return None


# JavaScript injected via CDP to extract meaningful image URLs from the DOM
_EXTRACT_IMAGES_JS = """
(function() {
    var imgs = Array.from(document.querySelectorAll('img'));
    var results = [];
    imgs.forEach(function(img) {
        // Prefer srcset largest version, then currentSrc, then src
        var url = img.currentSrc || img.src || '';
        if (!url || url.startsWith('data:')) return;
        var w = img.naturalWidth || img.width || 0;
        var h = img.naturalHeight || img.height || 0;
        if (w < 80 || h < 80) return;  // skip tiny icons/spacers
        // Pinterest: upgrade thumbnail URL to originals for max quality
        url = url.replace(/\\/\\d+x(\\/|$)/, '/originals$1')
                 .replace(/\\/\\d+x\\d+\\//, '/originals/');
        results.push({url: url, w: w, h: h, alt: img.alt || ''});
    });
    // Sort by area descending — biggest images first
    results.sort(function(a, b) { return (b.w * b.h) - (a.w * a.h); });
    // Deduplicate by URL
    var seen = {};
    results = results.filter(function(r) {
        if (seen[r.url]) return false;
        seen[r.url] = true;
        return true;
    });
    return JSON.stringify(results.slice(0, 20));
})();
"""


def scrape_browser_images(count: int = 5, min_width: int = 80, min_height: int = 80) -> dict:
    """
    Extract and download images directly from the current browser tab's DOM via CDP.

    Instead of taking a screenshot, this runs JavaScript on the live page to pull
    the actual <img> src URLs, downloads the image files, and returns their paths.
    Works even when the browser is in the background. Full resolution — no compression.

    Args:
        count:      Max number of images to download (default 5).
        min_width:  Minimum image width to include (pixels).
        min_height: Minimum image height to include (pixels).

    Returns:
        dict with 'success', 'filepaths' (list of saved paths), 'count', 'message'.
    """
    import asyncio
    import concurrent.futures
    import urllib.request as _urlreq
    import urllib.error

    async def _extract_and_download():
        import websockets

        # 1. Get CDP targets
        with _urlreq.urlopen(f"http://localhost:{_CDP_PORT}/json", timeout=5) as resp:
            targets = json.loads(resp.read())

        page = next(
            (t for t in targets if t.get("type") == "page" and "webSocketDebuggerUrl" in t),
            None
        )
        if not page:
            return {"success": False, "error": "No debuggable browser tab found. Is Edge running with CDP?"}

        ws_url = page["webSocketDebuggerUrl"]
        page_url = page.get("url", "")
        print(f"[scrape_images] Extracting from tab: {page.get('title', '?')} ({page_url[:60]})")

        async with websockets.connect(ws_url) as ws:
            # 2. Run JS to extract image URLs from DOM
            await ws.send(json.dumps({
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": _EXTRACT_IMAGES_JS,
                    "returnByValue": True
                }
            }))
            result = json.loads(await ws.recv())

        value = result.get("result", {}).get("result", {}).get("value")
        if not value:
            return {"success": False, "error": "No images found in DOM or JS evaluation failed."}

        images = json.loads(value)
        print(f"[scrape_images] Found {len(images)} candidate images in DOM")

        # 3. Download up to `count` images
        os.makedirs("temp", exist_ok=True)
        filepaths = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": page_url,
        }

        for img_info in images:
            if len(filepaths) >= count:
                break
            url = img_info["url"]
            if not url.startswith("http"):
                continue
            try:
                req = _urlreq.Request(url, headers=headers)
                with _urlreq.urlopen(req, timeout=10) as r:
                    data = r.read()
                content_type = r.headers.get("Content-Type", "image/jpeg")
                ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else \
                      "png" if "png" in content_type else \
                      "webp" if "webp" in content_type else "jpg"
                fname = f"temp/scraped_{int(time.time())}_{len(filepaths)}.{ext}"
                fpath = os.path.abspath(fname)
                with open(fpath, "wb") as f:
                    f.write(data)
                filepaths.append(fpath)
                print(f"[scrape_images] Saved: {fname} ({img_info['w']}x{img_info['h']}) — {len(data)//1024}KB")
            except Exception as e:
                print(f"[scrape_images] Failed to download {url[:80]}: {e}")
                continue

        if not filepaths:
            return {"success": False, "error": "Could not download any images from the page."}

        return {
            "success": True,
            "filepaths": filepaths,
            "count": len(filepaths),
            "message": f"Downloaded {len(filepaths)} image(s) directly from page DOM."
        }

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _extract_and_download())
            return future.result(timeout=30)
    except Exception as e:
        return {"success": False, "error": f"scrape_browser_images failed: {e}"}


def _find_browser_window():
    """Return the best browser window (largest area wins on ties), or None."""
    best = None
    best_area = 0
    for win in gw.getAllWindows():
        title = win.title.lower()
        if any(kw in title for kw in _BROWSER_KEYWORDS):
            area = win.width * win.height
            if area > best_area and win.width > 100 and win.height > 100:
                best_area = area
                best = win
    return best


def take_screenshot(mode="browser", save_to_disk=True):
    """
    Captures a screenshot.

    Args:
        mode: "browser" (default) – captures the active browser tab content via CDP
              (works even when browser is in background). Falls back to window-crop,
              then full screen.
              "full" – captures the entire desktop screen.
        save_to_disk: If True, saves a high-quality copy to temp/.

    Returns a base64-encoded image and optionally a file path.
    """
    try:
        img_base64 = None
        source_desc = "full screen"
        screenshot_pil = None

        if mode == "browser":
            # --- Priority 1: CDP direct viewport capture (background-safe) ---
            cdp_b64 = _cdp_screenshot_sync(_CDP_PORT)
            if cdp_b64:
                img_base64 = cdp_b64
                source_desc = "browser viewport (CDP)"
                # Decode for disk save & dimension reporting
                screenshot_pil = Image.open(io.BytesIO(base64.b64decode(cdp_b64))).convert("RGB")
                print(f"[screenshot] CDP capture success: {screenshot_pil.width}x{screenshot_pil.height}")
            else:
                # --- Priority 2: pygetwindow crop from full desktop capture ---
                full = pyautogui.screenshot().convert("RGB")
                win = _find_browser_window()
                if win:
                    screen_w, screen_h = pyautogui.size()
                    left   = max(0, win.left)
                    top    = max(0, win.top)
                    right  = min(screen_w, win.left + win.width)
                    bottom = min(screen_h, win.top + win.height)
                    if right > left and bottom > top:
                        screenshot_pil = full.crop((left, top, right, bottom))
                        source_desc = f"browser window crop ({win.title[:40]})"
                        print(f"[screenshot] Window crop: {right-left}x{bottom-top}")
                    else:
                        screenshot_pil = full
                        source_desc = "full screen (window bounds invalid)"
                else:
                    screenshot_pil = full
                    source_desc = "full screen (no browser window found)"
        else:
            # mode == "full"
            screenshot_pil = pyautogui.screenshot().convert("RGB")
            source_desc = "full screen"

        # Save high-quality copy to disk
        filepath = None
        if save_to_disk and screenshot_pil:
            os.makedirs("temp", exist_ok=True)
            filepath = os.path.abspath(f"temp/screenshot_{int(time.time())}.jpg")
            screenshot_pil.save(filepath, format="JPEG", quality=95)

        # Build LLM-sized base64 if we don't already have it from CDP
        if img_base64 is None and screenshot_pil:
            llm_img = screenshot_pil.copy()
            llm_img.thumbnail((1280, 720))
            buf = io.BytesIO()
            llm_img.save(buf, format="JPEG", quality=65, optimize=True)
            img_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        w = screenshot_pil.width if screenshot_pil else 0
        h = screenshot_pil.height if screenshot_pil else 0

        return {
            "success": True,
            "image_base64": img_base64,
            "filepath": filepath,
            "width": w,
            "height": h,
            "message": f"Screenshot captured ({source_desc})" + (f" and saved to {filepath}" if filepath else "")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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
