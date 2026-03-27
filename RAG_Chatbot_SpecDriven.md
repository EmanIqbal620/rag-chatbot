# RAG Chatbot — Spec-Driven Development Master Document
> Complete build guide for Qwen (or any LLM) to execute step-by-step without extra prompting.

---

## 📋 HOW TO USE THIS DOCUMENT

This document is self-contained. Give it to Qwen and say:
> "Read this document fully. Then execute Phase 1. When done, confirm completion and wait for me to say 'proceed to Phase 2'."

Each phase has its own **Constitution → Specify → Plan → Tasks → Implementation** cycle.

---

---

# 🏛️ GLOBAL CONSTITUTION (sp.constitution)

> These rules govern ALL phases of the RAG Chatbot build. Never violate them.

## Identity & Stack

| Layer | Technology |
|---|---|
| Embeddings | Cohere `embed-english-v3.0` |
| Vector DB | Qdrant Cloud Free Tier |
| Relational DB | Neon Serverless Postgres |
| Backend Framework | FastAPI (Python 3.11+) |
| Agent SDK | OpenAI Agents SDK |
| Frontend Widget | Vanilla JS (embeddable in book HTML) |
| Deployment | Local dev first, then Render/Railway |

## Non-Negotiable Rules

1. **Every module has its own `sp.specify`, `sp.plan`, `sp.tasks`** before any code is written.
2. **No hardcoded secrets** — all keys go in `.env` and loaded via `python-dotenv`.
3. **All async functions** — FastAPI endpoints must use `async def`.
4. **Error handling on every external call** — Qdrant, Neon, Cohere, OpenAI must have try/except.
5. **Chunking strategy is fixed**: 500 tokens, 50-token overlap, sentence-boundary aware.
6. **Metadata always stored alongside vectors**: `{source_url, chunk_index, page_title, char_start, char_end}`.
7. **Selected-text queries are prefixed** with `[SELECTED]: ` before retrieval.
8. **All endpoints return JSON** with `{status, data, error}` envelope.
9. **CORS must be configured** on FastAPI to allow the book's domain.
10. **No phase is "done" until its test suite passes**.

## Project Folder Structure (Enforced)

```
rag-chatbot/
├── .env                        # Secrets (gitignored)
├── .env.example                # Template (committed)
├── requirements.txt
├── README.md
│
├── ingestion/                  # Phase 1
│   ├── scraper.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── vector_store.py
│   └── db_store.py
│
├── retrieval/                  # Phase 2
│   ├── retriever.py
│   └── test_pipeline.py
│
├── agent/                      # Phase 3
│   ├── rag_agent.py
│   └── tools.py
│
├── api/                        # Phase 3 (FastAPI)
│   ├── main.py
│   ├── routes/
│   │   ├── ingest.py
│   │   └── chat.py
│   └── models.py
│
└── frontend/                   # Phase 4
    ├── chat-widget.js
    ├── chat-widget.css
    └── embed.html
```

## Environment Variables (`.env.example`)

```env
# Cohere
COHERE_API_KEY=your_cohere_key

# Qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_key
QDRANT_COLLECTION_NAME=book_chunks

# Neon Postgres
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require

# OpenAI
OPENAI_API_KEY=your_openai_key

# FastAPI
CORS_ORIGINS=http://localhost:3000,https://yourbook.com
```

---

---

# 🔵 PHASE 1 — Ingestion Pipeline

> **Goal**: Crawl all book URLs → chunk text → generate Cohere embeddings → store vectors in Qdrant → store metadata in Neon Postgres.

---

## Phase 1 — sp.specify

### What This Phase Builds

A one-time ingestion pipeline that:
1. Accepts a list of book page URLs
2. Scrapes each URL for clean text content
3. Splits text into overlapping chunks (500 tokens, 50 overlap)
4. Generates embeddings via Cohere `embed-english-v3.0`
5. Stores vectors + metadata in Qdrant Cloud
6. Stores chunk text + metadata in Neon Postgres

### Inputs

- `urls.txt` — list of book page URLs, one per line

### Outputs

- Qdrant collection `book_chunks` populated with vectors
- Neon Postgres table `chunks` populated with text + metadata
- Console log showing counts of processed chunks

### What It Does NOT Do

- Does NOT serve any API (that is Phase 3)
- Does NOT handle PDFs (only HTML pages)
- Does NOT re-embed already-stored URLs (idempotent check via Neon)

### Success Criteria

- All URLs scraped without HTTP errors
- Chunk count in Qdrant == chunk count in Neon
- A sample similarity search on Qdrant returns relevant results

---

## Phase 1 — sp.plan

### Step-by-Step Build Plan

```
1. Setup project skeleton
   - Create rag-chatbot/ folder
   - Create .env, .env.example, requirements.txt
   - Install: requests, beautifulsoup4, cohere, qdrant-client, psycopg2-binary,
             python-dotenv, tiktoken, langchain-text-splitters

2. Build scraper.py
   - Input: list of URLs
   - Use requests + BeautifulSoup
   - Extract: page title, main body text (strip nav/footer/scripts)
   - Output: list of {url, title, raw_text}

3. Build chunker.py
   - Use RecursiveCharacterTextSplitter from langchain
   - chunk_size=500 (tokens via tiktoken), chunk_overlap=50
   - Each chunk returns: {text, chunk_index, source_url, page_title,
                          char_start, char_end}

4. Build embedder.py
   - Init Cohere client
   - Batch embed chunks (max 96 per call — Cohere limit)
   - input_type="search_document"
   - Returns list of float vectors (1024-dim for embed-english-v3.0)

5. Build vector_store.py
   - Init Qdrant client (cloud URL + API key)
   - Create collection if not exists (vector size=1024, cosine distance)
   - Upsert points: {id=uuid, vector=embedding, payload=metadata}

6. Build db_store.py
   - Connect to Neon via psycopg2
   - Create table if not exists:
       CREATE TABLE IF NOT EXISTS chunks (
         id UUID PRIMARY KEY,
         source_url TEXT,
         page_title TEXT,
         chunk_index INT,
         chunk_text TEXT,
         char_start INT,
         char_end INT,
         created_at TIMESTAMPTZ DEFAULT NOW()
       );
   - Insert chunk records (skip if url+chunk_index already exists)

7. Build ingestion/run.py (orchestrator)
   - Read urls.txt
   - For each URL: scrape → chunk → embed → store vector → store db
   - Print progress bar
   - Print final summary: X URLs, Y chunks processed
```

---

## Phase 1 — sp.tasks

### Task List (Execute in Order)

- [ ] **T1.1** Create `rag-chatbot/` directory and subdirectories
- [ ] **T1.2** Create `requirements.txt` with all Phase 1 dependencies
- [ ] **T1.3** Create `.env.example` with all variable names
- [ ] **T1.4** Create `ingestion/scraper.py` — URL → `{url, title, raw_text}`
- [ ] **T1.5** Create `ingestion/chunker.py` — text → list of chunk dicts
- [ ] **T1.6** Create `ingestion/embedder.py` — chunks → embeddings (batched)
- [ ] **T1.7** Create `ingestion/vector_store.py` — init Qdrant + upsert
- [ ] **T1.8** Create `ingestion/db_store.py` — init Neon + insert chunks
- [ ] **T1.9** Create `ingestion/run.py` — orchestrate all steps
- [ ] **T1.10** Create `urls.txt` with 3 test URLs from the book
- [ ] **T1.11** Run `python ingestion/run.py` and verify output
- [ ] **T1.12** Log into Qdrant Cloud dashboard and confirm vectors exist
- [ ] **T1.13** Query Neon with `SELECT COUNT(*) FROM chunks;` and confirm count matches

### Acceptance Test (Must Pass)

```python
# Run this after ingestion:
from qdrant_client import QdrantClient
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
results = client.search(
    collection_name="book_chunks",
    query_vector=<embed one test query>,
    limit=3
)
assert len(results) == 3
print("Phase 1 PASSED ✅")
```

---

## Phase 1 — sp.implementation

### `requirements.txt`

```txt
requests==2.31.0
beautifulsoup4==4.12.3
cohere==5.3.3
qdrant-client==1.9.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
tiktoken==0.7.0
langchain-text-splitters==0.2.0
```

### `ingestion/scraper.py`

```python
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

def scrape_url(url: str) -> Dict:
    """Scrape a single URL and return clean text."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise elements
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()

        title = soup.find("title")
        page_title = title.get_text(strip=True) if title else url

        # Get main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        raw_text = main.get_text(separator="\n", strip=True) if main else ""

        return {"url": url, "title": page_title, "raw_text": raw_text}
    except Exception as e:
        print(f"[SCRAPER ERROR] {url}: {e}")
        return {"url": url, "title": "", "raw_text": ""}

def scrape_urls(urls: List[str]) -> List[Dict]:
    return [scrape_url(u) for u in urls if u.strip()]
```

### `ingestion/chunker.py`

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken
import uuid
from typing import List, Dict

ENCODER = tiktoken.get_encoding("cl100k_base")

def token_len(text: str) -> int:
    return len(ENCODER.encode(text))

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    length_function=token_len,
    separators=["\n\n", "\n", ". ", " ", ""]
)

def chunk_document(doc: Dict) -> List[Dict]:
    """Split a scraped document into chunks with metadata."""
    if not doc["raw_text"]:
        return []

    texts = splitter.split_text(doc["raw_text"])
    chunks = []
    char_cursor = 0

    for i, text in enumerate(texts):
        char_start = doc["raw_text"].find(text, char_cursor)
        char_end = char_start + len(text) if char_start != -1 else -1
        if char_start != -1:
            char_cursor = char_start + 1

        chunks.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "chunk_index": i,
            "source_url": doc["url"],
            "page_title": doc["title"],
            "char_start": char_start,
            "char_end": char_end
        })
    return chunks
```

### `ingestion/embedder.py`

```python
import cohere
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()
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
```

### `ingestion/vector_store.py`

```python
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "book_chunks")
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
                "chunk_index": c["chunk_index"],
                "char_start": c["char_start"],
                "char_end": c["char_end"],
                "text": c["text"]
            }
        )
        for c in chunks
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"[QDRANT] Upserted {len(points)} vectors")
```

### `ingestion/db_store.py`

```python
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def init_table():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id UUID PRIMARY KEY,
                source_url TEXT,
                page_title TEXT,
                chunk_index INT,
                chunk_text TEXT,
                char_start INT,
                char_end INT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(source_url, chunk_index)
            );
        """)
    conn.commit()
    conn.close()
    print("[NEON] Table initialized")

def insert_chunks(chunks: list):
    conn = get_conn()
    rows = [
        (c["id"], c["source_url"], c["page_title"], c["chunk_index"],
         c["text"], c["char_start"], c["char_end"])
        for c in chunks
    ]
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO chunks (id, source_url, page_title, chunk_index,
                                chunk_text, char_start, char_end)
            VALUES %s
            ON CONFLICT (source_url, chunk_index) DO NOTHING;
        """, rows)
    conn.commit()
    conn.close()
    print(f"[NEON] Inserted {len(rows)} chunks")
```

### `ingestion/run.py`

```python
from scraper import scrape_urls
from chunker import chunk_document
from embedder import embed_chunks
from vector_store import init_collection, upsert_chunks
from db_store import init_table, insert_chunks

def run_ingestion(urls_file: str = "urls.txt"):
    with open(urls_file) as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"[RUN] Starting ingestion for {len(urls)} URLs...")

    init_collection()
    init_table()

    total_chunks = 0
    for url in urls:
        print(f"\n[URL] {url}")
        doc = scrape_urls([url])[0]
        if not doc["raw_text"]:
            print("  → Skipped (no text)")
            continue

        chunks = chunk_document(doc)
        chunks = embed_chunks(chunks)
        upsert_chunks(chunks)
        insert_chunks(chunks)
        total_chunks += len(chunks)
        print(f"  → {len(chunks)} chunks processed")

    print(f"\n✅ Ingestion complete: {len(urls)} URLs, {total_chunks} total chunks")

if __name__ == "__main__":
    run_ingestion()
```

---

---

# 🟢 PHASE 2 — Retrieval Pipeline & Testing

> **Goal**: Build a retriever that takes a query string, embeds it with Cohere, searches Qdrant, and returns the top-k most relevant chunks. Verify the full pipeline end-to-end.

---

## Phase 2 — sp.specify

### What This Phase Builds

A `retriever.py` module and a test script that:
1. Takes a user query string (plain question or `[SELECTED]: <text>`)
2. Embeds the query using Cohere `input_type="search_query"`
3. Searches Qdrant for top-5 similar chunks
4. Returns structured results: `[{text, source_url, page_title, score}]`
5. Test script runs 5 test queries and prints results

### Success Criteria

- Top result for a direct quote from the book has score > 0.75
- Selected-text queries return the correct source chunk
- Response time < 2 seconds per query

---

## Phase 2 — sp.plan

```
1. Build retrieval/retriever.py
   - embed_query(query: str) → vector using Cohere search_query input_type
   - search(query: str, top_k=5) → list of result dicts
   - handle [SELECTED]: prefix — strip it and use as-is for embedding

2. Build retrieval/test_pipeline.py
   - 5 test queries covering:
       a. Direct content question
       b. Conceptual question
       c. Selected text query (prefixed)
       d. Out-of-scope question (should return low scores)
       e. Short 2-word query
   - Print results in table format: rank, score, source, snippet
   - Assert at least 3 of 5 queries return score > 0.5
```

---

## Phase 2 — sp.tasks

- [ ] **T2.1** Create `retrieval/retriever.py`
- [ ] **T2.2** Create `retrieval/test_pipeline.py` with 5 test queries
- [ ] **T2.3** Run test pipeline and capture output
- [ ] **T2.4** Confirm scores and tune top_k if needed

---

## Phase 2 — sp.implementation

### `retrieval/retriever.py`

```python
import os
import cohere
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

co = cohere.Client(os.getenv("COHERE_API_KEY"))
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)
COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "book_chunks")

def embed_query(query: str) -> list:
    """Embed a query string for similarity search."""
    # Strip the selected-text prefix if present
    clean_query = query.replace("[SELECTED]: ", "").strip()
    response = co.embed(
        texts=[clean_query],
        model="embed-english-v3.0",
        input_type="search_query"
    )
    return response.embeddings[0]

def search(query: str, top_k: int = 5) -> list:
    """Return top-k relevant chunks for a query."""
    try:
        vector = embed_query(query)
        results = qdrant.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=top_k
        )
        return [
            {
                "text": r.payload.get("text", ""),
                "source_url": r.payload.get("source_url", ""),
                "page_title": r.payload.get("page_title", ""),
                "chunk_index": r.payload.get("chunk_index", 0),
                "score": round(r.score, 4)
            }
            for r in results
        ]
    except Exception as e:
        print(f"[RETRIEVER ERROR] {e}")
        return []
```

### `retrieval/test_pipeline.py`

```python
import sys
sys.path.append(".")
from retriever import search

TEST_QUERIES = [
    "What is the main topic of this book?",
    "Explain the key concepts discussed in chapter one",
    "[SELECTED]: The author defines RAG as a technique that combines retrieval with generation",
    "What is the capital of France?",  # Out of scope — expect low score
    "implementation steps"
]

def run_tests():
    print("=" * 60)
    print("RAG PIPELINE TEST")
    print("=" * 60)
    passed = 0

    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\nQuery {i}: {query[:60]}...")
        results = search(query, top_k=3)

        if not results:
            print("  ⚠️  No results returned")
            continue

        top = results[0]
        print(f"  Top Score : {top['score']}")
        print(f"  Source    : {top['source_url']}")
        print(f"  Snippet   : {top['text'][:100]}...")

        if i != 4 and top["score"] > 0.5:  # Skip out-of-scope test
            passed += 1

    print(f"\n{'=' * 60}")
    print(f"Result: {passed}/4 queries passed (score > 0.5)")
    if passed >= 3:
        print("✅ Phase 2 PASSED")
    else:
        print("❌ Phase 2 FAILED — check embeddings and collection")

if __name__ == "__main__":
    run_tests()
```

---

---

# 🟡 PHASE 3 — OpenAI Agent + FastAPI Backend

> **Goal**: Build a RAG-aware agent using OpenAI Agents SDK and expose two FastAPI endpoints: `/ingest` (trigger ingestion) and `/chat` (streaming chat with retrieval).

---

## Phase 3 — sp.specify

### What This Phase Builds

1. **`agent/rag_agent.py`** — OpenAI Agent with a `retrieve_context` tool
2. **`api/main.py`** — FastAPI app with CORS
3. **`api/routes/chat.py`** — POST `/chat` endpoint
4. **`api/routes/ingest.py`** — POST `/ingest` endpoint
5. **`api/models.py`** — Pydantic request/response models

### API Contract

```
POST /chat
Body: {
  "question": "string",
  "selected_text": "string | null"
}
Response: {
  "status": "ok",
  "data": {
    "answer": "string",
    "sources": [{source_url, page_title, score}]
  },
  "error": null
}

POST /ingest
Body: { "urls": ["url1", "url2"] }
Response: { "status": "ok", "data": {"chunks_processed": int}, "error": null }
```

### Agent Behavior

- If `selected_text` is provided, prepend `[SELECTED]: <selected_text>\n\nQuestion: <question>`
- Retrieve top-5 chunks from Qdrant
- Inject chunks as system context
- Answer ONLY based on retrieved context
- If no relevant context: "I couldn't find that in the book."

---

## Phase 3 — sp.plan

```
1. Build agent/tools.py
   - retrieve_context(query: str) tool
   - Returns formatted string of top-5 chunks for the agent

2. Build agent/rag_agent.py
   - Create OpenAI Agent with retrieve_context as a tool
   - System prompt: "You are a book assistant. Answer ONLY from context."
   - run_agent(question, selected_text) → {answer, sources}

3. Build api/models.py
   - ChatRequest(question: str, selected_text: Optional[str])
   - ChatResponse(status, data, error)
   - IngestRequest(urls: List[str])

4. Build api/routes/chat.py
   - POST /chat
   - Validate input
   - Call run_agent()
   - Return ChatResponse

5. Build api/routes/ingest.py
   - POST /ingest
   - Call ingestion pipeline with provided URLs
   - Return chunk count

6. Build api/main.py
   - Include both routers
   - Configure CORS
   - Add /health endpoint

7. Test with curl or httpie
```

---

## Phase 3 — sp.tasks

- [ ] **T3.1** Install additional deps: `openai-agents fastapi uvicorn pydantic`
- [ ] **T3.2** Create `agent/tools.py`
- [ ] **T3.3** Create `agent/rag_agent.py`
- [ ] **T3.4** Create `api/models.py`
- [ ] **T3.5** Create `api/routes/chat.py`
- [ ] **T3.6** Create `api/routes/ingest.py`
- [ ] **T3.7** Create `api/main.py`
- [ ] **T3.8** Run `uvicorn api.main:app --reload --port 8000`
- [ ] **T3.9** Test `/health` endpoint
- [ ] **T3.10** Test `/chat` with a sample question
- [ ] **T3.11** Test `/chat` with selected_text populated

---

## Phase 3 — sp.implementation

### `agent/tools.py`

```python
import sys
sys.path.append(".")
from retrieval.retriever import search

def retrieve_context(query: str) -> str:
    """Tool: Retrieve relevant book chunks for a query."""
    results = search(query, top_k=5)
    if not results:
        return "No relevant content found in the book."

    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(
            f"[Source {i}] {r['page_title']} ({r['source_url']})\n{r['text']}"
        )
    return "\n\n---\n\n".join(context_parts)
```

### `agent/rag_agent.py`

```python
import os
from openai import AsyncOpenAI
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from .tools import retrieve_context

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

retrieve_tool = function_tool(retrieve_context)

SYSTEM_PROMPT = """You are a helpful assistant for a published book.
Your ONLY job is to answer questions based on the book's content.
You MUST use the retrieve_context tool before answering any question.
If the retrieved context does not contain the answer, say:
"I couldn't find that information in the book."
Never make up information. Always cite the source URL in your answer."""

book_agent = Agent(
    name="BookRAGAgent",
    instructions=SYSTEM_PROMPT,
    tools=[retrieve_tool],
    model="gpt-4o-mini"
)

async def run_agent(question: str, selected_text: str = None) -> dict:
    """Run the RAG agent and return answer + sources."""
    if selected_text:
        full_query = f"[SELECTED]: {selected_text}\n\nQuestion: {question}"
    else:
        full_query = question

    try:
        result = await Runner.run(book_agent, full_query)
        # Extract sources from retrieval (search again for metadata)
        from retrieval.retriever import search
        sources = search(full_query, top_k=5)
        source_list = [
            {"source_url": s["source_url"],
             "page_title": s["page_title"],
             "score": s["score"]}
            for s in sources
        ]
        return {
            "answer": result.final_output,
            "sources": source_list
        }
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "sources": []}
```

### `api/models.py`

```python
from pydantic import BaseModel
from typing import Optional, List, Any

class ChatRequest(BaseModel):
    question: str
    selected_text: Optional[str] = None

class IngestRequest(BaseModel):
    urls: List[str]

class APIResponse(BaseModel):
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
```

### `api/routes/chat.py`

```python
from fastapi import APIRouter
from api.models import ChatRequest, APIResponse
from agent.rag_agent import run_agent

router = APIRouter()

@router.post("/chat", response_model=APIResponse)
async def chat(request: ChatRequest):
    if not request.question.strip():
        return APIResponse(status="error", error="Question cannot be empty")
    try:
        result = await run_agent(request.question, request.selected_text)
        return APIResponse(status="ok", data=result)
    except Exception as e:
        return APIResponse(status="error", error=str(e))
```

### `api/routes/ingest.py`

```python
from fastapi import APIRouter, BackgroundTasks
from api.models import IngestRequest, APIResponse
import sys
sys.path.append(".")
from ingestion.scraper import scrape_urls
from ingestion.chunker import chunk_document
from ingestion.embedder import embed_chunks
from ingestion.vector_store import init_collection, upsert_chunks
from ingestion.db_store import init_table, insert_chunks

router = APIRouter()

@router.post("/ingest", response_model=APIResponse)
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    def run():
        init_collection()
        init_table()
        total = 0
        for url in request.urls:
            docs = scrape_urls([url])
            for doc in docs:
                chunks = chunk_document(doc)
                chunks = embed_chunks(chunks)
                upsert_chunks(chunks)
                insert_chunks(chunks)
                total += len(chunks)
        print(f"[INGEST BG] Done: {total} chunks")

    background_tasks.add_task(run)
    return APIResponse(
        status="ok",
        data={"message": f"Ingesting {len(request.urls)} URLs in background"}
    )
```

### `api/main.py`

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.routes.chat import router as chat_router
from api.routes.ingest import router as ingest_router

load_dotenv()

app = FastAPI(title="Book RAG Chatbot API", version="1.0.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(ingest_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Book RAG Chatbot"}
```

### Start Command

```bash
uvicorn api.main:app --reload --port 8000
```

### Test Commands (run after server starts)

```bash
# Health check
curl http://localhost:8000/health

# Chat test
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this book about?"}'

# Selected text test
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Can you explain this?", "selected_text": "RAG combines retrieval with generation"}'
```

---

---

# 🔴 PHASE 4 — Frontend Chat Widget Integration

> **Goal**: Build an embeddable JS chat widget that sits on the book's HTML pages, captures user-selected text, and communicates with the FastAPI backend.

---

## Phase 4 — sp.specify

### What This Phase Builds

1. **`frontend/chat-widget.js`** — Embeddable vanilla JS widget
2. **`frontend/chat-widget.css`** — Widget styles
3. **`frontend/embed.html`** — Demo page showing the widget embedded in book content

### Widget Features

- Floating chat button (bottom-right corner)
- Opens a chat panel with message history
- Detects text selected on the page and shows "Ask about this" button
- Sends `{question, selected_text}` to `/api/v1/chat`
- Displays answer and source links
- Loading state (typing indicator)
- Error state with retry
- Works on any HTML page via single `<script>` tag include

### Embed Instructions (for book pages)

```html
<!-- Add before </body> on any book page -->
<script>
  window.RAGChatConfig = {
    apiUrl: "http://localhost:8000/api/v1",
    botName: "Book Assistant",
    placeholder: "Ask a question about this book..."
  };
</script>
<script src="/frontend/chat-widget.js"></script>
<link rel="stylesheet" href="/frontend/chat-widget.css">
```

---

## Phase 4 — sp.plan

```
1. Build chat-widget.css
   - Floating button style
   - Chat panel (400px wide, 500px tall)
   - Message bubbles (user = right, bot = left)
   - Source chips below bot messages
   - "Ask about selection" floating toolbar
   - Mobile responsive

2. Build chat-widget.js
   - On load: inject HTML structure into DOM
   - Toggle open/close on button click
   - Selection detection: document.addEventListener("mouseup")
   - If selection > 5 words: show "Ask about this ✨" mini button
   - On send: POST to apiUrl/chat with {question, selected_text}
   - Render markdown-like responses (bold, line breaks)
   - Show source links under answer
   - Typing indicator while waiting

3. Build embed.html
   - Sample book page with 3 paragraphs of text
   - Widget included at bottom
   - Instructions comment at top
```

---

## Phase 4 — sp.tasks

- [ ] **T4.1** Create `frontend/chat-widget.css`
- [ ] **T4.2** Create `frontend/chat-widget.js`
- [ ] **T4.3** Create `frontend/embed.html` demo page
- [ ] **T4.4** Open `embed.html` in browser with backend running
- [ ] **T4.5** Test: type a question → get answer
- [ ] **T4.6** Test: select text → click "Ask about this" → get answer
- [ ] **T4.7** Test: mobile viewport (375px)
- [ ] **T4.8** Copy embed code into actual book HTML pages

---

## Phase 4 — sp.implementation

### `frontend/chat-widget.css`

```css
:root {
  --rag-primary: #4f46e5;
  --rag-primary-dark: #3730a3;
  --rag-bg: #ffffff;
  --rag-surface: #f8fafc;
  --rag-border: #e2e8f0;
  --rag-text: #1e293b;
  --rag-muted: #64748b;
  --rag-user-bg: #4f46e5;
  --rag-user-text: #ffffff;
  --rag-bot-bg: #f1f5f9;
  --rag-bot-text: #1e293b;
  --rag-shadow: 0 20px 60px rgba(0,0,0,0.15);
  --rag-radius: 16px;
}

#rag-chat-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--rag-primary);
  color: white;
  border: none;
  cursor: pointer;
  font-size: 24px;
  box-shadow: 0 4px 20px rgba(79,70,229,0.4);
  z-index: 9999;
  transition: transform 0.2s, background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
#rag-chat-btn:hover { background: var(--rag-primary-dark); transform: scale(1.1); }

#rag-chat-panel {
  position: fixed;
  bottom: 90px;
  right: 24px;
  width: 400px;
  height: 520px;
  background: var(--rag-bg);
  border-radius: var(--rag-radius);
  box-shadow: var(--rag-shadow);
  display: flex;
  flex-direction: column;
  z-index: 9998;
  overflow: hidden;
  border: 1px solid var(--rag-border);
  transition: opacity 0.2s, transform 0.2s;
}
#rag-chat-panel.hidden {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
  pointer-events: none;
}

#rag-chat-header {
  background: var(--rag-primary);
  color: white;
  padding: 16px 20px;
  font-weight: 600;
  font-size: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
#rag-chat-header button {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 18px;
  opacity: 0.8;
}

#rag-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--rag-surface);
}

.rag-msg {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}
.rag-msg.user {
  align-self: flex-end;
  background: var(--rag-user-bg);
  color: var(--rag-user-text);
  border-bottom-right-radius: 4px;
}
.rag-msg.bot {
  align-self: flex-start;
  background: var(--rag-bot-bg);
  color: var(--rag-bot-text);
  border-bottom-left-radius: 4px;
}

.rag-sources {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.rag-source-chip {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 20px;
  background: white;
  border: 1px solid var(--rag-border);
  color: var(--rag-primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.rag-typing {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 12px 14px;
  background: var(--rag-bot-bg);
  border-radius: 12px;
  border-bottom-left-radius: 4px;
  align-self: flex-start;
}
.rag-typing span {
  width: 7px;
  height: 7px;
  background: var(--rag-muted);
  border-radius: 50%;
  animation: ragBounce 1.2s infinite;
}
.rag-typing span:nth-child(2) { animation-delay: 0.2s; }
.rag-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes ragBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

#rag-chat-input-area {
  padding: 12px;
  border-top: 1px solid var(--rag-border);
  display: flex;
  gap: 8px;
  background: white;
}
#rag-chat-input {
  flex: 1;
  border: 1px solid var(--rag-border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  resize: none;
  outline: none;
  font-family: inherit;
  max-height: 80px;
  overflow-y: auto;
}
#rag-chat-input:focus { border-color: var(--rag-primary); }
#rag-send-btn {
  background: var(--rag-primary);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.2s;
}
#rag-send-btn:hover { background: var(--rag-primary-dark); }
#rag-send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

#rag-selection-toolbar {
  position: fixed;
  z-index: 10000;
  display: none;
}
#rag-ask-selection-btn {
  background: var(--rag-primary);
  color: white;
  border: none;
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(79,70,229,0.35);
  white-space: nowrap;
}

#rag-selected-banner {
  font-size: 12px;
  color: var(--rag-muted);
  padding: 4px 12px;
  background: #eef2ff;
  border-bottom: 1px solid var(--rag-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
#rag-clear-selection { cursor: pointer; font-size: 14px; }

@media (max-width: 480px) {
  #rag-chat-panel {
    width: calc(100vw - 16px);
    right: 8px;
    bottom: 80px;
    height: 60vh;
  }
}
```

### `frontend/chat-widget.js`

```javascript
(function () {
  const config = window.RAGChatConfig || {};
  const API_URL = config.apiUrl || "http://localhost:8000/api/v1";
  const BOT_NAME = config.botName || "Book Assistant";
  const PLACEHOLDER = config.placeholder || "Ask about the book...";

  let selectedText = "";
  let isOpen = false;

  // --- Inject HTML ---
  const style = document.createElement("link");
  style.rel = "stylesheet";
  style.href = (config.cssUrl || "/frontend/chat-widget.css");
  document.head.appendChild(style);

  document.body.insertAdjacentHTML("beforeend", `
    <button id="rag-chat-btn" title="Ask the book assistant">💬</button>
    <div id="rag-chat-panel" class="hidden">
      <div id="rag-chat-header">
        <span>${BOT_NAME}</span>
        <button id="rag-close-btn">✕</button>
      </div>
      <div id="rag-selected-banner" style="display:none">
        <span id="rag-selected-preview"></span>
        <span id="rag-clear-selection">✕</span>
      </div>
      <div id="rag-chat-messages">
        <div class="rag-msg bot">👋 Hi! I can answer questions about this book. Select any text and click "Ask about this" to ask about a specific passage.</div>
      </div>
      <div id="rag-chat-input-area">
        <textarea id="rag-chat-input" rows="1" placeholder="${PLACEHOLDER}"></textarea>
        <button id="rag-send-btn">➤</button>
      </div>
    </div>
    <div id="rag-selection-toolbar">
      <button id="rag-ask-selection-btn">✨ Ask about this</button>
    </div>
  `);

  // --- Elements ---
  const btn = document.getElementById("rag-chat-btn");
  const panel = document.getElementById("rag-chat-panel");
  const closeBtn = document.getElementById("rag-close-btn");
  const messages = document.getElementById("rag-chat-messages");
  const input = document.getElementById("rag-chat-input");
  const sendBtn = document.getElementById("rag-send-btn");
  const toolbar = document.getElementById("rag-selection-toolbar");
  const askSelBtn = document.getElementById("rag-ask-selection-btn");
  const banner = document.getElementById("rag-selected-banner");
  const preview = document.getElementById("rag-selected-preview");
  const clearSel = document.getElementById("rag-clear-selection");

  // --- Toggle ---
  btn.addEventListener("click", () => {
    isOpen = !isOpen;
    panel.classList.toggle("hidden", !isOpen);
    btn.textContent = isOpen ? "✕" : "💬";
  });
  closeBtn.addEventListener("click", () => {
    isOpen = false;
    panel.classList.add("hidden");
    btn.textContent = "💬";
  });

  // --- Text Selection Detection ---
  document.addEventListener("mouseup", (e) => {
    if (panel.contains(e.target)) return;
    const sel = window.getSelection();
    const text = sel ? sel.toString().trim() : "";
    if (text.split(" ").length >= 5) {
      const range = sel.getRangeAt(0).getBoundingClientRect();
      toolbar.style.display = "block";
      toolbar.style.left = (range.left + window.scrollX) + "px";
      toolbar.style.top = (range.top + window.scrollY - 44) + "px";
      toolbar._pendingText = text;
    } else {
      toolbar.style.display = "none";
    }
  });

  askSelBtn.addEventListener("click", () => {
    selectedText = toolbar._pendingText || "";
    toolbar.style.display = "none";
    if (selectedText) {
      banner.style.display = "flex";
      preview.textContent = "📌 " + selectedText.slice(0, 60) + (selectedText.length > 60 ? "…" : "");
      isOpen = true;
      panel.classList.remove("hidden");
      btn.textContent = "✕";
      input.focus();
    }
  });

  clearSel.addEventListener("click", () => {
    selectedText = "";
    banner.style.display = "none";
  });

  // --- Send Message ---
  function addMessage(text, role, sources) {
    const div = document.createElement("div");
    div.className = `rag-msg ${role}`;
    div.innerHTML = text.replace(/\n/g, "<br>");
    if (sources && sources.length) {
      const chips = document.createElement("div");
      chips.className = "rag-sources";
      sources.slice(0, 3).forEach(s => {
        const a = document.createElement("a");
        a.className = "rag-source-chip";
        a.href = s.source_url;
        a.target = "_blank";
        a.title = s.page_title;
        a.textContent = "📄 " + (s.page_title || s.source_url).slice(0, 30);
        chips.appendChild(a);
      });
      div.appendChild(chips);
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addTyping() {
    const div = document.createElement("div");
    div.className = "rag-typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    div.id = "rag-typing-indicator";
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById("rag-typing-indicator");
    if (t) t.remove();
  }

  async function sendMessage() {
    const question = input.value.trim();
    if (!question) return;

    addMessage(question, "user");
    input.value = "";
    sendBtn.disabled = true;
    addTyping();

    const body = { question };
    if (selectedText) body.selected_text = selectedText;

    try {
      const resp = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const json = await resp.json();
      removeTyping();
      if (json.status === "ok") {
        addMessage(json.data.answer, "bot", json.data.sources);
      } else {
        addMessage("⚠️ " + (json.error || "Something went wrong."), "bot");
      }
    } catch (e) {
      removeTyping();
      addMessage("⚠️ Could not reach the server. Is the backend running?", "bot");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
})();
```

### `frontend/embed.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Book Demo — RAG Chatbot</title>
  <style>
    body { font-family: Georgia, serif; max-width: 760px; margin: 40px auto; padding: 0 20px; color: #1e293b; line-height: 1.8; }
    h1 { color: #4f46e5; }
    h2 { color: #334155; margin-top: 2em; }
    p { margin-bottom: 1.2em; }
    .tip { background: #eef2ff; border-left: 4px solid #4f46e5; padding: 12px 16px; border-radius: 4px; font-size: 14px; color: #3730a3; }
  </style>
</head>
<body>
  <h1>Chapter 1: Introduction to RAG</h1>
  <div class="tip">💡 <strong>Try it:</strong> Select any text on this page, then click "✨ Ask about this" — or click the chat button (bottom-right).</div>

  <h2>What is Retrieval-Augmented Generation?</h2>
  <p>Retrieval-Augmented Generation (RAG) is an AI technique that enhances large language models by grounding their responses in external knowledge. Instead of relying solely on patterns learned during training, a RAG system actively retrieves relevant documents at inference time and uses them as context for generation.</p>

  <p>The core insight behind RAG is simple: language models are excellent at reasoning and synthesis, but they cannot update their knowledge after training. By pairing a retrieval component with a generation model, we get the best of both worlds — dynamic, up-to-date information combined with fluent, coherent language generation.</p>

  <h2>The Three Pillars</h2>
  <p>Every RAG system has three essential components. The first is the <strong>knowledge base</strong> — a collection of documents, articles, or data that the system can search. The second is the <strong>retriever</strong>, which finds the most relevant pieces of information given a user query. The third is the <strong>generator</strong>, a language model that uses the retrieved context to produce a final answer.</p>

  <!-- RAG Chat Widget -->
  <script>
    window.RAGChatConfig = {
      apiUrl: "http://localhost:8000/api/v1",
      botName: "Book Assistant",
      placeholder: "Ask about this chapter..."
    };
  </script>
  <script src="chat-widget.js"></script>
  <link rel="stylesheet" href="chat-widget.css">
</body>
</html>
```

---

---

# ✅ MASTER CHECKLIST

## Phase 1 — Ingestion
- [ ] Project structure created
- [ ] `.env` filled with all keys
- [ ] `scraper.py` working
- [ ] `chunker.py` working
- [ ] `embedder.py` working
- [ ] `vector_store.py` working
- [ ] `db_store.py` working
- [ ] `run.py` processes all URLs
- [ ] Qdrant dashboard shows vectors
- [ ] Neon shows rows in `chunks` table

## Phase 2 — Retrieval
- [ ] `retriever.py` working
- [ ] Test pipeline passes 3/4 queries

## Phase 3 — Agent + API
- [ ] Agent answers questions from book context
- [ ] FastAPI server starts on port 8000
- [ ] `/health` returns `{status: "ok"}`
- [ ] `/chat` returns answer + sources
- [ ] Selected text query works correctly
- [ ] CORS configured for book domain

## Phase 4 — Frontend
- [ ] Widget renders on book page
- [ ] Chat opens and closes
- [ ] Text selection toolbar appears
- [ ] Question sent → answer received
- [ ] Source links clickable
- [ ] Mobile view works

---

# 🚀 QUICK START FOR QWEN

**Prompt to use:**

```
Read this entire document. Then:
1. Start with Phase 1.
2. Execute every task in the sp.tasks list in order.
3. Use the exact code from sp.implementation.
4. After completing all tasks and the acceptance test passes, say "Phase 1 complete ✅" and stop.
5. Do not move to Phase 2 until I say so.
```

Then for all phase:
```
Read this entire document fully.
Then execute ALL phases (1, 2, 3, 4) one by one in order.
Complete every task in each phase before moving to the next.
Do not stop or wait for confirmation between phases.
When all 4 phases are done, print "ALL PHASES COMPLETE
```
