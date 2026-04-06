# Future Features & Enhancements Plan

This document outlines high-impact features and improvements to add to the ARIA AI Assistant, expanding its capabilities beyond basic system tools and Spotify integration.

## 1. "Always Listening" Wake Word & Voice Input
Currently, the assistant relies on text input (`input("You: ")`). Upgrading it to a true voice assistant is the highest priority for a hands-free experience.
*   **Wake Word Detection:** Implement a local, lightweight wake word engine (e.g., `Porcupine` or `OpenWakeWord`) to listen for a specific phrase like "Hey Aria".
*   **Speech-to-Text (STT):** When the wake word is detected, use a fast local model like `faster-whisper` to transcribe the user's spoken command into text, seamlessly feeding it into the existing LLM loop.

## 2. Vision & Context Awareness Upgrades
Building upon the existing `take_screenshot` tool to make the AI more contextually aware of the active workspace.
*   **Active Window Context:** A tool to extract the title and text content of the currently active window (using libraries like `pygetwindow`, `pywin32`, or accessibility APIs). 
    *   *Example:* "Summarize this article for me" (AI reads the active Chrome window).
*   **Screen Interaction (OCR & UI Control):** Integrate an OCR library like `pytesseract`.
    *   *Example:* "Click on the 'Submit' button" (AI takes a screenshot, finds the coordinates of the word, and uses `pyautogui` to click it).

## 3. Advanced Operating System & Workflow Automation
Enhancing OS integration to be safer and more specific than a generic `execute_command` tool.
*   **Window Management:** Tools to minimize, maximize, snap, or move windows around the screen.
    *   *Example:* "Snap Spotify to the left and Chrome to the right."
*   **File System Navigation:** Add tools to search for files by name or content (`grep`-like functionality), moving beyond simple read/write operations.
    *   *Example:* "Find that PDF I downloaded yesterday about taxes."
*   **Clipboard Management:** A tool to read from and write to the clipboard (`pyperclip`).
    *   *Example:* "Translate what's in my clipboard to Spanish and save it to a file."
*   **App & Process Management:** Ability to safely terminate unresponsive tasks, list running applications, and monitor the CPU/Memory usage of specific programs (using `psutil`).
    *   *Example:* "Chrome is frozen, can you force quit it?" or "What's eating up my RAM right now?"
*   **System Settings & Power Management:** Tools to change display brightness, switch audio output devices, or lock the PC.
    *   *Example:* "Switch audio to my headphones" or "Lock my computer."
*   **Automated Desktop Workflows (Macros):** Combining multiple OS actions into a single semantic voice command to automate routine tasks.
    *   *Example:* "Start my work day" -> AI opens Slack, launches your IDE, sets your status to 'Active', and starts a focus Spotify playlist.
*   **Notification Management:** Reading Windows/OS notifications and allowing the user to interact with or clear them via voice.
    *   *Example:* "What was that last notification?" or "Clear all my notifications."

## 4. Personal Knowledge & Memory (RAG)
Giving ARIA persistent memory so it doesn't forget information between restarts.
*   **Persistent Fact Memory:** Create a simple vector database (using `chromadb` or a JSON file with embeddings) to store user preferences and facts.
    *   *Example:* "Remember that my Wi-Fi password is 'hunter2'." -> Later: "What's my Wi-Fi password again?"
*   **Local File Indexing (RAG):** Point ARIA at a specific folder (like Documents or Notes) and have it index those files so the user can ask questions about their own personal data.

## 5. Web & API Integrations
Connecting ARIA to external services to retrieve real-time, specific information.
*   **Web Scraping/Browsing:** A tool using `BeautifulSoup` or `Playwright` to fetch the actual readable content of a URL, allowing the AI to answer specific questions about web pages rather than just returning search results.
*   **Calendar & Email:** Integration with Google Workspace or Outlook APIs.
    *   *Example:* "What's my next meeting?" or "Schedule a 30-minute block for lunch at noon."
*   **Smart Home Control:** Simple local network API integrations for smart devices (Philips Hue, Home Assistant, etc.).
    *   *Example:* "Turn off the desk lamp" or "Dim the lights."