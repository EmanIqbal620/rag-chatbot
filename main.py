# main.py - Complete RAG Backend for Docusaurus Book with Local File Ingestion
# Switched from URL crawling to local file ingestion

import os
from dotenv import load_dotenv
load_dotenv()

# =====================================
# CONFIGURATION
# =====================================

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import cohere
import uuid

COLLECTION_NAME = "humanoid_ai_book"

# API Keys - Load from environment
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Debug: Check if keys are loaded
print("\n[KEY] Checking API Keys...")
print(f"   COHERE_API_KEY: {'[OK] Loaded' if COHERE_API_KEY else '[ERROR] MISSING!'}")
print(f"   QDRANT_URL: {'[OK] Loaded' if QDRANT_URL else '[ERROR] MISSING!'}")
print(f"   QDRANT_API_KEY: {'[OK] Loaded' if QDRANT_API_KEY else '[ERROR] MISSING!'}")

# Exit if keys missing
if not COHERE_API_KEY:
    print("\n[ERROR] COHERE_API_KEY not found!")
    print("   Please create a .env file with your API keys.")
    print("   Or set environment variables manually.")
    exit(1)

# Embedding model (FREE tier compatible)
EMBED_MODEL = "embed-english-light-v3.0"  # 384 dimensions

# =====================================
# INITIALIZE CLIENTS
# =====================================

print("\n[CONNECT] Initializing clients...")

cohere_client = cohere.Client(api_key=COHERE_API_KEY)

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

print("[OK] Clients initialized successfully!")

# =====================================
# EMBEDDING FUNCTIONS
# =====================================

def embed_documents(texts):
    """Embed documents for storage in vector DB"""
    if isinstance(texts, str):
        texts = [texts]

    response = cohere_client.embed(
        model=EMBED_MODEL,
        texts=texts,
        input_type="search_document",
        embedding_types=["float"]
    )

    if hasattr(response, 'embeddings'):
        if hasattr(response.embeddings, 'float'):
            return response.embeddings.float
        return response.embeddings
    return response

def embed_query(query_text):
    """Embed user query for searching"""
    response = cohere_client.embed(
        model=EMBED_MODEL,
        texts=[query_text],
        input_type="search_query",
        embedding_types=["float"]
    )

    if hasattr(response, 'embeddings'):
        if hasattr(response.embeddings, 'float'):
            return response.embeddings.float[0]
        return response.embeddings[0]
    return response[0]

def get_embedding_dimension():
    """Get the embedding dimension from the model"""
    try:
        print("   Testing embedding dimension...")
        test_embedding = embed_documents(["test"])[0]
        dim = len(test_embedding)
        print(f"   [OK] Embedding dimension: {dim}")
        return dim
    except Exception as e:
        print(f"   [WARN] Could not determine embedding dim: {e}")
        if "light" in EMBED_MODEL and "v3" in EMBED_MODEL:
            return 384
        return 1024

# =====================================
# QDRANT COLLECTION
# =====================================

def create_collection(force_recreate=False):
    """Create Qdrant collection"""
    print("\n[DB] Setting up Qdrant collection...")

    collection_exists = qdrant_client.collection_exists(COLLECTION_NAME)

    if collection_exists and force_recreate:
        print(f"   [WARN] Deleting existing collection: {COLLECTION_NAME}")
        qdrant_client.delete_collection(COLLECTION_NAME)
        collection_exists = False

    if not collection_exists:
        dim = get_embedding_dimension()
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=dim,
                distance=Distance.COSINE
            )
        )
        print(f"   [OK] Collection created: {COLLECTION_NAME}")
    else:
        print(f"   [OK] Collection already exists: {COLLECTION_NAME}")

# =====================================
# SAVE TO QDRANT
# =====================================

def save_chunk_to_qdrant(chunk, chunk_id, file_path, file_name=""):
    """Save a single chunk to Qdrant"""
    vector = embed_documents(chunk)[0]

    point = PointStruct(
        id=chunk_id,
        vector=vector,
        payload={
            "content": chunk,
            "file_path": file_path,
            "file_name": file_name,
            "chunk_id": chunk_id,
            "source": "local_file"
        }
    )

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point]
    )

# =====================================
# SEARCH FUNCTION
# =====================================

def search(query, top_k=5):
    """Search for relevant chunks based on user query"""
    query_vector = embed_query(query)

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        with_payload=True
    )

    return results.points  # Return the points list

# =====================================
# CHAT FUNCTION
# =====================================

def chat_with_book(user_query, top_k=5):
    """RAG-based chat: Search relevant chunks and generate answer"""
    print(f"\n[SEARCH] Searching for: {user_query}")

    results = search(user_query, top_k=top_k)

    if not results:
        return {
            "answer": "I couldn't find relevant information in the book.",
            "sources": []
        }

    context_parts = []
    sources = []

    for i, result in enumerate(results, 1):
        text = result.payload.get("content", "")
        file_path = result.payload.get("file_path", "")
        score = getattr(result, 'score', 0)  # Handle score differently for new API

        context_parts.append(f"[Source {i}]\n{text}")
        sources.append({
            "file_path": file_path,
            "score": round(score, 4),
            "excerpt": text[:200] + "..." if len(text) > 200 else text
        })

    context = "\n\n".join(context_parts)

    prompt = f"""You are a helpful assistant for a textbook about Humanoid Robotics and AI.
Answer the user's question based ONLY on the provided context from the book.
If the context doesn't contain enough information, say so.

CONTEXT FROM BOOK:
{context}

USER QUESTION: {user_query}

ANSWER:"""

    response = cohere_client.chat(
        model="command-r-08-2024",
        message=prompt,
        temperature=0.3
    )

    return {
        "answer": response.text,
        "sources": sources
    }

# =====================================
# IMPORT LOCAL INGESTION
# =====================================

def ingest_local_files(force_recreate=False):
    """Run local file ingestion"""
    print("\n" + "="*50)
    print("[FILES] STARTING LOCAL FILE INGESTION")
    print("="*50)

    # Import and run the local ingestion
    from ingestion.local_ingestion import LocalIngestion

    ingestion = LocalIngestion(
        data_dir="backend/data",
        cohere_api_key=COHERE_API_KEY,
        qdrant_url=QDRANT_URL,
        qdrant_api_key=QDRANT_API_KEY
    )

    # Create collection if needed
    create_collection(force_recreate=force_recreate)

    # Run the ingestion
    ingestion.run_ingestion()

def ingest_sitemap(sitemap_url="https://humanoid-robotics-textbook-zeta.vercel.app/sitemap.xml", force_recreate=False):
    """Run sitemap-based ingestion"""
    print("\n" + "="*50)
    print("[SITEMAP] STARTING SITEMAP INGESTION")
    print("="*50)

    # Import and run the Selenium-based sitemap ingestion
    from ingestion.selenium_sitemap_ingestion import SeleniumSitemapIngestion

    ingestion = SeleniumSitemapIngestion(
        sitemap_url=sitemap_url,
        cohere_api_key=COHERE_API_KEY,
        qdrant_url=QDRANT_URL,
        qdrant_api_key=QDRANT_API_KEY
    )

    # Create collection if needed
    create_collection(force_recreate=force_recreate)

    # Run the ingestion
    ingestion.run_ingestion()

# =====================================
# ENTRY POINT
# =====================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "ingest":
            force = "--force" in sys.argv or "-f" in sys.argv
            ingest_local_files(force_recreate=force)

        elif command == "ingest-sitemap":
            force = "--force" in sys.argv or "-f" in sys.argv
            sitemap_url = "https://humanoid-robotics-textbook-zeta.vercel.app/sitemap.xml"
            # Check if a custom sitemap URL was provided
            for arg in sys.argv:
                if arg.startswith("--sitemap="):
                    sitemap_url = arg.split("=", 1)[1]
            ingest_sitemap(sitemap_url=sitemap_url, force_recreate=force)

        elif command == "chat":
            print("\n[BOT] Chat Mode - Type 'quit' to exit")
            while True:
                query = input("\n[INPUT] You: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                if query:
                    result = chat_with_book(query)
                    print(f"\n[BOT] Bot: {result['answer']}")

        elif command == "search":
            if len(sys.argv) > 2:
                query = " ".join(sys.argv[2:])
                results = search(query)
                for r in results:
                    print(f"\nScore: {r.score:.4f}")
                    print(f"URL: {r.payload.get('url', r.payload.get('file_path'))}")
                    print(f"Content: {r.payload.get('content', '')[:200]}...")
        else:
            print("Commands: ingest, ingest-sitemap [--sitemap=URL], chat, search <query>")
    else:
        # Default to sitemap ingestion instead of local files
        ingest_sitemap()