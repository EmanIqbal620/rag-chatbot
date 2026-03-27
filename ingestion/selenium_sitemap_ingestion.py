import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import List
import cohere
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
import tiktoken
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SeleniumSitemapIngestion:
    def __init__(self, sitemap_url: str, cohere_api_key: str = None, qdrant_url: str = None, qdrant_api_key: str = None):
        self.sitemap_url = sitemap_url
        self.cohere_client = cohere.Client(cohere_api_key) if cohere_api_key else None
        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key) if qdrant_url else QdrantClient(host="localhost", port=6333)
        self.enc = tiktoken.get_encoding("cl100k_base")  # For token counting

        # Create Qdrant collection if it doesn't exist
        self.collection_name = "humanoid_ai_book"
        self._setup_qdrant_collection()

        # Set up Selenium driver
        self.driver = self._create_selenium_driver()

    def _setup_qdrant_collection(self):
        """Set up the Qdrant collection for storing embeddings"""
        try:
            # Check if collection exists
            self.qdrant_client.get_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} already exists")
        except:
            # Create collection if it doesn't exist
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),  # Cohere light embeddings are 384-dim
            )
            logger.info(f"Created collection {self.collection_name}")

    def _create_selenium_driver(self):
        """Create a Chrome driver with options to appear less like a bot"""
        chrome_options = Options()

        # Add arguments to appear more like a real user
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Speed up loading
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Set window size to appear more human-like
        chrome_options.add_argument("--window-size=1366,768")

        # Disable automation indicators
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            driver = webdriver.Chrome(options=chrome_options)
            # Execute script to remove webdriver property that identifies automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {str(e)}")
            logger.info("Make sure you have Chrome and chromedriver installed")
            logger.info("Install with: pip install selenium")
            logger.info("Download chromedriver from: https://chromedriver.chromium.org/")
            return None

    def fetch_sitemap_urls(self) -> List[str]:
        """Fetch and parse sitemap to get all URLs"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(self.sitemap_url, headers=headers, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

            urls = []
            for url_element in root.findall(f"{namespace}url"):
                loc = url_element.find(f"{namespace}loc")
                if loc is not None and loc.text:
                    urls.append(loc.text.strip())

            logger.info(f"Found {len(urls)} URLs in sitemap")
            return urls
        except Exception as e:
            logger.error(f"Failed to fetch sitemap: {str(e)}")
            return []

    def extract_text_from_url(self, url: str) -> str:
        """Extract text content from a URL using Selenium to handle JavaScript"""
        if not self.driver:
            logger.error("Selenium driver not available")
            return ""

        try:
            logger.info(f"Navigating to {url}")
            self.driver.get(url)

            # Wait for page to load
            try:
                # Wait for any element to be present (indicating page loaded)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Get page title to confirm we got the page
                title = self.driver.title
                logger.info(f"Successfully loaded: {url} - Title: {title[:50]}...")

                # Get the page source after JavaScript execution
                page_source = self.driver.page_source

                # Use BeautifulSoup to extract text from the rendered HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_source, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer", ".sidebar"]):
                    script.decompose()

                # Try to find main content areas typically used in Docusaurus
                content_selectors = [
                    'article', '.main-wrapper', '.theme-doc-markdown',
                    '.markdown', '.doc-content', '.docs-content',
                    '.main-content', 'main', '.container',
                    '.docItemContainer', '.markdown', '[class*="docItem"]'
                ]

                text_content = ""
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        text_content = content_elem.get_text(separator=' ', strip=True)
                        if len(text_content) > 50:  # If we get substantial content, use it
                            break

                # If no specific content area found with selectors, try alternative approach
                if not text_content or len(text_content) < 50:
                    # Try to find content by looking for content-related classes
                    content_elements = soup.find_all(['div', 'section', 'article', 'main'],
                                                   class_=lambda x: x and any(keyword in x.lower() for keyword in
                                                   ['content', 'main', 'article', 'doc', 'markdown', 'text']))
                    if content_elements:
                        for elem in content_elements:
                            elem_text = elem.get_text(separator=' ', strip=True)
                            if len(elem_text) > len(text_content):
                                text_content = elem_text

                # If still no good content, get the body text
                if not text_content or len(text_content) < 50:
                    body = soup.find('body')
                    if body:
                        # Remove common non-content elements
                        for elem in body(["nav", "header", "footer", "aside", "script", "style"]):
                            elem.decompose()
                        text_content = body.get_text(separator=' ', strip=True)

                # Clean up the text
                if text_content:
                    # Remove extra whitespace
                    text_content = re.sub(r'\s+', ' ', text_content).strip()

                    # If text is still too short, it might be a placeholder or protected page
                    if len(text_content) < 50:
                        logger.warning(f"Content too short from {url}: {len(text_content)} chars")
                        return ""

                    return text_content

            except TimeoutException:
                logger.warning(f"Timeout loading: {url}")
                return ""

        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {str(e)}")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {str(e)}")
            return ""

    def chunk_text(self, text: str, max_tokens: int = 500) -> List[str]:
        """Chunk text into smaller pieces based on token count"""
        # Split text into sentences or paragraphs
        sentences = text.split('\n')
        if len(sentences) == 1:  # If no newlines, split by sentences
            sentences = [s.strip() for s in text.replace('. ', '.\n').replace('! ', '!\n').replace('? ', '?\n').split('\n') if s.strip()]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Estimate token count
            token_count = len(self.enc.encode(current_chunk + " " + sentence))

            if token_count <= max_tokens:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:  # If current chunk is not empty, save it
                    chunks.append(current_chunk.strip())
                # Start a new chunk with the current sentence
                current_chunk = sentence

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Cohere"""
        if not self.cohere_client:
            raise ValueError("Cohere client not initialized")

        response = self.cohere_client.embed(
            texts=texts,
            model="embed-english-light-v3.0",  # 384 dimensions
            input_type="search_document"
        )

        return response.embeddings

    def store_in_qdrant(self, chunks: List[str], url: str):
        """Store chunks and their embeddings in Qdrant"""
        if not chunks:
            return

        # Generate embeddings for all chunks
        embeddings = self.generate_embeddings(chunks)

        # Prepare points for Qdrant
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "content": chunk,
                    "url": url,
                    "chunk_index": i,
                    "source": "sitemap_url"
                }
            )
            points.append(point)

        # Upload to Qdrant
        self.qdrant_client.upload_points(
            collection_name=self.collection_name,
            points=points
        )

        logger.info(f"Stored {len(chunks)} chunks from {url} in Qdrant")

    def process_url(self, url: str):
        """Process a single URL: extract text, chunk, embed, and store"""
        logger.info(f"Processing URL: {url}")

        # Extract text
        text = self.extract_text_from_url(url)
        if not text.strip():
            logger.warning(f"No text extracted from {url}")
            return

        logger.info(f"Extracted {len(text)} characters from {url}")

        # Chunk text
        chunks = self.chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from {url}")

        # Store in Qdrant
        self.store_in_qdrant(chunks, url)

        # Be respectful to the server
        time.sleep(random.uniform(1, 2))

    def ingest_sitemap(self):
        """Process all URLs from the sitemap"""
        urls = self.fetch_sitemap_urls()

        if not urls:
            logger.error("No URLs found in sitemap")
            return

        logger.info(f"Starting ingestion of {len(urls)} URLs from sitemap")

        successful_count = 0
        for i, url in enumerate(urls):
            try:
                logger.info(f"Processing {i+1}/{len(urls)}: {url}")
                self.process_url(url)
                successful_count += 1
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                continue

        logger.info(f"Successfully processed {successful_count}/{len(urls)} URLs")

    def run_ingestion(self):
        """Run the complete sitemap ingestion process"""
        logger.info("Starting Selenium-based sitemap ingestion process...")
        logger.info(f"Sitemap URL: {self.sitemap_url}")

        if not self.driver:
            logger.error("Cannot proceed without a working Selenium driver")
            return

        try:
            # Process all URLs from sitemap
            self.ingest_sitemap()
        finally:
            # Always quit the driver when done
            if self.driver:
                self.driver.quit()

        logger.info("Selenium-based sitemap ingestion process completed!")

def main():
    # Initialize with environment variables
    sitemap_url = "https://humanoid-robotics-textbook-zeta.vercel.app/sitemap.xml"
    cohere_api_key = os.getenv("COHERE_API_KEY")
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if not cohere_api_key:
        raise ValueError("COHERE_API_KEY environment variable not set")
    if not qdrant_url:
        raise ValueError("QDRANT_URL environment variable not set")

    ingestion = SeleniumSitemapIngestion(
        sitemap_url=sitemap_url,
        cohere_api_key=cohere_api_key,
        qdrant_url=qdrant_url,
        qdrant_api_key=QDRANT_API_KEY
    )

    ingestion.run_ingestion()

if __name__ == "__main__":
    main()