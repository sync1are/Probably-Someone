import os
import sys
import webbrowser
from threading import Timer
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

load_dotenv()

from src.web_ui.server import app, warmup_backend
import threading

def open_browser():
    webbrowser.open("http://localhost:8500")

if __name__ == "__main__":
    print("Starting ARIA Web UI on http://localhost:8500")
    # Start warmup in background
    threading.Thread(target=warmup_backend, daemon=True).start()
    # Wait 2 seconds before opening browser to ensure server is up
    Timer(2, open_browser).start()
    app.run(host="0.0.0.0", port=8500)
