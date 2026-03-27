import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "humanoid_ai_book")
VECTOR_SIZE = 1024

def init_collection():
    """Create collection if it doesn't exist."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
        print(f"[QDRANT] Created collection: {COLLECTION}")

def upsert_chunks(chunks: list):
    """Upsert embedded chunks into Qdrant."""
    points = [
        PointStruct(
            id=c["id"],
            vector=c["embedding"],
            payload={
                "source_url": c["source_url"],
                "page_title": c["page_title"],
                "chapter_name": c.get("chapter_name", c["page_title"]),
                "chunk_index": c["chunk_index"],
                "text": c["text"]
            }
        )
        for c in chunks
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"[QDRANT] Upserted {len(points)} vectors")
