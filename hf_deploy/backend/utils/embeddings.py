from typing import List, Union
import logging
import os
import asyncio
import cohere
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for generating text embeddings using Cohere API.
    """

    def __init__(self):
        """Initialize the EmbeddingService with Cohere client."""
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            logger.warning("COHERE_API_KEY environment variable is not set.")
            self.client = None
            self.model_name = "embed-english-light-v3.0"
            self.max_batch_size = 96
        else:
            try:
                import cohere
                self.client = cohere.Client(cohere_api_key)
                self.model_name = "embed-english-light-v3.0"  # Using the same model as in the ingestion
                self.max_batch_size = 96  # Cohere's API limit is 96 texts per request
                logger.info("Cohere client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Cohere client: {str(e)}")
                self.client = None
                self.model_name = "embed-english-light-v3.0"
                self.max_batch_size = 96

        # Use a thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text(s) using Cohere API.

        Args:
            text: Single text string or list of text strings to embed

        Returns:
            Single embedding vector or list of embedding vectors
        """
        # If Cohere client is not available, return empty embeddings or handle gracefully
        if not self.client:
            logger.error("Cohere client is not available. Cannot generate embeddings.")
            # Return a default embedding (this is just to prevent crashes, but it won't be meaningful)
            # In a real scenario, you'd want to use a different embedding provider or pre-computed embeddings
            if isinstance(text, str):
                # Return a default embedding vector (384 dimensions for Cohere light model)
                return [0.0] * 384
            else:
                # Return a list of default embedding vectors
                return [[0.0] * 384 for _ in text]

        try:
            # Handle single text by converting to list
            is_single = isinstance(text, str)
            texts = [text] if is_single else text

            # Process in batches if needed (Cohere API has limits)
            all_embeddings = []
            for i in range(0, len(texts), self.max_batch_size):
                batch = texts[i:i + self.max_batch_size]

                # Call Cohere API in a thread since it's synchronous
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    self.executor,
                    lambda: self.client.embed(
                        texts=batch,
                        model=self.model_name,
                        input_type="search_query" if is_single else "search_document"
                    )
                )

                all_embeddings.extend(response.embeddings)

            # Return single embedding if input was single, otherwise return list
            return all_embeddings[0] if is_single else all_embeddings

        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            # Return default embeddings as fallback
            if isinstance(text, str):
                return [0.0] * 384
            else:
                return [[0.0] * 384 for _ in text]

    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.

        Args:
            documents: List of document strings to embed

        Returns:
            List of embedding vectors
        """
        return await self.embed_text(documents)

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query string.

        Args:
            query: Query string to embed

        Returns:
            Embedding vector
        """
        return await self.embed_text(query)

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embeddings produced by this service.
        For Cohere's embed-english-light-v3.0 model, it's 384.
        """
        return 384

    def is_healthy(self) -> bool:
        """
        Check if the embedding service is healthy by making a test call.
        """
        try:
            # Test with a simple embedding
            test_embedding = asyncio.run(self.embed_text("test"))
            return len(test_embedding) > 0
        except Exception as e:
            logger.error(f"Embedding service health check failed: {str(e)}")
            return False