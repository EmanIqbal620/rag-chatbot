"""
Text extractor module for the RAG Book Ingestion Pipeline.
Extracts clean plain text from HTML content.
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple
import re
from config.settings import settings
from .logger import ingestion_logger


class TextExtractor:
    """
    Extracts clean plain text from HTML content, preserving important information
    like code snippets while removing HTML tags and unnecessary elements.
    """

    def __init__(self):
        # Common selectors for content areas in documentation sites
        self.content_selectors = [
            'main',
            'article',
            '.content',
            '.documentation-content',
            '.main-content',
            '#content',
            '.post-content',
            '.docs-content',
            '.markdown-body',
            '.doc-content'
        ]

        # Selectors for elements to remove (ads, navigation, etc.)
        self.remove_selectors = [
            'nav',
            'header',
            'footer',
            '.sidebar',
            '.menu',
            '.advertisement',
            '.ads',
            '.cookie-consent',
            '.social-share',
            '.comments',
            'script',
            'style',
            'noscript',
            '.hidden'
        ]

    def extract_text_from_html(self, html_content: str, url: str = "") -> str:
        """
        Extract clean text from HTML content.

        Args:
            html_content: The HTML content to extract text from
            url: The URL of the page (used for logging)

        Returns:
            str: Clean extracted text
        """
        ingestion_logger.log_extraction_start(url)

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove unwanted elements
            for selector in self.remove_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # Try to find content in specific selectors first
            content_element = None
            for selector in self.content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break

            # If no specific content area found, use the body
            if not content_element:
                content_element = soup.find('body') or soup

            # Extract text while preserving structure
            text = self._extract_text_with_structure(content_element)

            # Clean up the text
            text = self._clean_text(text)

            ingestion_logger.log_extraction_success(url, len(text))
            return text

        except Exception as e:
            ingestion_logger.log_extraction_error(url, str(e))
            return ""

    def _extract_text_with_structure(self, element) -> str:
        """
        Extract text while preserving some structure like headings and code.

        Args:
            element: BeautifulSoup element to extract text from

        Returns:
            str: Text with preserved structure
        """
        if element.name in ['script', 'style', 'meta', 'link']:
            return ""

        # Handle text nodes
        if isinstance(element, str):
            return element

        text_parts = []
        for content in element.contents:
            if isinstance(content, str):
                text_parts.append(content)
            else:
                # Handle code blocks specially
                if content.name in ['code', 'pre']:
                    code_text = self._extract_code_text(content)
                    text_parts.append(code_text)
                # Handle headings
                elif content.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    heading_text = content.get_text().strip()
                    if heading_text:
                        text_parts.append(f"\n{heading_text}\n")
                # Handle list items
                elif content.name in ['li', 'p']:
                    item_text = content.get_text().strip()
                    if item_text:
                        text_parts.append(f"\n{item_text}\n")
                # Handle other elements
                else:
                    text_parts.append(self._extract_text_with_structure(content))

        return "".join(text_parts)

    def _extract_code_text(self, element) -> str:
        """
        Extract code text while preserving formatting.

        Args:
            element: BeautifulSoup element containing code

        Returns:
            str: Formatted code text
        """
        code_text = element.get_text()
        # Add some formatting to distinguish code blocks
        return f"\n```\n{code_text}\n```\n"

    def _clean_text(self, text: str) -> str:
        """
        Clean up extracted text by removing extra whitespace and normalizing.

        Args:
            text: The raw extracted text

        Returns:
            str: Cleaned text
        """
        # Remove extra whitespace while preserving some structure
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Remove extra blank lines
        text = re.sub(r'[ \t]+', ' ', text)     # Normalize spaces
        text = text.strip()

        # Remove excessive newlines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text

    def extract_text_from_url(self, url: str) -> str:
        """
        Extract text directly from a URL.

        Args:
            url: The URL to extract text from

        Returns:
            str: Extracted text, or empty string if failed
        """
        try:
            response = requests.get(url, timeout=settings.REQUEST_TIMEOUT)
            response.raise_for_status()
            return self.extract_text_from_html(response.text, url)
        except requests.RequestException as e:
            ingestion_logger.log_extraction_error(url, str(e))
            return ""


def extract_text_from_html(html_content: str, url: str = "") -> str:
    """
    Convenience function to extract text from HTML content.

    Args:
        html_content: The HTML content to extract text from
        url: The URL of the page (used for logging)

    Returns:
        str: Clean extracted text
    """
    extractor = TextExtractor()
    return extractor.extract_text_from_html(html_content, url)


def extract_text_from_url(url: str) -> str:
    """
    Convenience function to extract text from a URL.

    Args:
        url: The URL to extract text from

    Returns:
        str: Extracted text, or empty string if failed
    """
    extractor = TextExtractor()
    return extractor.extract_text_from_url(url)


def validate_text_quality(text: str) -> Dict[str, any]:
    """
    Validate the quality of extracted text.

    Args:
        text: The text to validate

    Returns:
        Dict with validation results
    """
    if not text or len(text.strip()) == 0:
        return {
            "valid": False,
            "reason": "Text is empty or contains only whitespace",
            "length": len(text),
            "word_count": 0
        }

    # Count words
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    # Check for minimum content
    if word_count < 20:
        return {
            "valid": False,
            "reason": f"Text has only {word_count} words, less than minimum of 20",
            "length": len(text),
            "word_count": word_count
        }

    # Check for excessive repetition (potential scraping issue)
    if len(text) > 0:
        unique_chars_ratio = len(set(text)) / len(text)
        if unique_chars_ratio < 0.1:  # If less than 10% of characters are unique
            return {
                "valid": False,
                "reason": f"Text appears to have excessive repetition (unique chars ratio: {unique_chars_ratio:.2f})",
                "length": len(text),
                "word_count": word_count
            }

    return {
        "valid": True,
        "reason": "Text meets quality standards",
        "length": len(text),
        "word_count": word_count
    }


if __name__ == "__main__":
    # Test the text extractor
    print("Testing text extractor...")

    # Example HTML content for testing
    test_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Sample Documentation</h1>
            <p>This is a sample paragraph with some <strong>important</strong> text.</p>
            <pre><code>def hello_world():
    print("Hello, World!")
</code></pre>
            <p>Another paragraph with more content.</p>
        </body>
    </html>
    """

    extractor = TextExtractor()
    extracted_text = extractor.extract_text_from_html(test_html, "test_url")
    print("Extracted text:")
    print(extracted_text)

    # Validate the extracted text
    validation = validate_text_quality(extracted_text)
    print(f"\nValidation: {validation}")