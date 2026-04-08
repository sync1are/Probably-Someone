"""
News Fetching Tools
Provides access to latest headlines using Google News RSS feeds.
No API key required.
"""

from typing import Dict, Any
import urllib.parse

try:
    import feedparser
except ImportError:
    pass


def get_latest_news(topic: str = None, count: int = 5) -> Dict[str, Any]:
    """
    Fetch the latest news headlines from Google News.

    Args:
        topic (str, optional): A specific topic or keyword (e.g., "technology", "finance").
                               If None, fetches general top headlines.
        count (int): Number of headlines to return (default 5, max 10).

    Returns:
        dict: Success status and list of news headlines
    """
    try:
        count = min(max(1, count), 15)  # clamp between 1 and 15

        if topic:
            # URL encode the topic to make it safe
            safe_topic = urllib.parse.quote(topic)
            url = f"https://news.google.com/rss/search?q={safe_topic}&hl=en-US&gl=US&ceid=US:en"
            news_type = f"'{topic}'"
        else:
            # Top headlines
            url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
            news_type = "Top Headlines"

        # Fetch and parse the RSS feed
        feed = feedparser.parse(url)

        if not feed.entries:
            return {
                "success": False,
                "message": f"Could not find any recent news for {news_type}."
            }

        headlines = []
        for i, entry in enumerate(feed.entries[:count]):
            # Clean up the title (Google News sometimes appends the publisher name with a dash)
            title = entry.title

            # The summary sometimes contains HTML, so we just stick to the title for clean TTS
            headlines.append(f"{i+1}. {title}")

        formatted_headlines = "\n".join(headlines)

        return {
            "success": True,
            "message": f"Here are the latest {news_type} news.",
            "data": {
                "topic": topic,
                "count": len(headlines),
                "headlines": formatted_headlines
            },
            "summary": f"Here is the latest news for {news_type}:\n{formatted_headlines}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to fetch the latest news."
        }
