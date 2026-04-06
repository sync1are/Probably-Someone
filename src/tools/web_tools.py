"""Web scraping and content extraction tools."""

import requests
from bs4 import BeautifulSoup


def scrape_webpage(url, extract_links=False):
    """
    Scrape and extract clean text content from a webpage.
    
    Args:
        url (str): The URL to scrape
        extract_links (bool): Whether to also extract links (default: False)
    
    Returns:
        dict: Success status with extracted content or error.
    """
    try:
        # Add headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        # Get page title
        title = soup.title.string if soup.title else "No title"
        
        result = {
            "success": True,
            "url": url,
            "content": text[:10000],  # Limit to 10k chars to avoid token overflow
            "title": title,
            "length": len(text),
            "truncated": len(text) > 10000,
            "message": f"Extracted {min(len(text), 10000)} characters from {title}"
        }
        
        if extract_links:
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            # Filter and clean links
            links = [link for link in links if link and link.startswith('http')]
            result['links'] = links[:50]  # Limit to 50 links
            result['link_count'] = len(links)
        
        return result
        
    except requests.RequestException as e:
        return {"success": False, "error": f"Failed to fetch URL: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
