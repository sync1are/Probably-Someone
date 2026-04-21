import time
import base64
import requests
import pygetwindow as gw
from src.tools.system_tools import take_screenshot

def test_cdp():
    # ---- Step 1: Check if port 9222 is reachable at all ----
    print("Step 1: Checking if Edge debug port 9222 is reachable...")
    try:
        tabs = requests.get("http://localhost:9222/json", timeout=2).json()
        print(f"[OK] Port 9222 is OPEN! Found {len(tabs)} tab(s).")
        for t in tabs:
            print(f"   - [{t.get('type')}] {t.get('title', 'No title')}")
    except Exception as e:
        print(f"[FAIL] Port 9222 is NOT reachable: {e}")
        print("\n--- HOW TO FIX ---")
        print("1. Close ALL Edge windows completely (check taskbar).")
        print("2. Run this command:")
        print("   Start-Process msedge.exe -ArgumentList \"--remote-debugging-port=9222\",\"--remote-allow-origins=*\"")
        print("   (BOTH flags are required! Edge ignores them if already running.)")
        return

    # ---- Step 2: Check if Edge is the active window ----
    print("\nStep 2: Looking for an active Edge window...")
    windows = gw.getWindowsWithTitle('Edge') + gw.getWindowsWithTitle('Chrome') + gw.getWindowsWithTitle('Brave')
    if not windows:
        print("[FAIL] Could not detect an Edge window. Make sure Edge is open and focused.")
        return

    browser_window = windows[0]
    safe_title = browser_window.title.encode('ascii', errors='replace').decode('ascii')
    print(f"Found: {safe_title}")
    print("Bringing Edge to the foreground...")
    try:
        browser_window.activate()
    except Exception:
        pass
    time.sleep(1)

    # ---- Step 3: Take screenshot and verify source ----
    print("\nStep 3: Taking screenshot...")
    res = take_screenshot()

    if res.get('success'):
        source = res.get('source', 'pyautogui')
        print(f"\n--- RESULTS ---")
        print(f"Screenshot Source: {source.upper()}")
        if source == 'cdp':
            print(f"[OK] SUCCESS! CDP is working. Viewport: {res['actual_screen_width']}x{res['actual_screen_height']}px")
        else:
            print("[FAIL] Screenshot fell back to pyautogui despite port being open.")
            print("This is likely a timing or window-focus issue. Try again.")

        with open("test_cdp_output.jpg", "wb") as f:
            f.write(base64.b64decode(res['image_base64']))
        print("\nSaved image as 'test_cdp_output.jpg' -- check if it's viewport-only (no tabs/address bar).")
    else:
        print(f"Error taking screenshot: {res.get('error')}")

if __name__ == '__main__':
    test_cdp()
