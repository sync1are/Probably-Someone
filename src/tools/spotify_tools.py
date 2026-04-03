"""Spotify playback control tools using Spotify Web API."""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from src.config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI


def get_spotify_client():
    """Initialize and return authenticated Spotify client."""
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-modify-playback-state user-read-playback-state user-read-currently-playing"
    ))


def spotify_play(query=None):
    """
    Play a specific song, artist, or playlist, or resume playback.
    
    Args:
        query (str, optional): Search query for a track. If None, resumes current playback.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        if query:
            # Search for the track
            results = sp.search(q=query, limit=1, type='track')
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                sp.start_playback(uris=[track['uri']])
                return {
                    "success": True,
                    "message": f"Playing '{track['name']}' by {track['artists'][0]['name']}"
                }
            return {"success": False, "error": "Track not found"}
        else:
            # Resume current playback
            sp.start_playback()
            return {"success": True, "message": "Resumed playback"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_pause():
    """
    Pause the current playback.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        sp.pause_playback()
        return {"success": True, "message": "Playback paused"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_skip_next():
    """
    Skip to the next track in the queue.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        sp.next_track()
        return {"success": True, "message": "Skipped to next track"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_skip_previous():
    """
    Go back to the previous track.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        sp.previous_track()
        return {"success": True, "message": "Returned to previous track"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_add_to_queue(query):
    """
    Search for a song and add it to the playback queue.
    
    Args:
        query (str): Search query for the track to add.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        results = sp.search(q=query, limit=1, type='track')
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            sp.add_to_queue(track['uri'])
            return {
                "success": True,
                "message": f"Added '{track['name']}' by {track['artists'][0]['name']} to queue"
            }
        return {"success": False, "error": "Track not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_current_track():
    """
    Get information about the currently playing track.
    
    Returns:
        dict: Success status with track info or error.
    """
    sp = get_spotify_client()
    try:
        current = sp.current_playback()
        if current and current.get('item'):
            track = current['item']
            is_playing = current['is_playing']
            artists = ', '.join([artist['name'] for artist in track['artists']])
            
            return {
                "success": True,
                "message": f"{'Playing' if is_playing else 'Paused'}: '{track['name']}' by {artists}",
                "track_name": track['name'],
                "artists": artists,
                "is_playing": is_playing,
                "progress_ms": current.get('progress_ms', 0),
                "duration_ms": track.get('duration_ms', 0)
            }
        return {"success": False, "error": "No track currently playing"}
    except Exception as e:
        return {"success": False, "error": str(e)}
