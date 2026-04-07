import os
from dotenv import load_dotenv
from pathlib import Path

# Load backend .env specifically
backend_dir = Path(__file__).parent.parent
load_dotenv(backend_dir / ".env", override=True)

# Initialize Cohere
co = None
COHERE_AVAILABLE = False
try:
    import cohere
    api_key = os.getenv("COHERE_API_KEY")
    if api_key:
        co = cohere.Client(api_key)
        COHERE_AVAILABLE = True
        print(f"[COHERE] Connected")
    else:
        print("[COHERE] API key not set")
except Exception as e:
    print(f"[COHERE] Error: {e}")

# Initialize Qdrant
qdrant = None
QDRANT_AVAILABLE = False
COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "humanoid_ai_book")
try:
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    if qdrant_url and qdrant_key:
        from qdrant_client import QdrantClient
        qdrant = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        # Test connection
        collections = qdrant.get_collections()
        print(f"[QDRANT] Connected — URL: {qdrant_url}")
        # Check if collection exists
        collection_names = [c.name for c in collections.collections]
        if COLLECTION in collection_names:
            print(f"[QDRANT] Collection '{COLLECTION}' exists")
        else:
            print(f"[QDRANT] WARNING: Collection '{COLLECTION}' not found! Run ingestion first.")
        QDRANT_AVAILABLE = True
    else:
        print("[QDRANT] URL or API key not set")
        print(f"[QDRANT] QDRANT_URL={'set' if qdrant_url else 'MISSING'}, QDRANT_API_KEY={'set' if qdrant_key else 'MISSING'}")
except Exception as e:
    print(f"[QDRANT] Error: {e}")

# Query embedding cache
_query_cache = {}

def embed_query(query: str) -> list:
    """Fast embedding with cache using Cohere."""
    if query in _query_cache:
        return _query_cache[query]

    if not COHERE_AVAILABLE:
        return [0.0] * 1024  # Dummy embedding

    clean_query = query.replace("[SELECTED]: ", "").strip()
    try:
        response = co.embed(
            texts=[clean_query],
            model="embed-english-v3.0",
            input_type="search_query"
        )
        embedding = response.embeddings[0]
        _query_cache[query] = embedding
        return embedding
    except Exception as e:
        print(f"[COHERE EMBED ERROR] {e}")
        return [0.0] * 1024

def search(query: str, top_k: int = 5) -> list:
    """Search Qdrant for relevant chunks."""
    if not QDRANT_AVAILABLE:
        print(f"[SEARCH] Qdrant not available, returning empty for: {query[:50]}")
        return []

    try:
        vector = embed_query(query)
        results = qdrant.query_points(
            collection_name=COLLECTION,
            query=vector,
            limit=top_k
        )
        hits = len(results.points)
        print(f"[SEARCH] Query returned {hits} results for: {query[:50]}")
        
        points = []
        for r in results.points:
            point = {
                "text": r.payload.get("text", ""),
                "source_url": r.payload.get("source_url", ""),
                "page_title": r.payload.get("page_title", ""),
                "chapter_name": r.payload.get("chapter_name", r.payload.get("page_title", "Unknown")),
                "chunk_index": r.payload.get("chunk_index", 0),
                "score": round(r.score, 4)
            }
            points.append(point)
            print(f"[SEARCH] Hit: {point['chapter_name']} (score: {point['score']})")
        
        return points
    except Exception as e:
        print(f"[RETRIEVER ERROR] {e}")
        return []
