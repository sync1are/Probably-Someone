# Implementation Plan: "USER MESSAGES" Feature

This document outlines the strategy for implementing a "Message Taker" feature. When ARIA is in Autonomous mode, she will recognize messages intended for the actual user (the owner), store them, and report them as soon as the user returns to the app.

## 1. Goal
To enable ARIA to act as a digital secretary that intercepts and logs specific requests from whitelisted contacts (e.g., "Tell him to call me") and delivers them to the user upon their return.

## 2. Component Architecture

### A. Storage: `messaging/pending_user_messages.json`
A new persistent storage file to keep track of messages that haven't been seen by the user yet.
```json
{
  "pending_count": 2,
  "messages": [
    {
      "platform": "whatsapp",
      "from": "+1234567890",
      "name": "Anas",
      "content": "Tell him to call me when he's free",
      "timestamp": 1712654400
    }
  ]
}
```

### B. Detection: The `store_user_message` Tool
Instead of just relying on text matching, we will give the LLM a specific tool to "take a memo."
*   **Tool Name:** `store_user_message`
*   **Parameters:** `contact_name`, `platform`, `message_content`.
*   **Logic:** When the LLM decides a message is meant for the owner, it calls this tool.

### C. Delivery: The "Welcome Back" Routine
Update the main entry point (`app.py`) to check for pending messages.
*   **Trigger 1 (Startup):** Immediately after "🤖 ARIA Voice Assistant Started!", check the JSON and read out the count.
*   **Trigger 2 (Inactivity):** If the user hasn't typed anything for > 30 mins and then speaks, ARIA should say: "Welcome back! While you were away, you received 2 messages..."

## 3. Implementation Roadmap

### Phase 1: Storage & Tools
1.  Add `store_user_message` to `tools.json`.
2.  Implement the logic in `src/tools/messaging_tools.py` to write to `pending_user_messages.json`.
3.  Add a companion tool `get_pending_messages` to retrieve and clear them.

### Phase 2: AI Brain Update
1.  Update the `ResponseGenerator` (or the specific messaging prompt) to instruct the AI: 
    > "If a contact asks you to tell the owner something, or leave a message for him, DO NOT just say 'Okay'. Use the `store_user_message` tool to log it."

### Phase 3: `app.py` Integration
1.  Create a `check_for_user_messages()` function in `app.py`.
2.  Call this function during the startup sequence.
3.  Implement a simple "Return Detection" logic that triggers if the time since the last `user_input` is significant.

### Phase 4: Voice Reporting
1.  Ensure the delivery of these messages uses the `AudioEngine` so the user *hears* their messages immediately upon return.

## 4. Example Workflow
1.  **Friend (WhatsApp):** "Hey, tell him I'll be late for the gym."
2.  **ARIA (Autonomous):** Calls `store_user_message(name="John", platform="whatsapp", content="He'll be late for the gym")`.
3.  **ARIA (Reply to Friend):** "I've noted that down and will let him know as soon as he's back!"
4.  **User (Later, opens app):** "Hey Aria."
5.  **ARIA (Audio):** "Welcome back. You have one new message from John on WhatsApp: 'He'll be late for the gym'. How can I help you now?"
