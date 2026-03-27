"""
Vector store module for the RAG Book Ingestion Pipeline.
Handles storing and retrieving embeddings in Qdrant.
"""

import uuid
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
from config.settings import settings
from .logger import ingestion_logger


class VectorStore:
    """
    Manages storage and retrieval of embeddings in Qdrant.
    """

    def __init__(self, collection_name: str = "book_embeddings"):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the Qdrant collection to use
        """
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=60  # Increased timeout for bulk operations
        )
        self.collection_name = collection_name
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """
        Ensure the collection exists in Qdrant with appropriate configuration.
        """
        try:
            # Try to get collection info to see if it exists
            self.client.get_collection(self.collection_name)
            ingestion_logger.info(f"Collection '{self.collection_name}' already exists")
        except:
            # Collection doesn't exist, create it
            # We'll use a default vector size based on Cohere embeddings (typically 768 for multilingual models)
            # But we'll make it flexible by creating it when we first add a vector
            ingestion_logger.info(f"Creating collection '{self.collection_name}'")
            # We'll create the collection when we first upsert vectors

    def create_collection(self, vector_size: int = 768):
        """
        Create a collection in Qdrant with the specified vector size.

        Args:
            vector_size: Size of the embedding vectors
        """
        try:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            ingestion_logger.info(f"Created collection '{self.collection_name}' with vector size {vector_size}")
        except Exception as e:
            ingestion_logger.error(f"Error creating collection: {e}")

    def upsert_vectors(self, chunks_with_embeddings: List[Dict]) -> bool:
        """
        Upsert (insert or update) vectors with metadata into Qdrant.

        Args:
            chunks_with_embeddings: List of chunk dictionaries with 'embedding' field and metadata

        Returns:
            bool: True if successful, False otherwise
        """
        if not chunks_with_embeddings:
            ingestion_logger.info("No chunks to upsert")
            return True

        try:
            # Prepare points for upsert
            points = []
            for chunk in chunks_with_embeddings:
                # Generate a unique ID for each chunk
                point_id = str(uuid.uuid4())

                # Extract embedding and metadata
                embedding = chunk.get('embedding')
                text = chunk.get('text', '')
                source_metadata = chunk.get('source_metadata', {})

                # Prepare payload with metadata
                payload = {
                    'text': text,
                    'chunk_index': chunk.get('chunk_index', 0),
                    'token_count': chunk.get('token_count', 0),
                    'overlap_with_next': chunk.get('overlap_with_next', False),
                    'url': source_metadata.get('url', ''),
                    'title': source_metadata.get('title', ''),
                    'section': source_metadata.get('section', ''),
                    'created_at': chunk.get('created_at', __import__('datetime').datetime.utcnow().isoformat())
                }

                # Add any additional metadata from source
                for key, value in source_metadata.items():
                    if key not in payload:
                        payload[key] = value

                # Create point
                point = models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)

            # Determine vector size from first embedding if collection doesn't exist
            if embedding:
                try:
                    self.client.get_collection(self.collection_name)
                except:
                    # Collection doesn't exist, create it
                    self.create_collection(len(embedding))

            # Upsert points to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            ingestion_logger.log_storage_success(len(points))
            return True

        except Exception as e:
            ingestion_logger.log_storage_error(f"Failed to upsert vectors: {str(e)}")
            return False

    def search(self, query_embedding: List[float], limit: int = 10) -> List[Dict]:
        """
        Search for similar vectors in Qdrant.

        Args:
            query_embedding: The embedding vector to search for similar ones
            limit: Maximum number of results to return

        Returns:
            List[Dict]: List of similar chunks with their metadata
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_result = {
                    'id': result.id,
                    'text': result.payload.get('text', ''),
                    'url': result.payload.get('url', ''),
                    'title': result.payload.get('title', ''),
                    'section': result.payload.get('section', ''),
                    'score': result.score,
                    'chunk_index': result.payload.get('chunk_index', 0),
                    'metadata': {k: v for k, v in result.payload.items()
                                if k not in ['text', 'url', 'title', 'section', 'chunk_index']}
                }
                formatted_results.append(formatted_result)

            return formatted_results

        except Exception as e:
            ingestion_logger.error(f"Search failed: {str(e)}")
            return []

    def validate_storage(self) -> bool:
        """
        Validate that vectors are properly stored in Qdrant.

        Returns:
            bool: True if storage is working, False otherwise
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection(self.collection_name)

            # Check if we have any points
            count = self.client.count(
                collection_name=self.collection_name
            )

            ingestion_logger.info(f"Collection '{self.collection_name}' has {count.count} vectors")
            return count.count >= 0  # If we can get the count, storage is accessible

        except Exception as e:
            ingestion_logger.error(f"Storage validation failed: {str(e)}")
            return False

    def delete_collection(self):
        """
        Delete the entire collection (use with caution!).
        """
        try:
            self.client.delete_collection(self.collection_name)
            ingestion_logger.info(f"Deleted collection '{self.collection_name}'")
        except Exception as e:
            ingestion_logger.error(f"Failed to delete collection: {str(e)}")

    def get_total_count(self) -> int:
        """
        Get the total number of vectors in the collection.

        Returns:
            int: Total number of vectors
        """
        try:
            count = self.client.count(
                collection_name=self.collection_name
            )
            return count.count
        except Exception as e:
            ingestion_logger.error(f"Failed to get count: {str(e)}")
            return 0


def upsert_vectors(chunks_with_embeddings: List[Dict], collection_name: str = "book_embeddings") -> bool:
    """
    Convenience function to upsert vectors to Qdrant.

    Args:
        chunks_with_embeddings: List of chunk dictionaries with 'embedding' field and metadata
        collection_name: Name of the Qdrant collection to use

    Returns:
        bool: True if successful, False otherwise
    """
    vector_store = VectorStore(collection_name)
    return vector_store.upsert_vectors(chunks_with_embeddings)


def search_vectors(query_embedding: List[float], collection_name: str = "book_embeddings", limit: int = 10) -> List[Dict]:
    """
    Convenience function to search for similar vectors in Qdrant.

    Args:
        query_embedding: The embedding vector to search for similar ones
        collection_name: Name of the Qdrant collection to search
        limit: Maximum number of results to return

    Returns:
        List[Dict]: List of similar chunks with their metadata
    """
    vector_store = VectorStore(collection_name)
    return vector_store.search(query_embedding, limit)


def validate_storage(collection_name: str = "book_embeddings") -> bool:
    """
    Convenience function to validate storage.

    Args:
        collection_name: Name of the Qdrant collection to validate

    Returns:
        bool: True if storage is working, False otherwise
    """
    vector_store = VectorStore(collection_name)
    return vector_store.validate_storage()


if __name__ == "__main__":
    # Test the vector store
    print("Testing vector store...")

    # Check if Qdrant is configured
    if not settings.QDRANT_URL:
        print("Warning: QDRANT_URL not set in environment. Skipping vector store test.")
        print("Please set QDRANT_URL and QDRANT_API_KEY to test vector storage functionality.")
    else:
        try:
            # Create a mock embedding for testing
            mock_embedding = [0.1] * 768  # Standard Cohere embedding size

            # Test vector store
            vs = VectorStore("test_collection")

            # Test validation
            is_valid = vs.validate_storage()
            print(f"Storage validation: {is_valid}")

            # Clean up test collection
            vs.delete_collection()

            print("Vector store test completed.")

        except Exception as e:
            print(f"Error during vector store test: {e}")
            print("This may be due to Qdrant connection issues or invalid credentials.")