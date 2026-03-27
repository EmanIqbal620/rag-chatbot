import os
from dotenv import load_dotenv

load_dotenv()

# Initialize once for speed
try:
    import cohere
    co = cohere.Client(os.getenv("COHERE_API_KEY"))
    COHERE_AVAILABLE = True
except:
    co = None
    COHERE_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    qdrant = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    QDRANT_AVAILABLE = True
except:
    qdrant = None
    QDRANT_AVAILABLE = False

COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "humanoid_ai_book")

# Query embedding cache
_query_cache = {}

def embed_query(query: str) -> list:
    """Fast embedding with cache."""
    if query in _query_cache:
        return _query_cache[query]
    
    if not COHERE_AVAILABLE:
        # Return dummy embedding if cohere not available
        return [0.0] * 1024

    clean_query = query.replace("[SELECTED]: ", "").strip()
    response = co.embed(
        texts=[clean_query],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    embedding = response.embeddings[0]
    _query_cache[query] = embedding
    return embedding

def search(query: str, top_k: int = 5) -> list:
    """Fast search."""
    if not QDRANT_AVAILABLE:
        return []
    
    try:
        vector = embed_query(query)
        results = qdrant.query_points(
            collection_name=COLLECTION,
            query=vector,
            limit=top_k
        )
        return [
            {
                "text": r.payload.get("text", ""),
                "source_url": r.payload.get("source_url", ""),
                "page_title": r.payload.get("page_title", ""),
                "chapter_name": r.payload.get("chapter_name", r.payload.get("page_title", "Unknown")),
                "chunk_index": r.payload.get("chunk_index", 0),
                "score": round(r.score, 4)
            }
            for r in results.points
        ]
    except Exception as e:
        print(f"[RETRIEVER ERROR] {e}")
        return []
