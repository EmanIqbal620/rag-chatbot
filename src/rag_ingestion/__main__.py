"""
Main ingestion pipeline that orchestrates crawling and extraction.
"""

import time
from typing import List, Tuple
from .crawler import Crawler, crawl_book_website
from .text_extractor import extract_text_from_url, validate_text_quality
from .logger import ingestion_logger, log_time
from config.settings import settings


class IngestionPipeline:
    """
    Main ingestion pipeline that orchestrates the crawling and extraction process.
    """

    def __init__(self):
        self.crawler = Crawler()
        self.processed_urls = set()

    def process_single_page(self, url: str) -> Tuple[str, bool]:
        """
        Process a single page: crawl and extract text.

        Args:
            url: The URL to process

        Returns:
            Tuple of (extracted_text, success_flag)
        """
        # Extract text from the URL
        text = extract_text_from_url(url)

        if not text:
            return "", False

        # Validate text quality
        validation = validate_text_quality(text)
        if not validation["valid"]:
            ingestion_logger.info(f"Text quality validation failed for {url}: {validation['reason']}")
            return "", False

        return text, True

    def run_ingestion(self, max_pages: int = None) -> List[Tuple[str, str]]:
        """
        Run the complete ingestion pipeline.

        Args:
            max_pages: Maximum number of pages to process. If None, process all discovered pages.

        Returns:
            List of tuples containing (url, extracted_text) for successfully processed pages
        """
        ingestion_logger.log_ingestion_start(settings.BOOK_BASE_URL)

        with log_time("Website crawling"):
            # Crawl the website to get all URLs
            urls = crawl_book_website(max_pages=max_pages)

        if not urls:
            ingestion_logger.log_ingestion_error(
                settings.BOOK_BASE_URL,
                "No URLs discovered during crawling"
            )
            return []

        ingestion_logger.info(f"Discovered {len(urls)} URLs to process")

        results = []
        start_time = time.time()

        for i, url in enumerate(urls):
            ingestion_logger.log_progress(
                i + 1,
                len(urls),
                f"Processing {url}"
            )

            try:
                text, success = self.process_single_page(url)
                if success:
                    results.append((url, text))
                    self.processed_urls.add(url)
                else:
                    ingestion_logger.info(f"Failed to process {url}")
            except Exception as e:
                ingestion_logger.log_extraction_error(url, str(e))

            # Be respectful to the server
            time.sleep(0.1)

        duration = time.time() - start_time
        ingestion_logger.log_ingestion_complete(
            settings.BOOK_BASE_URL,
            len(results),
            duration
        )

        return results

    def run_ingestion_for_urls(self, urls: List[str]) -> List[Tuple[str, str]]:
        """
        Run the ingestion pipeline for a specific list of URLs.

        Args:
            urls: List of URLs to process

        Returns:
            List of tuples containing (url, extracted_text) for successfully processed pages
        """
        results = []
        start_time = time.time()

        for i, url in enumerate(urls):
            ingestion_logger.log_progress(
                i + 1,
                len(urls),
                f"Processing {url}"
            )

            try:
                text, success = self.process_single_page(url)
                if success:
                    results.append((url, text))
                    self.processed_urls.add(url)
                else:
                    ingestion_logger.info(f"Failed to process {url}")
            except Exception as e:
                ingestion_logger.log_extraction_error(url, str(e))

            # Be respectful to the server
            time.sleep(0.1)

        duration = time.time() - start_time
        ingestion_logger.info(f"Ingestion completed for {len(urls)} URLs, {len(results)} successful in {duration:.2f}s")

        return results


def run_ingestion_pipeline(max_pages: int = None) -> List[Tuple[str, str]]:
    """
    Convenience function to run the ingestion pipeline.

    Args:
        max_pages: Maximum number of pages to process. If None, process all discovered pages.

    Returns:
        List of tuples containing (url, extracted_text) for successfully processed pages
    """
    pipeline = IngestionPipeline()
    return pipeline.run_ingestion(max_pages)


if __name__ == "__main__":
    print("Starting RAG Book Ingestion Pipeline...")

    # Create pipeline instance
    pipeline = IngestionPipeline()

    # Run ingestion (limiting to 5 pages for testing)
    results = pipeline.run_ingestion(max_pages=5)

    print(f"\nIngestion completed! Successfully processed {len(results)} pages.")
    for url, text in results[:2]:  # Show first 2 results
        print(f"\nURL: {url}")
        print(f"Text length: {len(text)} characters")
        print(f"First 100 chars: {text[:100]}...")