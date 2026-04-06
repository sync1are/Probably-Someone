# Spotify Commands Reference

## ✅ Instant Response (No API call to LLM)
These commands respond instantly without using LLM tokens:

- **"pause"** / **"pause music"** → Playback paused
- **"skip"** / **"next song"** → Skipped to next track
- **"previous"** / **"go back"** → Returned to previous track
- **"turn shuffle on"** → Shuffle enabled
- **"turn shuffle off"** → Shuffle disabled
- **"repeat this song"** → Repeat one track
- **"repeat all"** → Repeat all
- **"stop repeating"** → Repeat disabled
- **"set volume to 50"** → Volume set to 50%
- **"like this song"** / **"save this"** → Added to Liked Songs ❤️
- **"unlike this"** / **"remove this"** → Removed from Liked Songs

## 🎵 Natural Language Response (Uses LLM)
These commands use the LLM for natural, contextual responses:

### Play Commands
- **"play some jazz"** → Searches and plays jazz music
- **"play Charlie Puth"** → Plays artist's top tracks
- **"play the playlist Chill Vibes"** → Plays specific playlist
- **"play the album Purpose"** → Plays specific album
- **"play Bohemian Rhapsody"** → Plays specific track

### Queue & Info
- **"add this song to queue"** → Adds song to queue
- **"what's playing?"** → Shows current track info

## Content Types

The AI automatically detects what you want to play:

```
"play <artist name>" → Plays artist's top tracks
"play <song name>" → Plays the specific track
"play playlist <name>" → Plays the playlist
"play album <name>" → Plays the album
```

## Examples

```
You: pause
🤖 AI: Playback paused  [INSTANT]

You: play some 80s rock
🔧 Using tools...
  → Calling spotify_play...
  ✓ spotify_play completed
🤖 AI: Playing 'Sweet Child O' Mine' by Guns N' Roses

You: turn shuffle on
🤖 AI: Shuffle enabled  [INSTANT]

You: what's playing?
🔧 Using tools...
  → Calling spotify_current_track...
  ✓ spotify_current_track completed
🤖 AI: Playing: 'Sweet Child O' Mine' by Guns N' Roses

You: skip
🤖 AI: Skipped to next track  [INSTANT]

You: like this song
🤖 AI: Added 'Livin' On A Prayer' by Bon Jovi to Liked Songs  [INSTANT]
```
