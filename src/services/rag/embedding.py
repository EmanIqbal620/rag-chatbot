from openai import OpenAI
from typing import List


class EmbeddingService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        
    def create_embedding(self, text: str):
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
        
    def create_embeddings(self, texts: List[str]):
        response = self.client.embeddings.create(
            input=texts,
            model="text-embedding-ada-002"
        )
        return [item.embedding for item in response.data]
