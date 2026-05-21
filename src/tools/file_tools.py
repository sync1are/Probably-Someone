"""
File Operations Tools
Allows the AI to create, read, write, and manage text or JSON files.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any
from .file_finder import find_file


# Define the base directory for user files (e.g., Desktop or Documents)
# For safety, we default to a "ARIA_Files" folder in the user's Documents
USER_DOCS = Path(os.path.expanduser("~")) / "Documents" / "ARIA_Files"


# Module-level injectable permission hook (set by app.py at startup if running headless)
_headless_permission_callback = None

def set_headless_permission_callback(fn):
    """Register a callback(action, filepath) -> bool for headless permission checks."""
    global _headless_permission_callback
    _headless_permission_callback = fn


def _ask_permission(action: str, filepath: str) -> bool:
    """Prompt the user for permission in the console to read/write a file.

    Falls back to a registered callback in non-TTY mode, or denies the request if none.
    """
    # If a high-level handler (like the Web UI or Discord bridge) has already
    # registered a callback, we use that first.
    if _headless_permission_callback:
        return _headless_permission_callback(action, filepath)

    try:
        is_tty = os.isatty(sys.stdin.fileno())
    except (AttributeError, OSError):
        is_tty = False

    if not is_tty:
        # Default: Deny in headless mode if no registered callback
        print(f"[ARIA] Denied {action} permission for {filepath} (headless, no callback registered)")
        return False

    print(f"\n⚠️  ARIA is requesting permission to {action} the following file:")
    print(f"   {filepath}")
    while True:
        try:
            choice = input("   Allow this operation? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
        except EOFError:
            return False


def _resolve_path(filename: str, create_new: bool = False) -> Path:
    """Resolve the absolute path. Allows access to any file on the system.

    Args:
        filename: The filename or path to resolve.
        create_new: If True, skip the existence check and return a default path
                    for a new file. Use this when writing a new file.
    """
    # Check if filename is just a single file name without slashes
    if os.sep not in filename and (os.altsep is None or os.altsep not in filename) and not Path(filename).is_absolute():
        # For creating a new file, write directly to ARIA_Files without searching
        if create_new:
            filepath = USER_DOCS / filename
            return filepath

        matches = find_file(filename)

        if matches is None:
            if not os.isatty(sys.stdin.fileno()):
                raise FileNotFoundError(f"Could not determine working directory to find '{filename}'. Provide an absolute path.")
            print(f"\n⚠️  Could not determine the working directory to find '{filename}'.")
            while True:
                try:
                    user_path = input("   Please provide the full path to the file: ").strip()
                    if user_path:
                        path = Path(user_path).expanduser().resolve()
                        return path
                except EOFError:
                    break
        elif len(matches) == 0:
            if not os.isatty(sys.stdin.fileno()):
                raise FileNotFoundError(f"File '{filename}' not found. Provide an absolute path.")
            print(f"\n⚠️  The file '{filename}' was not found in the current context.")
            while True:
                try:
                    user_path = input("   Please provide the full path to the file: ").strip()
                    if user_path:
                        path = Path(user_path).expanduser().resolve()
                        return path
                except EOFError:
                    break
        elif len(matches) == 1:
            path = Path(matches[0]).expanduser().resolve()
            return path
        else:
            if not os.isatty(sys.stdin.fileno()):
                raise FileNotFoundError(f"Multiple matches found for '{filename}': {matches}. Provide an absolute path.")
            print(f"\n⚠️  Multiple matches found for '{filename}':")
            for i, match in enumerate(matches, 1):
                print(f"   {i}. {match}")
            while True:
                try:
                    choice = input(f"   Please select by number (1-{len(matches)}) or provide a full path: ").strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(matches):
                        path = Path(matches[int(choice) - 1]).expanduser().resolve()
                        return path
                    elif choice and not choice.isdigit():
                        path = Path(choice).expanduser().resolve()
                        return path
                    else:
                        print("   Invalid choice, please try again.")
                except EOFError:
                    break

    path = Path(filename).expanduser().resolve()
    return path


def write_file(filename: str, content: str, as_json: bool = False) -> Dict[str, Any]:
    """
    Write content to a file. Overwrites if it exists.

    Args:
        filename (str): Name of the file (can be absolute or relative path)
        content (str): The text or JSON string to write
        as_json (bool): Whether to format/validate the content as JSON

    Returns:
        dict: Success status and message
    """
    try:
        # Pass create_new=True so the file doesn't need to exist first
        filepath = _resolve_path(filename, create_new=True)
        
        # Programmatic safety check for core codebase
        try:
            resolved_file = filepath.resolve()
            project_dir = Path.cwd().resolve()
            src_dir = (project_dir / "src").resolve()
            app_py = (project_dir / "app.py").resolve()
            is_protected = (
                resolved_file == app_py or 
                resolved_file == src_dir or 
                resolved_file.is_relative_to(src_dir)
            )
        except Exception:
            protected_patterns = ['app.py', 'src/']
            is_protected = any(p in str(filepath).replace('\\', '/') for p in protected_patterns)
        
        if is_protected:
            print(f"\n🛑 CRITICAL SAFETY WARNING: ARIA is attempting to modify a CORE file:")
            print(f"   {filepath}")
            print(f"   Modifying this file could break the entire application.")
            if not _ask_permission("OVERWRITE CORE FILE", str(filepath)):
                return {
                    "success": False,
                    "message": "Access Denied. User refused to allow modification of core application files."
                }
        elif not _ask_permission("WRITE TO", str(filepath)):
            return {
                "success": False,
                "message": "Operation cancelled. User denied permission to write to the file."
            }
            
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if as_json:
            # Verify and format as valid JSON if requested
            try:
                # If they passed a string that is already JSON, parse it first
                if isinstance(content, str):
                    parsed_content = json.loads(content)
                else:
                    parsed_content = content

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(parsed_content, f, indent=4)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Failed to write file. The provided content was not valid JSON."
                }
        else:
            # Write as plain text
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(content))

        return {
            "success": True,
            "message": f"Successfully saved to {filename} in your Documents/ARIA_Files folder.",
            "data": {"filepath": str(filepath)}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to write to file {filename}."
        }


def append_to_file(filename: str, content: str) -> Dict[str, Any]:
    """
    Append text to the end of an existing file.

    Args:
        filename (str): Name of the file (can be absolute or relative path)
        content (str): Text to add

    Returns:
        dict: Success status and message
    """
    try:
        filepath = _resolve_path(filename)
        
        # Programmatic safety check for core codebase
        try:
            resolved_file = filepath.resolve()
            project_dir = Path.cwd().resolve()
            src_dir = (project_dir / "src").resolve()
            app_py = (project_dir / "app.py").resolve()
            is_protected = (
                resolved_file == app_py or 
                resolved_file == src_dir or 
                resolved_file.is_relative_to(src_dir)
            )
        except Exception:
            protected_patterns = ['app.py', 'src/']
            is_protected = any(p in str(filepath).replace('\\', '/') for p in protected_patterns)
        
        if is_protected:
            print(f"\n🛑 CRITICAL SAFETY WARNING: ARIA is attempting to modify a CORE file:")
            print(f"   {filepath}")
            print(f"   Appending to this file could break the entire application.")
            if not _ask_permission("APPEND TO CORE FILE", str(filepath)):
                return {
                    "success": False,
                    "message": "Access Denied. User refused to allow modification of core application files."
                }
        elif not _ask_permission("APPEND TO", str(filepath)):
            return {
                "success": False,
                "message": "Operation cancelled. User denied permission to append to the file."
            }
            
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Add a newline if we're appending to an existing file
        prefix = "\n" if filepath.exists() and filepath.stat().st_size > 0 else ""

        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"{prefix}{content}")

        return {
            "success": True,
            "message": f"Successfully added text to {filename}.",
            "data": {"filepath": str(filepath)}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to append to file {filename}."
        }


def read_file(filename: str) -> Dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        filename (str): Name of the file to read (can be absolute or relative path)

    Returns:
        dict: Success status, message, and file content
    """
    try:
        filepath = _resolve_path(filename)
        
        if not _ask_permission("READ", str(filepath)):
            return {
                "success": False,
                "message": "Operation cancelled. User denied permission to read the file."
            }

        if not filepath.exists():
            return {
                "success": False,
                "message": f"The file {filename} does not exist."
            }

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "success": True,
            "message": f"Read {len(content)} characters from {filename}.",
            "content": content
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to read file {filename}."
        }


def list_files(directory: str = None) -> Dict[str, Any]:
    """
    List all files in a specific directory. Defaults to the current working directory.

    Args:
        directory (str): The path to the directory to list

    Returns:
        dict: Success status and list of files
    """
    try:
        dir_path = _resolve_path(directory) if directory else Path.cwd()
        
        if not _ask_permission("LIST DIRECTORY", str(dir_path)):
            return {
                "success": False,
                "message": "Operation cancelled. User denied permission to list the directory."
            }
            
        if not dir_path.exists() or not dir_path.is_dir():
            return {
                "success": False,
                "message": f"Directory '{dir_path}' does not exist or is not a directory."
            }

        files = [f.name for f in dir_path.iterdir() if f.is_file()]

        if not files:
            return {
                "success": True,
                "message": f"No files found in {dir_path}.",
                "files": []
            }

        file_list_str = ", ".join(files)
        return {
            "success": True,
            "message": f"You have {len(files)} files in {dir_path}: {file_list_str}.",
            "files": files
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list files."
        }


def open_file_in_notepad(filename: str) -> Dict[str, Any]:
    """
    Open a file in Notepad. Safe, non-destructive — just launches Notepad with the file.

    Args:
        filename (str): Name of the file to open (can be absolute or relative path)

    Returns:
        dict: Success status and message
    """
    import subprocess
    try:
        filepath = _resolve_path(filename, create_new=True)
        if not filepath.exists():
            return {
                "success": False,
                "message": f"File not found: {filepath}. Create it first with write_file."
            }
        subprocess.Popen(["notepad.exe", str(filepath)])
        return {
            "success": True,
            "message": f"Opened {filepath} in Notepad.",
            "data": {"filepath": str(filepath)}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to open {filename} in Notepad."
        }


def read_pdf(filename: str, page_start: int = 1, page_end: int = None) -> Dict[str, Any]:
    """
    Read text from a PDF file. Automatically checks Downloads folder and ARIA_Files folder.

    Args:
        filename (str): Name of the PDF file
        page_start (int): First page to read (1-indexed)
        page_end (int): Last page to read (inclusive). If None, reads to the end.

    Returns:
        dict: Success status and extracted text
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return {"success": False, "message": "PyMuPDF is not installed. Please run 'pip install PyMuPDF'."}

    try:
        # Resolve path
        filepath = _resolve_path(filename)
        
        if not _ask_permission("READ PDF", str(filepath)):
            return {
                "success": False,
                "message": "Operation cancelled. User denied permission to read the directory or file."
            }

        if not filepath.exists():
            return {
                "success": False,
                "message": f"Could not find '{filename}' on the system."
            }

        # Open the PDF
        doc = fitz.open(filepath)
        total_pages = len(doc)

        # Handle page boundaries
        start_idx = max(0, page_start - 1)
        end_idx = total_pages if page_end is None else min(total_pages, page_end)

        if start_idx >= total_pages:
            return {"success": False, "message": f"The PDF only has {total_pages} pages."}

        # Extract text from requested pages
        extracted_text = []
        for i in range(start_idx, end_idx):
            page = doc[i]
            text = page.get_text()
            extracted_text.append(f"--- Page {i + 1} ---\n{text}")

        full_text = "\n\n".join(extracted_text)

        # Add a summary header so the LLM knows what it's looking at
        summary = f"Extracted {len(full_text)} characters from {filename} (Pages {start_idx + 1} to {end_idx} of {total_pages})."

        doc.close()

        return {
            "success": True,
            "message": summary,
            "content": full_text,
            "total_pages": total_pages
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to read PDF file {filename}."
        }
