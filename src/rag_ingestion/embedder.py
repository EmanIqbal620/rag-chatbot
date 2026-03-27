"""
Embedder module for the RAG Book Ingestion Pipeline.
Handles generating embeddings using Cohere models.
"""

import time
from typing import List, Dict, Union
from config.settings import settings
from .logger import ingestion_logger, log_time
import cohere


class Embedder:
    """
    Generates embeddings for text chunks using Cohere models.
    """

    def __init__(self, model: str = "multilingual-22-12"):
        """
        Initialize the embedder.

        Args:
            model: The Cohere model to use for embeddings
        """
        self.client = cohere.Client(settings.COHERE_API_KEY)
        self.model = model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding for a text.

        Args:
            text: The text to generate embedding for

        Returns:
            List[float]: The embedding vector
        """
        try:
            response = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="search_document"
            )
            return response.embeddings[0]  # Return the first (and only) embedding
        except Exception as e:
            ingestion_logger.log_embedding_error(f"Failed to generate embedding: {str(e)}")
            raise

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 96) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to generate embeddings for
            batch_size: Maximum number of texts to process in one request (Cohere limit is 96)

        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not texts:
            return []

        all_embeddings = []
        start_time = time.time()

        # Process in batches to respect API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                with log_time(f"Embedding batch {i//batch_size + 1}"):
                    response = self.client.embed(
                        texts=batch,
                        model=self.model,
                        input_type="search_document"
                    )

                batch_embeddings = response.embeddings
                all_embeddings.extend(batch_embeddings)

                # Log progress
                progress = min(i + batch_size, len(texts))
                ingestion_logger.log_progress(
                    progress,
                    len(texts),
                    f"Generated embeddings for {progress}/{len(texts)} texts"
                )

            except Exception as e:
                ingestion_logger.log_embedding_error(f"Failed to generate embeddings for batch {i//batch_size + 1}: {str(e)}")
                # Return partial results or raise based on requirements
                raise

        duration = time.time() - start_time
        ingestion_logger.log_embedding_success(len(texts), duration)

        return all_embeddings

    def generate_embeddings_for_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for a list of text chunks.

        Args:
            chunks: List of chunk dictionaries containing 'text' field

        Returns:
            List[Dict]: List of chunk dictionaries with added 'embedding' field
        """
        if not chunks:
            return []

        # Extract texts from chunks
        texts = [chunk.get('text', '') for chunk in chunks]

        # Generate embeddings
        embeddings = self.generate_embeddings_batch(texts)

        # Add embeddings back to chunks
        chunks_with_embeddings = []
        for i, chunk in enumerate(chunks):
            chunk_copy = chunk.copy()
            chunk_copy['embedding'] = embeddings[i]
            chunks_with_embeddings.append(chunk_copy)

        return chunks_with_embeddings


def generate_embedding(text: str, model: str = "multilingual-22-12") -> List[float]:
    """
    Convenience function to generate a single embedding.

    Args:
        text: The text to generate embedding for
        model: The Cohere model to use

    Returns:
        List[float]: The embedding vector
    """
    embedder = Embedder(model)
    return embedder.generate_embedding(text)


def generate_embeddings_batch(texts: List[str], model: str = "multilingual-22-12", batch_size: int = 96) -> List[List[float]]:
    """
    Convenience function to generate embeddings for a batch of texts.

    Args:
        texts: List of texts to generate embeddings for
        model: The Cohere model to use
        batch_size: Maximum number of texts per batch

    Returns:
        List[List[float]]: List of embedding vectors
    """
    embedder = Embedder(model)
    return embedder.generate_embeddings_batch(texts, batch_size)


def generate_embeddings_for_chunks(chunks: List[Dict], model: str = "multilingual-22-12") -> List[Dict]:
    """
    Convenience function to generate embeddings for text chunks.

    Args:
        chunks: List of chunk dictionaries containing 'text' field
        model: The Cohere model to use

    Returns:
        List[Dict]: List of chunk dictionaries with added 'embedding' field
    """
    embedder = Embedder(model)
    return embedder.generate_embeddings_for_chunks(chunks)


def validate_embedding(embedding: List[float]) -> bool:
    """
    Validate that an embedding is properly formed.

    Args:
        embedding: The embedding vector to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not embedding:
        return False

    if not isinstance(embedding, list):
        return False

    # Check that all values are numbers
    if not all(isinstance(val, (int, float)) for val in embedding):
        return False

    # Embeddings should not be all zeros (degenerate case)
    if all(val == 0 for val in embedding):
        return False

    return True


def get_model_info(model: str = "multilingual-22-12") -> Dict:
    """
    Get information about a Cohere model.

    Args:
        model: The model name

    Returns:
        Dict: Model information
    """
    try:
        # Note: Cohere doesn't have a direct API for model info,
        # but we can test the model by generating a simple embedding
        embedder = Embedder(model)
        test_embedding = embedder.generate_embedding("test")
        return {
            "model": model,
            "embedding_dimension": len(test_embedding),
            "valid": True
        }
    except Exception as e:
        return {
            "model": model,
            "error": str(e),
            "valid": False
        }


if __name__ == "__main__":
    # Test the embedder
    print("Testing embedder...")

    # Check if API key is configured
    if not settings.COHERE_API_KEY:
        print("Warning: COHERE_API_KEY not set in environment. Skipping embedding test.")
        print("Please set COHERE_API_KEY to test embedding functionality.")
    else:
        # Test single embedding
        test_text = "This is a test sentence for embedding."

        try:
            embedder = Embedder()
            embedding = embedder.generate_embedding(test_text)

            print(f"Generated embedding for: '{test_text[:30]}...'")
            print(f"Embedding dimension: {len(embedding)}")
            print(f"First 5 values: {embedding[:5]}")
            print(f"Embedding valid: {validate_embedding(embedding)}")

            # Test batch embedding
            test_texts = [
                "First test sentence.",
                "Second test sentence.",
                "Third test sentence."
            ]

            batch_embeddings = embedder.generate_embeddings_batch(test_texts)
            print(f"\nGenerated {len(batch_embeddings)} embeddings in batch")

        except Exception as e:
            print(f"Error during embedding test: {e}")
            print("This may be due to invalid API key or network issues.")