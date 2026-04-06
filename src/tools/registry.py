"""Central tool registry and execution dispatcher."""

from src.tools.system_tools import (
    take_screenshot,
    get_clipboard,
    set_clipboard,
    get_active_window
)
from src.tools.web_tools import scrape_webpage
from src.tools.spotify_tools import (
    spotify_play,
    spotify_pause,
    spotify_skip_next,
    spotify_skip_previous,
    spotify_add_to_queue,
    spotify_current_track,
    spotify_shuffle,
    spotify_repeat,
    spotify_volume,
    spotify_like_current,
    spotify_unlike_current
)

# Central tool handler registry
TOOL_HANDLERS = {
    # System tools
    "take_screenshot": take_screenshot,
    "get_clipboard": get_clipboard,
    "set_clipboard": set_clipboard,
    "get_active_window": get_active_window,
    
    # Web tools
    "scrape_webpage": scrape_webpage,
    
    # Spotify tools
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_skip_next": spotify_skip_next,
    "spotify_skip_previous": spotify_skip_previous,
    "spotify_add_to_queue": spotify_add_to_queue,
    "spotify_current_track": spotify_current_track,
    "spotify_shuffle": spotify_shuffle,
    "spotify_repeat": spotify_repeat,
    "spotify_volume": spotify_volume,
    "spotify_like_current": spotify_like_current,
    "spotify_unlike_current": spotify_unlike_current
}


def execute_tool(tool_name, arguments):
    """
    Execute a tool by name with given arguments.
    
    Args:
        tool_name (str): Name of the tool to execute
        arguments (dict): Arguments to pass to the tool
    
    Returns:
        dict: Tool execution result with success status
    """
    if tool_name not in TOOL_HANDLERS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    try:
        handler = TOOL_HANDLERS[tool_name]
        return handler(**arguments)
    except Exception as e:
        return {"success": False, "error": f"Error executing {tool_name}: {str(e)}"}
