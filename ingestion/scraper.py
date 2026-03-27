import requests
from bs4 import BeautifulSoup
from typing import List, Dict

def scrape_url(url: str) -> Dict:
    """Scrape a single URL and return clean text."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise elements
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()

        title = soup.find("title")
        page_title = title.get_text(strip=True) if title else url

        # Get main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        raw_text = main.get_text(separator="\n", strip=True) if main else ""

        return {"url": url, "title": page_title, "raw_text": raw_text}
    except Exception as e:
        print(f"[SCRAPER ERROR] {url}: {e}")
        return {"url": url, "title": "", "raw_text": ""}

def scrape_urls(urls: List[str]) -> List[Dict]:
    return [scrape_url(u) for u in urls if u.strip()]
