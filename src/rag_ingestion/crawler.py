"""
Crawler module for the RAG Book Ingestion Pipeline.
Handles crawling the humanoid robotics textbook website and extracting URLs.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set
import time
import logging
from config.settings import settings
from .logger import ingestion_logger


class Crawler:
    """
    A web crawler for extracting URLs from the humanoid robotics textbook website.
    """

    def __init__(self, base_url: str = None):
        """
        Initialize the crawler.

        Args:
            base_url: The base URL to crawl. If None, uses settings.BOOK_BASE_URL
        """
        self.base_url = base_url or settings.BOOK_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()

    def is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is valid for crawling.

        Args:
            url: The URL to validate

        Returns:
            bool: True if the URL is valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.base_url)

            # Check if the URL is from the same domain
            if parsed.netloc != base_parsed.netloc:
                return False

            # Check if it's an HTML page
            if parsed.path.endswith(('.html', '.htm', '/')):
                return True

            # If no extension, assume it's HTML
            if '.' not in parsed.path.split('/')[-1]:
                return True

            return False
        except Exception:
            return False

    def get_page_content(self, url: str) -> str:
        """
        Fetch the content of a single page.

        Args:
            url: The URL to fetch

        Returns:
            str: The content of the page, or empty string if failed
        """
        try:
            response = self.session.get(url, timeout=settings.REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            ingestion_logger.log_crawl_error(url, str(e))
            return ""

    def extract_links(self, html_content: str, base_url: str) -> List[str]:
        """
        Extract all links from HTML content.

        Args:
            html_content: The HTML content to parse
            base_url: The base URL for resolving relative links

        Returns:
            List[str]: List of extracted URLs
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        links = []

        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            if self.is_valid_url(full_url):
                links.append(full_url)

        return links

    def crawl_single_page(self, url: str) -> List[str]:
        """
        Crawl a single page and extract links.

        Args:
            url: The URL to crawl

        Returns:
            List[str]: List of discovered URLs on this page
        """
        if url in self.visited_urls:
            return []

        self.visited_urls.add(url)
        ingestion_logger.log_crawl_start(url)

        content = self.get_page_content(url)
        if not content:
            return []

        content_length = len(content)
        ingestion_logger.log_crawl_success(url, content_length)

        discovered_links = self.extract_links(content, url)
        return discovered_links

    def crawl(self, max_pages: int = None) -> List[str]:
        """
        Crawl the website starting from the base URL.

        Args:
            max_pages: Maximum number of pages to crawl. If None, crawl all accessible pages.

        Returns:
            List[str]: List of all discovered URLs
        """
        # Start with the base URL
        urls_to_visit = [self.base_url]
        page_count = 0

        while urls_to_visit and (max_pages is None or page_count < max_pages):
            current_url = urls_to_visit.pop(0)

            if current_url in self.visited_urls:
                continue

            discovered_links = self.crawl_single_page(current_url)

            # Add new links to visit if they haven't been visited or queued
            for link in discovered_links:
                if link not in self.visited_urls and link not in urls_to_visit:
                    urls_to_visit.append(link)
                    self.discovered_urls.add(link)

            page_count += 1

            # Log progress
            if page_count % 10 == 0:
                ingestion_logger.log_progress(
                    page_count,
                    len(self.visited_urls) + len(urls_to_visit),
                    f"Crawled {page_count} pages so far"
                )

            # Be respectful to the server
            time.sleep(0.1)

        return list(self.discovered_urls)

    def crawl_from_sitemap(self) -> List[str]:
        """
        Try to crawl from a sitemap if available.

        Returns:
            List[str]: List of URLs from the sitemap, or empty list if no sitemap found
        """
        sitemap_url = urljoin(self.base_url, 'sitemap.xml')
        content = self.get_page_content(sitemap_url)

        if content:
            # Parse sitemap XML
            soup = BeautifulSoup(content, 'xml')  # Use XML parser for sitemaps
            urls = []
            for loc in soup.find_all('loc'):
                url = loc.get_text().strip()
                if self.is_valid_url(url):
                    urls.append(url)
            return urls

        return []


def crawl_book_website(base_url: str = None, max_pages: int = None) -> List[str]:
    """
    Convenience function to crawl the book website.

    Args:
        base_url: The base URL to crawl. If None, uses settings.BOOK_BASE_URL
        max_pages: Maximum number of pages to crawl. If None, crawl all accessible pages.

    Returns:
        List[str]: List of all discovered URLs
    """
    crawler = Crawler(base_url)

    # First try to get URLs from sitemap
    sitemap_urls = crawler.crawl_from_sitemap()

    if sitemap_urls:
        # If sitemap exists, use those URLs
        all_urls = sitemap_urls
        for url in sitemap_urls:
            crawler.visited_urls.add(url)
    else:
        # If no sitemap, crawl normally starting from base URL
        all_urls = crawler.crawl(max_pages)

    return all_urls


if __name__ == "__main__":
    # Test the crawler
    print("Testing crawler...")
    urls = crawl_book_website()
    print(f"Discovered {len(urls)} URLs:")
    for i, url in enumerate(urls[:10]):  # Show first 10 URLs
        print(f"  {i+1}. {url}")
    if len(urls) > 10:
        print(f"  ... and {len(urls) - 10} more URLs")