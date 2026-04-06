# Quick Context Tools - Implementation Plan

## Overview

Add three high-value, low-effort features that massively boost ARIA's utility:

1. **Clipboard Management** - "Summarize what I just copied"
2. **Active Window Context** - Know what app you're using
3. **Web Scraping** - "Summarize this article [URL]"

**Total Implementation Time:** ~1 hour  
**Value Added:** Huge productivity boost with minimal code

---

## Phase 1: Setup (5 min)

### Dependencies to Add

```bash
pip install pyperclip pygetwindow requests beautifulsoup4 lxml
```

**Add to `requirements.txt`:**
```
pyperclip==1.8.2
pygetwindow==0.0.9
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0
```

---

## Phase 2: Clipboard Management (17 min) ⚡ EASIEST WIN

### 2.1 Implementation (`src/tools/system_tools.py`)

```python
import pyperclip

def get_clipboard():
    """Get current clipboard content."""
    try:
        content = pyperclip.paste()
        if not content:
            return {"success": False, "error": "Clipboard is empty"}
        
        return {
            "success": True,
            "content": content,
            "length": len(content),
            "message": f"Retrieved {len(content)} characters from clipboard"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_clipboard(text):
    """Set clipboard content."""
    try:
        pyperclip.copy(text)
        return {
            "success": True,
            "message": f"Copied {len(text)} characters to clipboard"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 2.2 Schema (`tools.json`)

```json
{
  "type": "function",
  "function": {
    "name": "get_clipboard",
    "description": "Get the current clipboard content. Use when user says 'what did I copy', 'clipboard', 'what's in my clipboard', or 'summarize what I copied'.",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "set_clipboard",
    "description": "Copy text to the clipboard. Use when user says 'copy this', 'put this in clipboard', or 'save this to clipboard'.",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "The text to copy to clipboard"
        }
      },
      "required": ["text"]
    }
  }
}
```

### 2.3 Register (`src/tools/registry.py`)

```python
from src.tools.system_tools import (
    take_screenshot,
    get_clipboard,
    set_clipboard
)

TOOL_HANDLERS = {
    # ... existing tools ...
    "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
}
```

**Use Cases:**
- "Summarize what I just copied"
- "Translate the text in my clipboard"
- "Fix the grammar in my clipboard"
- "Copy this response to my clipboard"

---

## Phase 3: Active Window Context (15 min) 🪟

### 3.1 Implementation (`src/tools/system_tools.py`)

```python
import pygetwindow as gw

def get_active_window():
    """Get information about the currently active window."""
    try:
        active_window = gw.getActiveWindow()
        
        if not active_window:
            return {"success": False, "error": "No active window detected"}
        
        # Extract app name from window title (heuristic)
        title = active_window.title
        app_name = title.split('-')[-1].strip() if '-' in title else title
        
        return {
            "success": True,
            "window_title": title,
            "app_name": app_name,
            "message": f"Active window: {title}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 3.2 Schema (`tools.json`)

```json
{
  "type": "function",
  "function": {
    "name": "get_active_window",
    "description": "Get the title and app name of the currently active/focused window. Use when user asks about their current app, window, or what they're working on.",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  }
}
```

### 3.3 Register

Add to `TOOL_HANDLERS`: `"get_active_window": get_active_window`

**Use Cases:**
- "What app am I using?" → "You're in Visual Studio Code"
- "Help me with this program" → LLM knows context
- Automatic context for follow-up questions

---

## Phase 4: Web Scraping (20 min) 🌐

### 4.1 Implementation (`src/tools/web_tools.py` - NEW FILE)

```python
"""Web scraping and content extraction tools."""

import requests
from bs4 import BeautifulSoup

def scrape_webpage(url, extract_links=False):
    """
    Scrape and extract clean text content from a webpage.
    
    Args:
        url (str): The URL to scrape
        extract_links (bool): Whether to also extract links
    
    Returns:
        dict: Success status with extracted content
    """
    try:
        # Add headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        result = {
            "success": True,
            "url": url,
            "content": text[:10000],  # Limit to 10k chars
            "title": soup.title.string if soup.title else "No title",
            "length": len(text),
            "message": f"Extracted {len(text)} characters from {url}"
        }
        
        if extract_links:
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            result['links'] = links[:50]  # Limit to 50 links
        
        return result
        
    except requests.RequestException as e:
        return {"success": False, "error": f"Failed to fetch URL: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4.2 Schema (`tools.json`)

```json
{
  "type": "function",
  "function": {
    "name": "scrape_webpage",
    "description": "Extract text content from a webpage URL. Use when user provides a URL and wants to know what's on the page, summarize an article, or analyze web content.",
    "parameters": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "description": "The URL of the webpage to scrape"
        },
        "extract_links": {
          "type": "boolean",
          "description": "Whether to also extract links from the page. Default false."
        }
      },
      "required": ["url"]
    }
  }
}
```

### 4.3 Register (`src/tools/registry.py`)

```python
from src.tools.web_tools import scrape_webpage

TOOL_HANDLERS = {
    # ... existing tools ...
    "scrape_webpage": scrape_webpage,
}
```

**Use Cases:**
- "Summarize this article: https://example.com/article"
- "What does this page say? [URL]"
- "Compare these two articles" (with URLs)
- "Find the main points from this blog post"

---

## Phase 5: Testing (15 min)

### Test Scripts

**Clipboard:**
```
1. Copy some text
2. Say: "What did I just copy?"
3. Say: "Summarize what's in my clipboard"
4. Say: "Copy 'Hello World' to my clipboard"
```

**Window Context:**
```
1. Open VS Code
2. Say: "What app am I using?"
3. Switch to Chrome
4. Say: "Help me with this program"
```

**Web Scraping:**
```
1. Say: "Summarize this article: https://en.wikipedia.org/wiki/Python_(programming_language)"
2. Say: "What are the main points from https://example.com"
```

---

## Expected Benefits

### Clipboard Management
- ✅ Instant text summarization from any source
- ✅ Grammar/spelling fixes without retyping
- ✅ Translation of copied text
- ✅ Save AI responses directly to clipboard

### Active Window Context
- ✅ LLM knows what you're working on
- ✅ Context-aware help (VS Code vs Chrome vs Word)
- ✅ No need to explain "I'm in Excel" every time

### Web Scraping
- ✅ Research assistant for articles/blogs
- ✅ Quick summaries without leaving voice chat
- ✅ Multi-article comparison
- ✅ Fact-checking and verification

---

## Total Time Breakdown

| Phase | Time |
|-------|------|
| Setup dependencies | 5 min |
| Clipboard (impl + schema + registry) | 17 min |
| Window context (impl + schema + registry) | 15 min |
| Web scraping (impl + schema + registry) | 20 min |
| Testing all features | 15 min |
| **TOTAL** | **~72 min** |

---

## Priority Order

**Do first (30 min):**
1. ✅ Setup dependencies
2. ✅ Clipboard management (MASSIVE value)
3. ✅ Active window context (Easy + useful)

**Do next (35 min):**
4. Web scraping
5. Testing

---

## Ready to Implement?

All three features are:
- ✅ Low code complexity
- ✅ High user value
- ✅ No complex dependencies
- ✅ Work on Windows
- ✅ Instant payoff

Start with clipboard management - it's the easiest 10-minute win!
