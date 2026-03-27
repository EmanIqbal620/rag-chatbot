from typing import List, Dict, Any, Optional
import logging
from qdrant_client import QdrantClient
from qdrant_client.http import models
import os

from utils.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

class QdrantRetriever:
    """
    Service for retrieving documents from Qdrant vector database.
    """

    def __init__(self):
        """Initialize the QdrantRetriever with Qdrant client and embedding service."""
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable is required")

        # Initialize Qdrant client
        if qdrant_api_key:
            try:
                self.client = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key,
                    prefer_grpc=True
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Qdrant client with API key: {str(e)}")
                # Try without API key as fallback
                self.client = QdrantClient(
                    url=qdrant_url,
                    prefer_grpc=True
                )
        else:
            # For local Qdrant instances without authentication
            self.client = QdrantClient(
                url=qdrant_url,
                prefer_grpc=True
            )

        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "humanoid_ai_book")
        self.embedding_service = EmbeddingService()

        # Validate that the collection exists
        try:
            self.client.get_collection(collection_name=self.collection_name)
            logger.info(f"Connected to Qdrant collection: {self.collection_name}")
            self.collection_exists = True
        except Exception as e:
            logger.error(f"Could not access Qdrant collection {self.collection_name}: {str(e)}")
            logger.error("Raw response content may indicate authentication or network issues")
            self.collection_exists = False
            # Instead of continuing, we should handle this as a critical issue
            logger.warning("Qdrant collection is not accessible - RAG functionality will be limited")

    async def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in the Qdrant vector database.

        Args:
            query: The query string to search for
            top_k: Number of top results to return
            filters: Optional filters to apply to the search

        Returns:
            List of dictionaries containing document content, metadata, and scores
        """
        # If collection doesn't exist or isn't accessible, return empty results
        if not self.collection_exists:
            logger.warning(f"Qdrant collection {self.collection_name} is not accessible. Returning empty results.")
            return []

        try:
            # Generate embedding for the query
            query_embedding = await self.embedding_service.embed_text(query)

            # Prepare filters for Qdrant search
            qdrant_filters = None
            if filters:
                # Convert filters to Qdrant filter format
                must_conditions = []
                for key, value in filters.items():
                    must_conditions.append(
                        models.FieldCondition(
                            key=f"metadata.{key}",
                            match=models.MatchValue(value=value)
                        )
                    )

                if must_conditions:
                    qdrant_filters = models.Filter(must=must_conditions)

            # Perform vector search using query_points (newer Qdrant SDK)
            search_response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=top_k,
                query_filter=qdrant_filters,
                with_payload=True,
                with_vectors=False,
                score_threshold=0.1  # Minimum similarity threshold
            )

            # Access the points from the response object
            search_results = search_response.points

            # Format results
            formatted_results = []
            for result in search_results:
                formatted_result = {
                    "id": result.id,
                    "content": result.payload.get("content", ""),
                    "metadata": result.payload.get("metadata", {}),
                    "score": result.score
                }
                formatted_results.append(formatted_result)

            logger.info(f"Retrieved {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching Qdrant for query '{query[:50]}...': {str(e)}")
            # Return empty results instead of raising exception to allow graceful degradation
            return []

    async def search_by_metadata(self, metadata_filters: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents by metadata filters.

        Args:
            metadata_filters: Dictionary of metadata key-value pairs to filter by
            top_k: Number of top results to return

        Returns:
            List of documents matching the metadata filters
        """
        try:
            # Create filter for metadata
            must_conditions = []
            for key, value in metadata_filters.items():
                must_conditions.append(
                    models.FieldCondition(
                        key=f"metadata.{key}",
                        match=models.MatchValue(value=value)
                    )
                )

            qdrant_filter = models.Filter(must=must_conditions)

            # Perform search with metadata filter using scroll (for filter-only search)
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False
            )

            # Convert scroll results to the same format as search results
            # Scroll returns (records, next_page_offset) tuple
            records, _ = search_results
            # For compatibility with the rest of the code, we'll create objects with similar structure
            # but we need to handle this differently since scroll doesn't return scores
            formatted_results = []
            for record in records:
                formatted_result = {
                    "id": record.id,
                    "content": record.payload.get("content", ""),
                    "metadata": record.payload.get("metadata", {}),
                    "score": 0.0  # Scroll doesn't return scores, so we use 0.0 as default
                }
                formatted_results.append(formatted_result)

            logger.info(f"Retrieved {len(formatted_results)} results by metadata filter")
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching Qdrant by metadata: {str(e)}")
            raise

    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by its ID.

        Args:
            doc_id: The ID of the document to retrieve

        Returns:
            Document dictionary if found, None otherwise
        """
        try:
            records = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[doc_id],
                with_payload=True,
                with_vectors=False
            )

            if records:
                record = records[0]
                return {
                    "id": record.id,
                    "content": record.payload.get("content", ""),
                    "metadata": record.payload.get("metadata", {})
                }
            else:
                return None

        except Exception as e:
            logger.error(f"Error retrieving document by ID {doc_id}: {str(e)}")
            raise

    async def get_similar_documents(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find documents similar to the given text.

        Args:
            text: The text to find similar documents for
            top_k: Number of top results to return

        Returns:
            List of similar documents
        """
        return await self.search(text, top_k)

    def is_healthy(self) -> bool:
        """
        Check if the Qdrant connection is healthy.
        """
        try:
            # If collection doesn't exist or isn't accessible, consider it unhealthy
            if not self.collection_exists:
                logger.warning("Qdrant collection is not accessible, marking as unhealthy")
                return False

            # Try to get collection info
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False