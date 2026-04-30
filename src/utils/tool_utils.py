import toml
from src.config import TOOLS_FILE

def load_tools():
    """Load tool definitions from tools.toml."""
    try:
        with open(TOOLS_FILE, 'r', encoding='utf-8') as f:
            tools_data = toml.load(f)
            tools = tools_data.get('tools', [])
            for t in tools:
                if 'function' in t and 'parameters' in t['function']:
                    if 'properties' not in t['function']['parameters']:
                        t['function']['parameters']['properties'] = {}
            return tools
    except FileNotFoundError:
        print(f"Warning: {TOOLS_FILE} not found.")
        return []
    except Exception as e:
        print(f"Error loading tools: {e}")
        return []
