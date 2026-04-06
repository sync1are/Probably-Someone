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
        scope="user-modify-playback-state user-read-playback-state user-read-currently-playing user-library-modify user-library-read"
    ))


def spotify_play(query=None, content_type="track"):
    """
    Play a specific song, artist, playlist, or album, or resume playback.
    
    Args:
        query (str, optional): Search query for a track/playlist/album. If None, resumes current playback.
        content_type (str): Type of content to search for: "track", "playlist", "album", "artist"
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        if query:
            # Search for the content
            results = sp.search(q=query, limit=1, type=content_type)
            
            if content_type == 'track' and results['tracks']['items']:
                track = results['tracks']['items'][0]
                sp.start_playback(uris=[track['uri']])
                return {
                    "success": True,
                    "message": f"Playing '{track['name']}' by {track['artists'][0]['name']}"
                }
            elif content_type == 'playlist' and results['playlists']['items']:
                playlist = results['playlists']['items'][0]
                sp.start_playback(context_uri=playlist['uri'])
                return {
                    "success": True,
                    "message": f"Playing playlist '{playlist['name']}'"
                }
            elif content_type == 'album' and results['albums']['items']:
                album = results['albums']['items'][0]
                sp.start_playback(context_uri=album['uri'])
                return {
                    "success": True,
                    "message": f"Playing album '{album['name']}' by {album['artists'][0]['name']}"
                }
            elif content_type == 'artist' and results['artists']['items']:
                artist = results['artists']['items'][0]
                # Get artist's top tracks
                top_tracks = sp.artist_top_tracks(artist['id'])
                if top_tracks['tracks']:
                    track_uris = [track['uri'] for track in top_tracks['tracks'][:10]]
                    sp.start_playback(uris=track_uris)
                    return {
                        "success": True,
                        "message": f"Playing top tracks from {artist['name']}"
                    }
            
            return {"success": False, "error": f"No {content_type} found for '{query}'"}
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


def spotify_shuffle(state):
    """
    Enable or disable shuffle mode.
    
    Args:
        state (bool): True to enable shuffle, False to disable
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        sp.shuffle(state)
        return {
            "success": True,
            "message": f"Shuffle {'enabled' if state else 'disabled'}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_repeat(state):
    """
    Set repeat mode.
    
    Args:
        state (str): "track" for repeat one, "context" for repeat all, "off" for no repeat
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        sp.repeat(state)
        state_text = {
            "track": "Repeat one track",
            "context": "Repeat all",
            "off": "Repeat disabled"
        }.get(state, "Repeat mode updated")
        
        return {
            "success": True,
            "message": state_text
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_volume(volume_percent):
    """
    Set playback volume.
    
    Args:
        volume_percent (int): Volume level from 0 to 100
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        volume_percent = max(0, min(100, volume_percent))
        sp.volume(volume_percent)
        return {
            "success": True,
            "message": f"Volume set to {volume_percent}%"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_like_current():
    """
    Like/save the currently playing track to library.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        current = sp.current_playback()
        if current and current.get('item'):
            track = current['item']
            track_id = track['id']
            
            # Check if already liked
            is_liked = sp.current_user_saved_tracks_contains([track_id])[0]
            
            if is_liked:
                return {
                    "success": True,
                    "message": f"'{track['name']}' is already in your Liked Songs",
                    "already_liked": True
                }
            
            sp.current_user_saved_tracks_add([track_id])
            return {
                "success": True,
                "message": f"Added '{track['name']}' by {track['artists'][0]['name']} to Liked Songs"
            }
        return {"success": False, "error": "No track currently playing"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def spotify_unlike_current():
    """
    Unlike/remove the currently playing track from library.
    
    Returns:
        dict: Success status and message or error.
    """
    sp = get_spotify_client()
    try:
        current = sp.current_playback()
        if current and current.get('item'):
            track = current['item']
            track_id = track['id']
            
            # Check if liked
            is_liked = sp.current_user_saved_tracks_contains([track_id])[0]
            
            if not is_liked:
                return {
                    "success": True,
                    "message": f"'{track['name']}' is not in your Liked Songs",
                    "not_liked": True
                }
            
            sp.current_user_saved_tracks_delete([track_id])
            return {
                "success": True,
                "message": f"Removed '{track['name']}' from Liked Songs"
            }
        return {"success": False, "error": "No track currently playing"}
    except Exception as e:
        return {"success": False, "error": str(e)}
