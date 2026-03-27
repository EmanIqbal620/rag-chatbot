from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict, Any


class VectorStore:
    def __init__(self, url: str, api_key: str = None):
        self.client = QdrantClient(url=url, api_key=api_key)
        
    def create_collection(self, collection_name: str):
        # Create a collection for storing textbook embeddings
        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )
        
    def add_texts(self, collection_name: str, texts: List[str], metadata: List[Dict[str, Any]] = None):
        # Add text chunks with embeddings to the collection
        from openai import OpenAI
        client = OpenAI()
        
        # Generate embeddings for the texts
        embeddings = []
        for text in texts:
            response = client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            embeddings.append(response.data[0].embedding)
        
        # Prepare points for insertion
        points = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            points.append(models.PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "text": text,
                    "metadata": metadata[i] if metadata else {}
                }
            ))
        
        # Upload to Qdrant
        self.client.upsert(collection_name=collection_name, points=points)
        
    def search(self, collection_name: str, query_text: str, top_k: int = 5):
        # Search for similar text chunks
        from openai import OpenAI
        client = OpenAI()
        
        # Generate embedding for the query
        response = client.embeddings.create(
            input=query_text,
            model="text-embedding-ada-002"
        )
        query_embedding = response.data[0].embedding
        
        # Search in Qdrant
        search_results = self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        # Extract the relevant text chunks
        results = []
        for result in search_results:
            results.append({
                "text": result.payload["text"],
                "metadata": result.payload["metadata"],
                "score": result.score
            })
        
        return results
