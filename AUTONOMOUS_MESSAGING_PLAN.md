# Implementation Plan: ARIA Autonomous Messaging Mode

This document outlines the strategy for evolving ARIA's messaging system from a reactive "Auto-Reply" system into a proactive "Autonomous" system that can initiate and manage conversations independently.

## 1. Goal
To give ARIA the ability to proactively engage with whitelisted contacts on Discord and WhatsApp based on context, time, or specific goals, rather than just waiting for an incoming message.

## 2. Core Autonomous Features

### A. Proactive Initiation (The "Check-in")
*   **Logic:** ARIA monitors the time since the last interaction with a whitelisted contact. If a defined threshold is met (e.g., 24 hours), ARIA can initiate a "check-in" message.
*   **Context Awareness:** The initiation is not generic. It uses the last conversation's summary to create a relevant follow-up.
    *   *Example:* "Hey [Name], how did that presentation go yesterday?"

### B. Goal-Oriented Task Execution
*   **Logic:** If the user gives ARIA a task via the main app (e.g., "Remind John about the meeting"), ARIA autonomously messages John and waits for a confirmation before reporting back to the user.
*   **Multi-turn handling:** ARIA manages the back-and-forth until the goal is achieved.

### C. Contextual "Ghost Mode" (Subtle Presence)
*   **Logic:** ARIA can "lurk" in whitelisted Discord channels and only intervene if its specific expertise is needed or if it's mentioned in a way that implies it should help.

## 3. Architecture Changes

### New Component: `src/messaging/autonomy_engine.py`
This new module will act as the "Proactive Brain":
*   **Interaction Tracker:** Monitors `last_message_time` for all whitelisted contacts.
*   **Scheduler:** Uses `apscheduler` or a simple background loop to trigger initiation checks.
*   **Goal Manager:** Tracks active "outbound tasks" assigned by the user.

### Enhancements to `src/messaging/controller.py`
*   Add `initiate_conversation(platform, contact_id, context)` method.
*   Integrate with the `AutonomyEngine` to receive triggers for outbound messages.

## 4. Implementation Roadmap

### Phase 1: Interaction Tracking
1.  Update `src/messaging/controller.py` to persist `last_interaction_timestamp` and a brief `context_summary` for each whitelisted contact in a local JSON database.

### Phase 2: The Autonomy Engine
1.  Create `src/messaging/autonomy_engine.py`.
2.  Implement a background heartbeat that checks for "stale" conversations that need a proactive follow-up.

### Phase 3: Outbound Tooling
1.  Add new tools to `tools.json` and `messaging_tools.py`:
    *   `send_proactive_message(contact_name, platform, message_goal)`
    *   `set_autonomous_checkin(contact_name, frequency_hours)`

### Phase 4: Feedback Loop
1.  Ensure ARIA reports back to the main app's TTS when an autonomous goal is completed.
    *   *Example:* ARIA voice: "I've checked in with John, he said he'll be at the meeting."

## 5. Safety & Etiquette Controls
*   **Max Initiations:** Limit autonomous initiations to once per 24 hours per contact.
*   **Do Not Disturb:** Honor a global "Quiet Mode" where ARIA will not initiate any outbound messages.
*   **User Confirmation:** For high-stakes messages, ARIA will ask the user: "Should I check in with Sarah about the project?" before sending.
