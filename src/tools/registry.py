"""Central tool registry and execution dispatcher."""

from src.tools.system_tools import take_screenshot
from src.tools.spotify_tools import (
    spotify_play,
    spotify_pause,
    spotify_skip_next,
    spotify_skip_previous,
    spotify_add_to_queue,
    spotify_current_track
)

# Central tool handler registry
TOOL_HANDLERS = {
    "take_screenshot": take_screenshot,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_skip_next": spotify_skip_next,
    "spotify_skip_previous": spotify_skip_previous,
    "spotify_add_to_queue": spotify_add_to_queue,
    "spotify_current_track": spotify_current_track
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
