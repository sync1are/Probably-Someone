import os
import sys
import json
import signal
import subprocess
import threading
import time
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import toml
import queue

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.core.agent import Agent
from src.config import TOOLS_FILE, DEFAULT_MODEL
from src.tools.file_tools import set_headless_permission_callback

# Tell file tools to bypass their internal CLI prompt because the Web UI 
# handles permissions interactively at the Agent level.
set_headless_permission_callback(lambda action, path: True)

app = Flask(__name__)

# Global log queue for real-time log streaming
log_queue = queue.Queue(maxsize=100)

# Pending permission requests: { request_id: { event: threading.Event, granted: bool } }
pending_permissions = {}

def warmup_backend():
    """Initializes backend connection to avoid first-request latency."""
    log_event("INFO", "Starting system warmup...")
    settings = load_settings()
    backend = settings.get("active_backend", "ollama")
    model = settings.get("models", {}).get(backend, DEFAULT_MODEL)
    
    from src.core.llm_client import LLMClient
    client = LLMClient(backend=backend)
    
    log_event("INFO", f"Warming up {backend} with model {model}...")
    try:
        # Send a tiny hidden request to "wake up" the model
        test_msg = [{"role": "user", "content": "ping"}]
        # Using a timeout to not block too long if backend is down
        # client.chat returns a generator for stream=True, or dict for stream=False
        res = client.chat(model=model, messages=test_msg, stream=False)
        if res:
            log_event("INFO", "Backend warmup successful.")
    except Exception as e:
        log_event("ERROR", f"Backend warmup failed: {str(e)}")
    
    # Optional: Pre-start TTS server if configured
    # log_event("INFO", "Warming up TTS engine...")
    # ...

def log_event(event_type, data):
    timestamp = time.strftime("%H:%M:%S")
    try:
        log_queue.put_nowait({"timestamp": timestamp, "type": event_type.lower(), "data": data})
    except queue.Full:
        try:
            log_queue.get_nowait()
        except queue.Empty:
            pass
        log_queue.put_nowait({"timestamp": timestamp, "type": event_type.lower(), "data": data})

SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")
TOOLS_TOML_PATH = os.path.join(PROJECT_ROOT, TOOLS_FILE)

# Track background processes
services = {
    "tts_server": {"process": None, "port": 8889, "cmd": [sys.executable, "src/core/tts_server.py"]},
    "whatsapp_bridge": {"process": None, "port": 3000, "cmd": ["node", "messaging/whatsapp_bridge/bridge.js"]},
    "discord_bot": {"process": None, "cmd": [sys.executable, "messaging/discord_bot.py"]},
    "instagram_bot": {"process": None, "cmd": [sys.executable, "messaging/instagram_bot.py"]},
    "messaging_http": {"process": None, "port": 5000, "cmd": [sys.executable, "src/messaging/http_server.py"]}
}

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    return {
        "active_backend": "ollama",
        "models": {
            "ollama": DEFAULT_MODEL,
            "nvidia": "mistralai/mistral-small-4-119b-2603",
            "lm_studio": "local-model"
        },
        "ollama_host": "http://localhost:11434",
        "tts": {
            "voice": "af_heart",
            "speed": 1.2,
            "sample_rate": 24000
        },
        "behavior": {
            "browser_headless": False,
            "asr_hotkey": "ctrl+shift"
        },
        "disabled_tools": []
    }

def save_settings(settings):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/settings", methods=["GET", "PUT"])
def settings_api():
    if request.method == "GET":
        return jsonify(load_settings())
    else:
        settings = request.json
        save_settings(settings)
        return jsonify({"success": True, "settings": settings})

@app.route("/api/tools", methods=["GET"])
def get_tools():
    settings = load_settings()
    disabled = settings.get("disabled_tools", [])
    
    if not os.path.exists(TOOLS_TOML_PATH):
        return jsonify([])
    
    with open(TOOLS_TOML_PATH, "r") as f:
        config = toml.load(f)
        tools = config.get("tools", [])
        
    tool_list = []
    for t in tools:
        func = t.get("function", {})
        name = func.get("name")
        tool_list.append({
            "name": name,
            "description": func.get("description"),
            "enabled": name not in disabled,
            "category": get_tool_category(name)
        })
    
    return jsonify(tool_list)

@app.route("/api/tools/<name>", methods=["PATCH"])
def toggle_tool(name):
    settings = load_settings()
    disabled = settings.get("disabled_tools", [])
    
    enabled = request.json.get("enabled", True)
    if enabled:
        if name in disabled:
            disabled.remove(name)
    else:
        if name not in disabled:
            disabled.append(name)
            
    settings["disabled_tools"] = disabled
    save_settings(settings)
    return jsonify({"success": True})

def get_tool_category(name):
    if name.startswith("spotify_"): return "Spotify"
    if name in ["setup_whatsapp", "setup_discord", "setup_instagram", "start_messaging", "stop_messaging", "messaging_status", "add_messaging_contact", "confirm_whitelist_match", "manage_whitelist", "send_message", "get_last_message", "get_all_new_messages", "set_autonomous_mode", "send_proactive_message", "store_user_message", "get_pending_messages", "set_current_status", "confirm_pending_message_send"]: return "Messaging"
    if name in ["open_application", "minimize_window", "maximize_window", "close_window", "close_all", "switch_to_window", "show_desktop"]: return "Window"
    if name in ["write_file", "append_to_file", "read_file", "list_files", "read_pdf", "open_file_in_notepad"]: return "Files"
    if name in ["set_system_volume", "adjust_system_volume", "toggle_system_mute", "set_system_brightness", "adjust_system_brightness", "smart_media_control"]: return "System"
    if name in ["browser_use_task", "start_edge_with_debugging", "search_web", "scrape_webpage"]: return "Web"
    if name in ["get_important_unread_emails", "read_specific_email", "send_email"]: return "Email"
    if name in ["get_clipboard", "set_clipboard"]: return "Clipboard"
    if name in ["take_screenshot", "get_active_window"]: return "Screenshot"
    if name == "get_latest_news": return "News"
    if name == "run_terminal_command": return "Terminal"
    return "Other"

@app.route("/api/logs/stream")
def logs_stream():
    def generate():
        while True:
            try:
                # Use a small timeout to check if the connection is still alive
                log = log_queue.get(timeout=10)
                yield f"data: {json.dumps(log)}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/chat/permission", methods=["POST"])
def chat_permission():
    data = request.json
    request_id = data.get("request_id")
    granted = data.get("granted", False)
    
    if request_id in pending_permissions:
        pending_permissions[request_id]["granted"] = granted
        pending_permissions[request_id]["event"].set()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid request ID"})

@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.json
    user_message = data.get("message")
    
    log_event("USER_QUERY", {"content": user_message})
    
    settings = load_settings()
    backend = settings.get("active_backend", "ollama")
    model = settings.get("models", {}).get(backend, DEFAULT_MODEL)
    disabled_tools = settings.get("disabled_tools", [])
    
    # Load all tools and filter
    with open(TOOLS_TOML_PATH, "r") as f:
        config = toml.load(f)
        all_tools = config.get("tools", [])
    
    filtered_tools = Agent.filter_tools(all_tools, disabled_tools)
    
    agent = Agent(
        backend=backend,
        model=model,
        tools=filtered_tools,
        browser_headless=settings.get("behavior", {}).get("browser_headless", False)
    )

    def generate():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        queue = []
        import uuid

        def output_callback(token):
            queue.append({"event": "token", "data": token})

        def tool_callback(name, args):
            queue.append({"event": "tool_call", "data": {"name": name, "args": args}})
            log_event("TOOL_CALL", {"name": name, "args": args})

        def tool_result_callback(name, result):
            queue.append({"event": "tool_result", "data": {"name": name, "result": result}})
            log_event("TOOL_RESULT", {"name": name, "result": result})

        def permission_callback(name, args):
            request_id = str(uuid.uuid4())
            event = threading.Event()
            pending_permissions[request_id] = {"event": event, "granted": False}
            
            queue.append({
                "event": "permission_request", 
                "data": {"request_id": request_id, "name": name, "args": args}
            })
            log_event("PERMISSION_REQUEST", {"name": name, "args": args})
            
            # Wait for user response from UI (max 5 minutes)
            event.wait(timeout=300)
            
            granted = pending_permissions[request_id]["granted"]
            del pending_permissions[request_id]
            
            log_event("PERMISSION_RESULT", {"name": name, "granted": granted})
            return granted

        async def run_agent():
            start_time = time.time()
            try:
                message = await agent.run(
                    user_message, 
                    output_callback, 
                    tool_callback, 
                    tool_result_callback,
                    permission_callback
                )
                duration = time.time() - start_time
                stats = {
                    "prompt_tokens": message.get("prompt_tokens", 0),
                    "eval_tokens": message.get("eval_tokens", 0),
                    "duration": round(duration, 2)
                }
                log_event("RESPONSE_COMPLETE", stats)
                queue.append({"event": "final_stats", "data": stats})
            except Exception as e:
                log_event("ERROR", {"error": str(e)})
            finally:
                queue.append({"event": "done", "data": ""})

        # Run agent in a separate thread to allow yielding tokens
        thread = threading.Thread(target=lambda: loop.run_until_complete(run_agent()))
        thread.start()

        while thread.is_alive() or queue:
            if queue:
                item = queue.pop(0)
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
            else:
                time.sleep(0.05)

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/services/status", methods=["GET"])
def service_status():
    status = {}
    for name, info in services.items():
        running = info["process"] is not None and info["process"].poll() is None
        status[name] = {
            "running": running,
            "port": info.get("port"),
            "pid": info["process"].pid if running else None
        }
    return jsonify(status)

@app.route("/api/services/<name>/start", methods=["POST"])
def start_service(name):
    if name not in services:
        return jsonify({"success": False, "error": "Unknown service"})
    
    info = services[name]
    if info["process"] is not None and info["process"].poll() is None:
        return jsonify({"success": True, "message": "Service already running"})
    
    try:
        # Start process
        proc = subprocess.Popen(info["cmd"], cwd=PROJECT_ROOT)
        info["process"] = proc
        return jsonify({"success": True, "pid": proc.pid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/services/<name>/stop", methods=["POST"])
def stop_service(name):
    if name not in services:
        return jsonify({"success": False, "error": "Unknown service"})
    
    info = services[name]
    if info["process"] is None or info["process"].poll() is not None:
        return jsonify({"success": True, "message": "Service not running"})
    
    try:
        # Try graceful termination
        info["process"].terminate()
        try:
            info["process"].wait(timeout=5)
        except subprocess.TimeoutExpired:
            info["process"].kill()
            
        info["process"] = None
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    # Start warmup in background
    threading.Thread(target=warmup_backend, daemon=True).start()
    app.run(host="0.0.0.0", port=8500, debug=True)
