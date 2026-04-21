import os
import toml
import urllib.parse

LEARNED_URLS_FILE = "learned_urls.toml"

def _load_urls():
    if not os.path.exists(LEARNED_URLS_FILE):
        return {"urls": {}}
    try:
        with open(LEARNED_URLS_FILE, 'r', encoding='utf-8') as f:
            return toml.load(f)
    except Exception:
        return {"urls": {}}

def _save_urls(data):
    with open(LEARNED_URLS_FILE, 'w', encoding='utf-8') as f:
        toml.dump(data, f)

def save_search_template(domain: str, url_template: str) -> dict:
    """
    Save a URL template for a specific domain. The template MUST contain '{query}'.
    Example: save_search_template("youtube.com", "https://youtube.com/results?search_query={query}")
    """
    if "{query}" not in url_template:
        return {"success": False, "error": "The url_template must contain the literal string '{query}' so it can be replaced later."}
    
    data = _load_urls()
    if "urls" not in data:
        data["urls"] = {}
        
    domain = domain.lower().replace("www.", "")
    data["urls"][domain] = url_template
    _save_urls(data)
    
    return {"success": True, "message": f"Successfully learned search pattern for {domain}."}

def get_learned_search_url(domain: str, query: str) -> dict:
    """
    Get a formatted search URL for a domain if it has been learned previously.
    Returns the exact URL to navigate to, or an error if the domain is not known.
    """
    data = _load_urls()
    domain = domain.lower().replace("www.", "")
    
    urls = data.get("urls", {})
    if domain in urls:
        template = urls[domain]
        # URL encode the query
        encoded_query = urllib.parse.quote_plus(query)
        final_url = template.replace("{query}", encoded_query)
        return {"success": True, "url": final_url}
        
    return {"success": False, "error": f"No learned template for {domain}. You must navigate manually and then save the template."}
