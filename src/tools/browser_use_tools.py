"""Browser-use powered web automation tools."""

import asyncio
import os
import subprocess
import time
from datetime import timedelta
from typing import Any, Dict, Optional


_cached_llm = None


def _get_cached_llm(backend: str = "ollama", model: Optional[str] = None, base_url: Optional[str] = None):
    """Create and reuse the chat model used by browser-use."""
    global _cached_llm

    if _cached_llm is None:
        try:
            from browser_use.llm import ChatOllama
        except ImportError as exc:
            raise RuntimeError(
                "Missing browser-use Ollama support. Install requirements, then run "
                "'playwright install chromium'."
            ) from exc

        _cached_llm = ChatOllama(
            model=os.getenv("BROWSER_USE_MODEL", "qwen3.5:cloud"),
            host=base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_options={
                "temperature": 0.0,
                "num_predict": int(os.getenv("BROWSER_USE_NUM_PREDICT", "512")),
                "top_k": 10,
                "top_p": 0.7,
                "repeat_penalty": 1.1,
            },
        )

    return _cached_llm


def _is_edge_cdp_available(port: int = 9222) -> bool:
    """Check if Edge is already running with CDP on the given port."""
    import urllib.request
    import urllib.error
    try:
        urllib.request.urlopen(f"http://localhost:{port}/json", timeout=2)
        return True
    except Exception:
        return False


def start_edge_with_debugging() -> Dict[str, Any]:
    """
    Start Microsoft Edge with remote debugging enabled.
    Skips launch if Edge is already running with CDP.
    """
    if _is_edge_cdp_available():
        return {
            "success": True,
            "message": "Edge is already running with remote debugging on port 9222.",
            "data": {"port": 9222},
        }

    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge_path = next((path for path in edge_paths if os.path.exists(path)), None)

    if not edge_path:
        return {
            "success": False,
            "error": "Microsoft Edge executable was not found in the standard install locations.",
        }

    try:
        # Kill existing Edge processes so we can restart it with debugging enabled on the main profile
        # This is necessary because Edge ignores the debugging flag if another instance is already running
        os.system("taskkill /F /IM msedge.exe >nul 2>&1")
        time.sleep(1)

        user_data_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")

        subprocess.Popen([
            edge_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={user_data_dir}",
            "--profile-directory=Default",
            "--no-first-run",
            "--restore-last-session",
        ])
        time.sleep(3)
        return {
            "success": True,
            "message": "Started Microsoft Edge with remote debugging on port 9222.",
            "data": {"port": 9222, "path": edge_path},
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to start Edge: {exc}"}


def _wait_for_cdp(port: int, retries: int = 12, delay: float = 1.0) -> bool:
    """Poll CDP endpoint with retries. Returns True as soon as it responds."""
    for attempt in range(retries):
        if _is_edge_cdp_available(port):
            return True
        print(f"[browser_use] Waiting for Edge CDP... ({attempt + 1}/{retries})")
        time.sleep(delay)
    return False


def _strip_screenshot_instructions(task: str) -> str:
    """
    Remove screenshot, send, save, pin, and share instructions from a task
    before passing to browser-use.

    Reasons:
    - browser-use has no bare 'screenshot' action → Pydantic crash.
    - Phrases like 'send them here' cause browser-use to click Pinterest's
      own Save/Send/Share buttons instead of just browsing.
    - Screenshots are taken by ARIA's own take_screenshot tool after the
      browser task returns.
    """
    import re
    patterns = [
        # Screenshot phrases (with optional send/share suffix)
        r",?\s*(?:then\s+)?(?:take\s+a?\s*|capture\s+a?\s*|grab\s+a?\s*)?screenshots?\s+(?:of\s+(?:them|it|the\s+results?|the\s+page))?\s*(?:and\s+(?:send|share)\s+(?:them|it)\s+(?:here|to\s+me))?",
        r"(?:take\s+a?\s*|capture\s+a?\s*|grab\s+a?\s*)?screenshots?\s+(?:of\s+(?:them|it|the\s+results?|the\s+page))\s*",
        r"screenshot\s+them\b",
        # Standalone send/share/save instructions (these trigger site UI buttons)
        r",?\s*(?:and\s+)?(?:then\s+)?(?:send|share|forward)\s+(?:them|it|the\s+(?:results?|images?|photos?|pics?))\s+(?:here|to\s+me|to\s+discord)\s*",
        r",?\s*(?:and\s+)?(?:then\s+)?(?:save|pin|bookmark|download)\s+(?:them|it|the\s+(?:results?|images?|photos?|pics?))\b",
        r"send\s+them\s+here\b",
        r"send\s+it\s+here\b",
    ]
    stripped = task
    for p in patterns:
        stripped = re.sub(p, " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s{2,}", " ", stripped).strip().rstrip(".,;")
    print(f"[browser_use] Task sanitized for browser: {stripped!r}")
    return stripped


async def _run_browser_agent(task: str, backend: str, model: Optional[str], base_url: Optional[str], verbose: bool, headless: bool = False):
    try:
        from browser_use import Agent
        from browser_use.browser.session import BrowserSession
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'browser-use'. Install requirements, then run "
            "'playwright install chromium'."
        ) from exc

    llm = _get_cached_llm(backend=backend, model=model, base_url=base_url)

    if verbose:
        print(f"[browser_use] Using {llm.provider} model: {llm.name}")

    # Strip screenshot instructions — handled by ARIA's take_screenshot tool, not browser-use
    clean_task = _strip_screenshot_instructions(task)

    # --- Strategy 1: Connect to existing Edge with CDP (preserves logins/cookies) ---
    cdp_port = int(os.getenv("EDGE_CDP_PORT", "9222"))
    if _is_edge_cdp_available(cdp_port):
        print(f"[browser_use] Connecting to existing Edge session via CDP on port {cdp_port}...")
        browser_session = BrowserSession(
            cdp_url=f"http://localhost:{cdp_port}",
            keep_alive=True,
            wait_between_actions=0.2,
            wait_for_network_idle_page_load_time=1.0,
            minimum_wait_page_load_time=0.5,
        )
    else:
        # --- Strategy 2: Launch Edge with debugging using user's real profile ---
        print("[browser_use] Edge CDP not found. Launching Edge with your profile and remote debugging...")
        launch_result = start_edge_with_debugging()
        # Poll with retries — Edge can take several seconds to expose its CDP port
        if launch_result.get("success") and _wait_for_cdp(cdp_port, retries=12, delay=1.0):
            print(f"[browser_use] Edge is up. Connecting via CDP on port {cdp_port}...")
            browser_session = BrowserSession(
                cdp_url=f"http://localhost:{cdp_port}",
                keep_alive=True,
                wait_between_actions=0.2,
                wait_for_network_idle_page_load_time=1.0,
                minimum_wait_page_load_time=0.5,
            )
        else:
            # --- Strategy 3: Fresh Chromium fallback (no logins) ---
            print("[browser_use] Could not reach Edge CDP. Falling back to fresh Chromium session.")
            browser_session = BrowserSession(
                headless=headless,
                keep_alive=True,
                wait_between_actions=0.2,
                wait_for_network_idle_page_load_time=1.0,
                minimum_wait_page_load_time=0.5,
            )

    agent = Agent(
        task=clean_task,
        llm=llm,
        browser_session=browser_session,
        use_thinking=False,
        use_judge=False,
        enable_planning=False,
        step_timeout=60,
        extend_system_message=(
            "CRITICAL RULES — follow these without exception:\n"
            "1. NEVER click Save, Pin, Bookmark, Download, Share, or Send buttons on ANY website. "
            "These are site-internal actions that will modify data and are strictly forbidden. "
            "On Pinterest specifically, do NOT click the red Save button, the send arrow, "
            "or any share/download icon.\n"
            "2. Do NOT attempt to take a screenshot or return screenshot data as an action. "
            "You have no screenshot action. Screenshots are handled externally after you finish.\n"
            "3. Your ONLY job is to NAVIGATE and BROWSE. Open pages, search, click images to "
            "view them full-size — then call done with a text summary once the image is visible.\n"
            "4. When the requested navigation is visually complete, call done immediately. "
            "Do not linger, re-verify, or take extra actions."
        ),
    )
    return await agent.run(max_steps=25)


async def browser_use_task(
    task: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    verbose: bool = False,
    backend: str = "ollama",
    headless: bool = False,
) -> Dict[str, Any]:
    """
    Run a natural-language browser automation task using browser-use.
    Automatically connects to your existing Edge session if available (port 9222),
    preserving all your logins and cookies.

    Args:
        task: The browser task to complete.
        model: Optional Ollama model override. Defaults to BROWSER_USE_MODEL or qwen3.5:cloud.
        base_url: Optional Ollama base URL override. Defaults to OLLAMA_HOST or localhost.
        verbose: If true, performs the same direct LLM test used in the prototype.
    """
    if not task or not task.strip():
        return {"success": False, "error": "A browser automation task is required."}

    start_time = time.time()
    print(f"[browser_use] Task started at {time.strftime('%H:%M:%S')}")

    try:
        result = await _run_browser_agent(
            task=task.strip(),
            backend=backend,
            model=model,
            base_url=base_url,
            verbose=verbose,
            headless=headless,
        )
    except RuntimeError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": f"Browser-use task failed: {exc}"}

    elapsed = time.time() - start_time
    return {
        "success": True,
        "message": f"Browser task completed in {elapsed:.2f}s.",
        "data": {
            "task": task,
            "result": str(result),
            "elapsed_seconds": round(elapsed, 2),
            "elapsed": str(timedelta(seconds=int(elapsed))),
        },
    }