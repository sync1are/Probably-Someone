import os
import win32gui
import win32process
import psutil

def get_active_window_cwd():
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return None
        
        process = psutil.Process(pid)
        cwd = process.cwd()
        
        if not cwd:
            return None

        # Check for unreliable paths
        lower_cwd = cwd.lower()
        if "program files" in lower_cwd or "appdata" in lower_cwd or "localappdata" in lower_cwd:
            return None
            
        return cwd
    except Exception:
        return None

def find_file(filename):
    cwd = get_active_window_cwd()
    if not cwd:
        cwd = os.getcwd()  # Fallback to the assistant's working directory
        
    matches = []
    
    # Pass 1: Flat search in cwd
    try:
        for f in os.listdir(cwd):
            if f.lower() == filename.lower() and os.path.isfile(os.path.join(cwd, f)):
                matches.append(os.path.abspath(os.path.join(cwd, f)))
    except Exception:
        pass
        
    if matches:
        return matches

    skip_dirs = {'node_modules', '__pycache__', '.git', 'venv', '.venv'}

    # Pass 2: Recursive search down from cwd
    try:
        for root, dirs, files in os.walk(cwd):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for f in files:
                if f.lower() == filename.lower():
                    matches.append(os.path.abspath(os.path.join(root, f)))
    except Exception:
        pass

    if matches:
        return matches
        
    # Pass 3: Recursive search from parent (as requested)
    parent_dir = os.path.dirname(cwd)
    # Prevent searching the entire root drive (C:\, D:\) which takes forever
    if parent_dir != cwd and len(parent_dir) > 3:
        try:
            for root, dirs, files in os.walk(parent_dir):
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
                for f in files:
                    if f.lower() == filename.lower():
                        p = os.path.abspath(os.path.join(root, f))
                        if p not in matches:
                            matches.append(p)
        except Exception:
            pass
            
    return matches
