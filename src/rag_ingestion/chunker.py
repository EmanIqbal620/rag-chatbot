"""
Chunker module for the RAG Book Ingestion Pipeline.
Handles splitting text into appropriately sized chunks with overlap.
"""

import re
from typing import List, Tuple, Dict
from config.settings import settings
from .logger import ingestion_logger


class Chunker:
    """
    Splits text into appropriately sized chunks with overlap to maintain context.
    """

    def __init__(self, chunk_size: int = None, overlap_percent: float = None):
        """
        Initialize the chunker.

        Args:
            chunk_size: Size of each chunk in tokens. If None, uses settings.CHUNK_SIZE
            overlap_percent: Overlap percentage between chunks. If None, uses settings.CHUNK_OVERLAP
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap_percent = overlap_percent or settings.CHUNK_OVERLAP
        self.overlap_size = int(self.chunk_size * self.overlap_percent)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text (using a simple word-based approximation).

        Args:
            text: The text to estimate tokens for

        Returns:
            int: Estimated number of tokens
        """
        # Simple approximation: split on whitespace and punctuation
        words = re.findall(r'\b\w+\b', text)
        return len(words)

    def split_by_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences to maintain semantic boundaries.

        Args:
            text: The text to split

        Returns:
            List[str]: List of sentences
        """
        # Split by sentence endings, keeping the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        # Remove empty strings and strip whitespace
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def create_chunks(self, text: str, source_metadata: Dict = None) -> List[Dict]:
        """
        Create chunks from text with overlap.

        Args:
            text: The text to chunk
            source_metadata: Metadata about the source (URL, title, etc.)

        Returns:
            List[Dict]: List of chunks with metadata
        """
        if not text:
            return []

        # Get sentences to maintain semantic boundaries
        sentences = self.split_by_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for sentence in sentences:
            # Estimate tokens in current chunk + new sentence
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_token_count = self.estimate_tokens(test_chunk)

            if test_token_count <= self.chunk_size:
                # Add to current chunk
                current_chunk = test_chunk
            else:
                # Current chunk is full, save it
                if current_chunk.strip():
                    chunk_data = {
                        "text": current_chunk.strip(),
                        "chunk_index": chunk_index,
                        "token_count": self.estimate_tokens(current_chunk),
                        "source_metadata": source_metadata or {},
                        "overlap_with_next": True  # Will be updated later
                    }
                    chunks.append(chunk_data)
                    chunk_index += 1

                # Start new chunk with overlap if possible
                if self.overlap_size > 0:
                    # Get overlapping text from the end of current chunk
                    # For now, we'll just start with the current sentence
                    current_chunk = sentence
                else:
                    current_chunk = sentence

        # Add the last chunk if it has content
        if current_chunk.strip():
            chunk_data = {
                "text": current_chunk.strip(),
                "chunk_index": chunk_index,
                "token_count": self.estimate_tokens(current_chunk),
                "source_metadata": source_metadata or {},
                "overlap_with_next": False
            }
            chunks.append(chunk_data)

        # Apply overlap between chunks
        chunks = self._apply_overlap(chunks)

        ingestion_logger.log_chunking_success(source_metadata.get('url', 'unknown'), len(chunks))
        return chunks

    def _apply_overlap(self, chunks: List[Dict]) -> List[Dict]:
        """
        Apply overlap between consecutive chunks.

        Args:
            chunks: List of chunks to apply overlap to

        Returns:
            List[Dict]: Chunks with overlap applied
        """
        if len(chunks) <= 1 or self.overlap_size <= 0:
            return chunks

        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i < len(chunks) - 1:  # Not the last chunk
                # Get overlap from the next chunk
                next_chunk = chunks[i + 1]
                next_text = next_chunk["text"]

                # Extract overlap text from the beginning of the next chunk
                next_words = next_text.split()
                overlap_words = next_words[:self.overlap_size]
                overlap_text = " ".join(overlap_words)

                # Add overlap to the current chunk
                if overlap_text.strip():
                    chunk["text"] = chunk["text"] + " " + overlap_text
                    chunk["token_count"] = self.estimate_tokens(chunk["text"])
                    chunk["overlap_with_next"] = True
                else:
                    chunk["overlap_with_next"] = True
            else:
                chunk["overlap_with_next"] = False

            overlapped_chunks.append(chunk)

        return overlapped_chunks

    def chunk_batch(self, texts: List[Tuple[str, Dict]]) -> List[Dict]:
        """
        Chunk a batch of texts.

        Args:
            texts: List of tuples containing (text, source_metadata)

        Returns:
            List[Dict]: List of all chunks from all texts
        """
        all_chunks = []
        for text, metadata in texts:
            chunks = self.create_chunks(text, metadata)
            all_chunks.extend(chunks)
        return all_chunks


def create_chunks(text: str, source_metadata: Dict = None) -> List[Dict]:
    """
    Convenience function to create chunks from text.

    Args:
        text: The text to chunk
        source_metadata: Metadata about the source (URL, title, etc.)

    Returns:
        List[Dict]: List of chunks with metadata
    """
    chunker = Chunker()
    return chunker.create_chunks(text, source_metadata)


def chunk_batch(texts: List[Tuple[str, Dict]]) -> List[Dict]:
    """
    Convenience function to chunk a batch of texts.

    Args:
        texts: List of tuples containing (text, source_metadata)

    Returns:
        List[Dict]: List of all chunks from all texts
    """
    chunker = Chunker()
    return chunker.chunk_batch(texts)


if __name__ == "__main__":
    # Test the chunker
    print("Testing chunker...")

    test_text = """
    This is the first sentence of our sample text. It contains some information that should be preserved.
    Here's the second sentence which continues the thought from the first sentence.
    The third sentence adds more context to what we're discussing.
    Finally, the fourth sentence concludes this particular thought.
    We'll add another paragraph with different content.
    This new paragraph has its own context and meaning.
    The last sentence wraps up this second paragraph nicely.
    """

    chunker = Chunker(chunk_size=20, overlap_percent=0.2)
    chunks = chunker.create_chunks(test_text, {"url": "test_url", "title": "Test Document"})

    print(f"Created {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1} (tokens: {chunk['token_count']}, index: {chunk['chunk_index']}):")
        print(f"Text preview: {chunk['text'][:100]}...")
        print(f"Overlap with next: {chunk['overlap_with_next']}")