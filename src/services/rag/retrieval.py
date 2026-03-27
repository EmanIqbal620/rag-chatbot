from typing import List
from backend.services.rag.vector_store import VectorStore
from backend.utils.logging import logger


class RAGService:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        
    def retrieve_context(self, query: str, collection_name: str, top_k: int = 5) -> List[dict]:
        """
        Retrieve relevant context from the vector store based on the query
        """
        try:
            results = self.vector_store.search(
                collection_name=collection_name,
                query_text=query,
                top_k=top_k
            )
            
            logger.info(f"Retrieved {len(results)} context chunks for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []
