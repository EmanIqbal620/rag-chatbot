import os
import re
from pathlib import Path
import logging
from typing import List, Tuple
import markdown
from bs4 import BeautifulSoup
from pypdf import PdfReader
import cohere
from qdrant_client import QdrantClient
from qdrant_client.http import models
import uuid
import tiktoken

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalIngestion:
    def __init__(self, data_dir: str = "backend/data", cohere_api_key: str = None, qdrant_url: str = None, qdrant_api_key: str = None):
        self.data_dir = Path(data_dir)
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
                vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE),  # Cohere embeddings are 1024-dim
            )
            logger.info(f"Created collection {self.collection_name}")

    def extract_text_from_markdown(self, file_path: Path) -> str:
        """Extract text from markdown file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # Convert markdown to HTML, then extract text
            html = markdown.markdown(content)
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()

    def extract_text_from_html(self, file_path: Path) -> str:
        """Extract text from HTML file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text()

    def extract_text_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from file based on its extension"""
        extension = file_path.suffix.lower()

        if extension == '.md':
            return self.extract_text_from_markdown(file_path)
        elif extension in ['.html', '.htm']:
            return self.extract_text_from_html(file_path)
        elif extension == '.txt':
            return self.extract_text_from_txt(file_path)
        elif extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        else:
            logger.warning(f"Unsupported file type: {extension}")
            return ""

    def chunk_text(self, text: str, max_tokens: int = 500) -> List[str]:
        """Chunk text into smaller pieces based on token count"""
        # Split text into sentences or paragraphs
        sentences = re.split(r'[.!?]+\s+|\n+', text)

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
            model="embed-english-v3.0",
            input_type="search_document"
        )

        return response.embeddings

    def store_in_qdrant(self, chunks: List[str], file_path: Path):
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
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "chunk_index": i,
                    "source": "local_file"
                }
            )
            points.append(point)

        # Upload to Qdrant
        self.qdrant_client.upload_points(
            collection_name=self.collection_name,
            points=points
        )

        logger.info(f"Stored {len(chunks)} chunks from {file_path.name} in Qdrant")

    def process_file(self, file_path: Path):
        """Process a single file: extract text, chunk, embed, and store"""
        logger.info(f"Processing file: {file_path}")

        # Extract text
        text = self.extract_text_from_file(file_path)
        if not text.strip():
            logger.warning(f"No text extracted from {file_path}")
            return

        logger.info(f"Extracted {len(text)} characters from {file_path.name}")

        # Chunk text
        chunks = self.chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks from {file_path.name}")

        # Store in Qdrant
        self.store_in_qdrant(chunks, file_path)

    def ingest_all_files(self):
        """Process all files in the data directory"""
        supported_extensions = {'.md', '.html', '.htm', '.txt', '.pdf'}

        files = []
        for ext in supported_extensions:
            files.extend(self.data_dir.glob(f"*{ext}"))
            files.extend(self.data_dir.glob(f"**/*{ext}"))  # Include subdirectories

        logger.info(f"Found {len(files)} files to process")

        for file_path in files:
            try:
                self.process_file(file_path)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                continue

    def run_ingestion(self):
        """Run the complete ingestion process"""
        logger.info("Starting local ingestion process...")
        logger.info(f"Data directory: {self.data_dir}")

        # Process all files
        self.ingest_all_files()

        logger.info("Ingestion process completed!")

def main():
    # Initialize with environment variables or defaults
    cohere_api_key = os.getenv("COHERE_API_KEY")
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    ingestion = LocalIngestion(
        data_dir="backend/data",
        cohere_api_key=cohere_api_key,
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key
    )

    ingestion.run_ingestion()

if __name__ == "__main__":
    main()