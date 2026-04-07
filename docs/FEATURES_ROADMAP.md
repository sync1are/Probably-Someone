# 🚀 ARIA System Features Roadmap

Comprehensive list of system-level features to be implemented one by one.

---

## ⚠️ **Important Design Decisions**

### Media Control Conflicts
**Question:** System-level "next track" vs Spotify controls - how to handle conflicts?

**Answer:** Implement priority-based media control:

1. **Explicit Platform Commands** (Highest Priority)
   - "Next track on Spotify" → Only controls Spotify
   - "Pause YouTube" → Only controls YouTube
   - "Volume on Discord" → Only Discord volume

2. **Smart Context Detection** (Medium Priority)
   - Check which media is currently active/focused
   - Prioritize: Spotify > YouTube > Browser > System
   - "Next track" → Goes to the currently playing app

3. **Multiple Media Playing** (Conflict Resolution)
   ```
   If multiple media playing:
   - "Pause" → Pause ALL
   - "Next track" → Control the FOCUSED app
   - "What's playing?" → List all active media
   - "Pause Spotify" → Specific control
   ```

4. **Implementation Strategy**
   ```python
   def get_active_media():
       """Returns list of currently playing media sources"""
       active = []
       if spotify_is_playing(): active.append('spotify')
       if youtube_is_playing(): active.append('youtube')
       if system_media_playing(): active.append('system')
       return active
   
   def smart_media_control(action, target=None):
       if target:  # Explicit: "pause spotify"
           control_specific(target, action)
       else:  # Implicit: "pause"
           active_media = get_active_media()
           if len(active_media) == 1:
               control_specific(active_media[0], action)
           elif len(active_media) > 1:
               # Get focused window or ask user
               focused = get_focused_media_app()
               control_specific(focused, action)
   ```

**Decision:** Keep existing Spotify tools, add system-level as separate tools with smart routing.

---

## 📋 **Feature Categories**

### Priority 1: Quick Wins (Implement First)
- [x] WhatsApp & Discord Messaging ✅
- [x] Window Management ✅
- [x] App Launcher ✅
- [x] System Audio Control ✅
- [ ] File Operations (Basic)

### Priority 2: Productivity
- [ ] Reminders & Timers
- [ ] Task Management
- [ ] Calendar Integration
- [ ] Context Awareness

### Priority 3: Advanced
- [ ] Web Automation
- [ ] Email Integration
- [ ] Meeting Assistant
- [ ] Smart Automation

---

## 🖥️ **1. Window Management**

### Description
Control application windows through voice commands.

### Commands
```
"Minimize this window"
"Maximize Chrome"
"Close Spotify"
"Switch to VS Code"
"Show all windows"
"Hide all windows" (show desktop)
```

### Implementation
- Use `pygetwindow` library
- Find window by title/process name
- Perform operations: minimize, maximize, close, focus

### Conflicts
- None - pure window management

### Priority
⭐⭐⭐⭐⭐ High (Quick win)

---

## 🚀 **2. App Launcher**

### Description
Launch applications by name.

### Commands
```
"Open Chrome"
"Launch VS Code"
"Start Discord"
"Run Notepad"
"Open File Explorer"
```

### Implementation
- Windows: `os.startfile()` or registry lookup
- Use known paths for common apps
- Search PATH environment variable
- Fallback to Start Menu search

### Conflicts
- None

### Priority
⭐⭐⭐⭐⭐ High (Quick win)

---

## 🔊 **3. System Audio Control**

### Description
Control system-wide audio levels and media playback.

### Commands
```
"Volume to 50%"
"Increase volume"
"Decrease volume"
"Mute"
"Unmute"
"Next track" (system-wide)
"Pause" (system-wide)
"Play" (system-wide)
```

### Implementation
```python
# Volume control
import pycaw  # Windows audio control

# Media keys
import keyboard  # Send media key presses

def system_media_control(action):
    """
    Priority order:
    1. Check if Spotify is playing → use spotify tools
    2. Check if YouTube/browser has media → control that
    3. Fallback to system media keys
    """
    if is_spotify_active():
        return spotify_control(action)
    elif is_browser_media_active():
        return browser_media_control(action)
    else:
        return system_media_keys(action)
```

### Conflict Resolution
**Explicit commands:**
- "Next on Spotify" → `spotify_skip_next()`
- "Pause YouTube" → Browser automation
- "System volume to 50%" → System audio

**Implicit commands:**
- "Next track" → Smart detection (see above)
- "Pause" → Smart detection or pause ALL

### Priority
⭐⭐⭐⭐ Medium-High

---

## 📁 **4. File Operations**

### Description
Create, delete, move, copy, and search files through voice.

### Commands
```
"Create file called notes.txt"
"Delete this file"
"Move document.pdf to Downloads"
"Copy file to Desktop"
"Rename this to project_v2.txt"
"What files are in this folder?"
"Search for files named report"
```

### Implementation
- Use `pathlib` for file operations
- Safety checks (no system file deletion)
- Confirmation for destructive operations
- Work in user directories only

### Conflicts
- None

### Priority
⭐⭐⭐⭐ Medium-High

---

## ⏰ **5. Reminders & Timers**

### Description
Set voice-activated reminders and timers.

### Commands
```
"Remind me in 30 minutes to call Mom"
"Set a timer for 25 minutes"
"Cancel all timers"
"What reminders do I have?"
"Snooze this reminder"
```

### Implementation
- Use Python `schedule` library
- Store reminders in JSON
- TTS notification when timer expires
- Background thread for checking

### Conflicts
- None

### Priority
⭐⭐⭐⭐⭐ High (Very useful)

---

## ✅ **6. Task Management**

### Description
Voice-based to-do list management.

### Commands
```
"Add task: finish project report"
"Mark task as done"
"Show my to-do list"
"Delete task 3"
"What's my priority for today?"
```

### Implementation
- Store tasks in JSON
- Priority levels (high, medium, low)
- Due dates
- Categories/tags

### Conflicts
- None

### Priority
⭐⭐⭐ Medium

---

## 📅 **7. Calendar Integration**

### Description
Connect to Google Calendar or Outlook.

### Commands
```
"What's on my calendar today?"
"Add meeting at 3pm tomorrow"
"When is my next appointment?"
"Cancel tomorrow's 2pm meeting"
```

### Implementation
- Google Calendar API
- Microsoft Graph API (Outlook)
- OAuth authentication
- Event CRUD operations

### Conflicts
- None

### Priority
⭐⭐⭐ Medium

---

## 🌐 **8. Web Automation**

### Description
Control browser and perform web searches.

### Commands
```
"Open YouTube and search for tutorials"
"Google 'Python best practices'"
"Open my Gmail"
"Search Amazon for headphones"
```

### Implementation
- Use `webbrowser` module
- Selenium for advanced automation
- URL templating for searches

### Conflicts
- None

### Priority
⭐⭐⭐ Medium

---

## 🖥️ **9. System Information**

### Description
Query system stats and information.

### Commands
```
"What's my CPU usage?"
"How much RAM am I using?"
"Show disk space"
"What's the battery level?"
"Network speed test"
"List running processes"
```

### Implementation
- Use `psutil` library
- Real-time system monitoring
- Battery info (laptops)
- Network stats

### Conflicts
- None

### Priority
⭐⭐ Low-Medium

---

## 🔒 **10. Power Management**

### Description
Lock, sleep, shutdown, restart computer.

### Commands
```
"Lock the computer"
"Put computer to sleep"
"Restart in 5 minutes"
"Shutdown when done"
"Cancel shutdown"
```

### Implementation
- Windows: `os.system('shutdown /s /t 300')`
- Lock: `ctypes.windll.user32.LockWorkStation()`
- Sleep: Power management APIs

### Conflicts
- None

### Security
⚠️ Requires confirmation for destructive actions

### Priority
⭐⭐ Low-Medium

---

## 🧠 **11. Context Awareness**

### Description
Track and recall what you were working on.

### Commands
```
"What was I working on yesterday?"
"Show me files I edited today"
"What apps did I use most this week?"
"Summarize my day"
```

### Implementation
- File access monitoring
- Window focus tracking
- Activity logging (privacy-conscious)
- SQLite database for history

### Conflicts
- None

### Privacy
⚠️ User must opt-in, data stored locally only

### Priority
⭐⭐⭐⭐ Medium-High (Advanced feature)

---

## 📧 **12. Email Integration**

### Description
Read and send emails through voice.

### Commands
```
"Read my latest email"
"Send email to John"
"How many unread emails?"
"Search emails for 'invoice'"
```

### Implementation
- Gmail API
- Outlook API
- IMAP/SMTP fallback
- OAuth authentication

### Conflicts
- None

### Priority
⭐⭐⭐ Medium

---

## 🎙️ **13. Meeting Assistant**

### Description
Record, transcribe, and summarize meetings.

### Commands
```
"Start recording this meeting"
"Take notes from this call"
"Transcribe what they're saying"
"Summarize this meeting"
```

### Implementation
- Audio recording with `sounddevice`
- Whisper API for transcription
- LLM for summarization
- Save to markdown

### Conflicts
- Audio device conflicts (needs testing)

### Priority
⭐⭐⭐ Medium (Advanced)

---

## 🤖 **14. Smart Automation**

### Description
IFTTT-style automation rules.

### Commands
```
"When I say 'work mode', close social media apps"
"If battery below 20%, enable power saving"
"Auto-reply to emails when I'm busy"
```

### Implementation
- Trigger-action system
- Condition evaluation
- Save rules to JSON
- Background monitoring

### Conflicts
- None (but needs testing)

### Priority
⭐⭐ Low-Medium (Future)

---

## 📊 **15. Personal Analytics**

### Description
Track and visualize productivity metrics.

### Commands
```
"How much time did I spend on Chrome today?"
"Show my productivity stats"
"What's my screen time?"
```

### Implementation
- Activity tracking
- Data visualization
- Weekly reports
- Export to CSV

### Conflicts
- None

### Privacy
⚠️ Opt-in, local storage only

### Priority
⭐⭐ Low-Medium

---

## 🔧 **Implementation Order**

### Phase 1: Foundation (Week 1-2)
1. Window Management ✅ Completed
2. App Launcher ✅ Completed
3. System Audio Control ✅ Completed

### Phase 2: Productivity (Week 3-4)
4. File Operations
5. Reminders & Timers
6. Task Management

### Phase 3: Integration (Week 5-6)
7. Calendar Integration
8. Web Automation
9. System Information

### Phase 4: Advanced (Week 7+)
10. Context Awareness
11. Email Integration
12. Meeting Assistant

### Phase 5: Future
13. Smart Automation
14. Personal Analytics
15. Power Management

---

## 🎯 **Conflict Resolution Summary**

### Media Control Matrix

| Command | Spotify Playing | YouTube Playing | Both Playing | Nothing Playing |
|---------|----------------|-----------------|--------------|----------------|
| "Pause" | Pause Spotify | Pause YouTube | Pause focused app | No-op |
| "Next" | Spotify next | YouTube next | Focused app next | No-op |
| "Pause Spotify" | Pause Spotify | No-op | Pause Spotify | No-op |
| "Pause all" | Pause Spotify | Pause YouTube | Pause both | No-op |

### Window Focus Priority
1. User-specified app (explicit)
2. Currently focused window
3. Most recently used
4. Ask user to clarify

---

## 📝 **Notes**

- All features should work offline when possible
- Privacy-first: no data leaves the machine
- Confirmation required for destructive actions
- Voice feedback for all operations
- Fallback to text if voice fails

---

## 🔄 **Status Legend**
- [ ] Not started
- [🔨] In progress
- [✅] Completed
- [⏸️] Paused
- [❌] Cancelled

---

**Last Updated:** 2026-04-07
**Next Feature:** Window Management
