import cohere
import os
from typing import List
from dotenv import load_dotenv
from pathlib import Path

# Load backend .env specifically
backend_dir = Path(__file__).parent.parent
load_dotenv(backend_dir / ".env", override=True)

co = cohere.Client(os.getenv("COHERE_API_KEY"))

BATCH_SIZE = 96  # Cohere max

def embed_chunks(chunks: List[dict]) -> List[dict]:
    """Add 'embedding' key to each chunk dict."""
    texts = [c["text"] for c in chunks]
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        try:
            response = co.embed(
                texts=batch,
                model="embed-english-v3.0",
                input_type="search_document"
            )
            all_embeddings.extend(response.embeddings)
        except Exception as e:
            print(f"[EMBEDDER ERROR] batch {i}: {e}")
            all_embeddings.extend([[0.0] * 1024] * len(batch))

    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding

    return chunks
