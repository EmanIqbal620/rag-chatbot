import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import List
import markdown
from bs4 import BeautifulSoup
import cohere
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
import tiktoken
import time
import random

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SitemapIngestion:
    def __init__(self, sitemap_url: str, cohere_api_key: str = None, qdrant_url: str = None, qdrant_api_key: str = None):
        self.sitemap_url = sitemap_url
        self.cohere_client = cohere.Client(cohere_api_key) if cohere_api_key else None
        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key) if qdrant_url else QdrantClient(host="localhost", port=6333)
        self.enc = tiktoken.get_encoding("cl100k_base")  # For token counting

        # Create Qdrant collection if it doesn't exist
        self.collection_name = "humanoid_ai_book"
        self._setup_qdrant_collection()

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
        """Extract text content from a URL"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Try to extract content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", ".sidebar"]):
                script.decompose()

            # Try to find main content areas typically used in Docusaurus
            content_selectors = [
                '.theme-doc-markdown', '.markdown', 'article', '.main-wrapper',
                '.doc-content', '.docs-content', '.main-content', 'main', '.container',
                '[class*="docItemContainer"]', '[class*="docRoot"]', '[class*="docItemCol"]'
            ]

            text_content = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    text_content = content_elem.get_text(separator=' ', strip=True)
                    break

            # If no specific content area found, get body text
            if not text_content:
                body = soup.find('body')
                if body:
                    text_content = body.get_text(separator=' ', strip=True)

            return text_content if text_content else ""

        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {str(e)}")
            return ""

    def chunk_text(self, text: str, max_tokens: int = 700, overlap_tokens: int = 120) -> List[str]:
        """Chunk text into smaller pieces based on token count with overlap"""
        # Split text into sentences or paragraphs
        sentences = text.split('\n')
        if len(sentences) == 1:  # If no newlines, split by sentences
            sentences = [s.strip() for s in text.replace('. ', '.\n').replace('! ', '!\n').replace('? ', '?\n').split('\n') if s.strip()]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Estimate token count for current chunk + sentence
            token_count = len(self.enc.encode(current_chunk + " " + sentence))

            if token_count <= max_tokens:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:  # If current chunk is not empty, save it
                    chunks.append(current_chunk.strip())

                # For overlap, keep some content from the end of the previous chunk
                if overlap_tokens > 0 and chunks:
                    # Get the last chunk and take the last overlap_tokens worth of content
                    last_chunk_tokens = self.enc.encode(current_chunk)
                    if len(last_chunk_tokens) > overlap_tokens:
                        # Get the last 'overlap_tokens' tokens and decode them
                        overlap_start_idx = max(0, len(last_chunk_tokens) - overlap_tokens)
                        overlap_tokens_list = last_chunk_tokens[overlap_start_idx:]
                        overlap_text = self.enc.decode(overlap_tokens_list)
                        current_chunk = overlap_text + " " + sentence
                    else:
                        current_chunk = sentence
                else:
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
        time.sleep(random.uniform(1, 3))

    def ingest_sitemap(self):
        """Process all URLs from the sitemap"""
        urls = self.fetch_sitemap_urls()

        if not urls:
            logger.error("No URLs found in sitemap")
            return

        logger.info(f"Starting ingestion of {len(urls)} URLs from sitemap")

        for i, url in enumerate(urls):
            try:
                logger.info(f"Processing {i+1}/{len(urls)}: {url}")
                self.process_url(url)
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                continue

    def run_ingestion(self):
        """Run the complete sitemap ingestion process"""
        logger.info("Starting sitemap ingestion process...")
        logger.info(f"Sitemap URL: {self.sitemap_url}")

        # Process all URLs from sitemap
        self.ingest_sitemap()

        logger.info("Sitemap ingestion process completed!")

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

    ingestion = SitemapIngestion(
        sitemap_url=sitemap_url,
        cohere_api_key=cohere_api_key,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key
    )

    ingestion.run_ingestion()

if __name__ == "__main__":
    main()