"""
File Operations Tools
Allows the AI to create, read, write, and manage text or JSON files.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any


# Define the base directory for user files (e.g., Desktop or Documents)
# For safety, we default to a "ARIA_Files" folder in the user's Documents
USER_DOCS = Path(os.path.expanduser("~")) / "Documents" / "ARIA_Files"


def _ensure_safe_path(filename: str) -> Path:
    """Ensure the path is safe and inside the designated ARIA folder."""
    # Create the directory if it doesn't exist
    USER_DOCS.mkdir(parents=True, exist_ok=True)

    # Prevent directory traversal attacks
    safe_name = os.path.basename(filename)
    if not safe_name:
        safe_name = "untitled.txt"

    return USER_DOCS / safe_name


def write_file(filename: str, content: str, as_json: bool = False) -> Dict[str, Any]:
    """
    Write content to a file. Overwrites if it exists.

    Args:
        filename (str): Name of the file (e.g., 'notes.txt' or 'data.json')
        content (str): The text or JSON string to write
        as_json (bool): Whether to format/validate the content as JSON

    Returns:
        dict: Success status and message
    """
    try:
        filepath = _ensure_safe_path(filename)

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
        filename (str): Name of the file
        content (str): Text to add

    Returns:
        dict: Success status and message
    """
    try:
        filepath = _ensure_safe_path(filename)

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
        filename (str): Name of the file to read

    Returns:
        dict: Success status, message, and file content
    """
    try:
        filepath = _ensure_safe_path(filename)

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


def list_files() -> Dict[str, Any]:
    """
    List all files managed by ARIA.

    Returns:
        dict: Success status and list of files
    """
    try:
        USER_DOCS.mkdir(parents=True, exist_ok=True)
        files = [f.name for f in USER_DOCS.iterdir() if f.is_file()]

        if not files:
            return {
                "success": True,
                "message": "You don't have any saved files yet.",
                "files": []
            }

        file_list_str = ", ".join(files)
        return {
            "success": True,
            "message": f"You have {len(files)} files: {file_list_str}.",
            "files": files
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list files."
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
        # First check ARIA_Files folder
        filepath = USER_DOCS / filename

        # If not there, intelligently check the user's Downloads folder
        if not filepath.exists():
            downloads_dir = Path(os.path.expanduser("~")) / "Downloads"
            filepath = downloads_dir / filename

            # Try adding .pdf extension if missing
            if not filepath.exists() and not filename.lower().endswith('.pdf'):
                filepath = downloads_dir / f"{filename}.pdf"

        if not filepath.exists():
            return {
                "success": False,
                "message": f"Could not find '{filename}' in your ARIA folder or Downloads folder."
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
