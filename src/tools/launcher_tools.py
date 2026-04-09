"""
App Launcher Tools
Opens applications and websites by name using Windows shell execution and registry lookups.
"""

import os
import subprocess
import webbrowser
from typing import Dict, Any
from pathlib import Path


# Common application aliases and their executable names
COMMON_APPS = {
    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",

    # Editors / IDEs
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "notepad": "notepad.exe",
    "notepad++": "notepad++.exe",

    # Communication
    "discord": "discord.exe",
    "slack": "slack.exe",
    "teams": "teams.exe",
    "zoom": "zoom.exe",
    "whatsapp": "whatsapp.exe",

    # Media / Entertainment
    "spotify": "spotify.exe",
    "steam": "steam.exe",
    "vlc": "vlc.exe",

    # System Utilities
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "downloads folder": "explorer.exe shell:Downloads",
    "downloads": "explorer.exe shell:Downloads",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
}

# Common websites for URL resolution
COMMON_WEBSITES = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "reddit": "https://reddit.com",
    "netflix": "https://netflix.com",
}


def open_application(app_name: str) -> Dict[str, Any]:
    """
    Launches an application by name or common alias.

    Args:
        app_name (str): The name of the application (e.g., "chrome", "vscode", "spotify")

    Returns:
        dict: Success status and message
    """
    app_lower = app_name.lower().strip()

    try:
        # Check if it's an exact file or directory path that exists on the hard drive
        if os.path.exists(app_name):
            if os.name == 'nt':
                # If it's a directory, use explorer. If it's a file (like index.html), use startfile
                if os.path.isdir(app_name):
                    subprocess.Popen(f'explorer.exe "{app_name}"', shell=True)
                else:
                    os.startfile(app_name)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', app_name])
            else:
                subprocess.Popen(['xdg-open', app_name])

            return {
                "success": True,
                "message": f"Successfully opened {os.path.basename(app_name)}.",
                "data": {"app": app_name, "executable": app_name}
            }

        # Check if it's a known website alias first
        if app_lower in COMMON_WEBSITES:
            url = COMMON_WEBSITES[app_lower]
            webbrowser.open(url)
            return {
                "success": True,
                "message": f"Opened {app_name} website in your browser."
            }

        # Handle explicit websites (e.g., "open google.com")
        if "." in app_lower and ("/" not in app_lower or "http" in app_lower):
            # If the user tries to launch a local executable with arguments (like notepad.exe path/to/file),
            # prevent it from treating the whole string as a website.
            is_local_command = any(ext in app_lower for ext in [".exe", ".bat", ".cmd", "c:/", "c:\\"])
            if is_local_command:
                # Let it fall through to the subprocess launcher below
                pass
            else:
                url = app_lower if app_lower.startswith("http") else f"https://{app_lower}"
                webbrowser.open(url)
                return {
                    "success": True,
                    "message": f"Opened website: {url}"
                }

        # Look up executable name from aliases
        executable = COMMON_APPS.get(app_lower, app_lower)

        # On Windows, os.startfile opens the default associated program
        # or the executable if it's in the system PATH
        if os.name == 'nt':
            if app_lower == "settings":
                os.startfile(executable)
                return {"success": True, "message": "Opened Windows Settings."}
            else:
                try:
                    # Attempt to run via subprocess (more reliable for some apps)
                    subprocess.Popen(executable, shell=True)
                except FileNotFoundError:
                    # Fallback to startfile
                    os.startfile(executable)

        # Non-Windows systems (Linux/Mac fallback)
        else:
            if sys.platform == 'darwin':
                subprocess.Popen(['open', '-a', app_name])
            else:
                subprocess.Popen([executable])

        return {
            "success": True,
            "message": f"Successfully launched {app_name}.",
            "data": {"app": app_name, "executable": executable}
        }

    except Exception as e:
        error_str = str(e)
        if "The system cannot find the file specified" in error_str:
            return {
                "success": False,
                "error": error_str,
                "message": f"Could not find '{app_name}'. It may not be installed or not added to your system PATH."
            }
        return {
            "success": False,
            "error": error_str,
            "message": f"Failed to open '{app_name}'."
        }
