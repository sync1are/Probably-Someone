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

    print("[browser_use] Launching fresh browser session...")
    browser_session = BrowserSession(
        headless=False,
        keep_alive=True,
        wait_between_actions=0.2,
        wait_for_network_idle_page_load_time=1.0,
        minimum_wait_page_load_time=0.5,
    )

    agent = Agent(
        task=task,
        llm=llm,
        browser_session=browser_session,
        use_thinking=False,
        use_judge=False,
        enable_planning=False,
        step_timeout=60,
        extend_system_message=(
            "When the requested visible browser action is complete, such as a YouTube video "
            "starting playback, immediately mark the task done. Do not keep observing or "
            "verifying after the visible goal has been achieved."
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