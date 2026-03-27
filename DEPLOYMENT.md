# Deployment Configuration for Humanoid Robotics AI RAG System

## Environment Variables (.env)
```
OPENAI_API_KEY=your_openai_api_key_here
COHERE_API_KEY=your_cohere_api_key_here
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here
NEON_DATABASE_URL=your_neon_database_url_here
QDRANT_COLLECTION_NAME=humanoid_ai_book
```

## Installation and Setup

### 1. Clone and setup virtual environment:
```bash
git clone <your-repo-url>
cd <repo-name>/backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Usage Commands

### Ingest content (existing functionality):
```bash
# Ingest local files
python main.py ingest

# Ingest from sitemap (default behavior when no command specified)
python main.py ingest-sitemap
# Or simply:
python main.py
```

### Chat with the system (existing functionality):
```bash
python main.py chat
```

### Search content (existing functionality):
```bash
python main.py search "your query here"
```

## API Server

### Start the API server:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### API Endpoints:

- `GET /` - Root endpoint
- `GET /api/v1/health` - Health check
- `POST /api/v1/chat` - Chat with RAG system using OpenAI Agents SDK
- `POST /api/v1/query` - Alternative query endpoint with more options
- `GET /api/v1/stats` - Get usage statistics

## Docker Deployment (Optional)

### Dockerfile:
```Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and run:
```bash
docker build -t rag-system .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=... \
  -e COHERE_API_KEY=... \
  -e QDRANT_URL=... \
  -e QDRANT_API_KEY=... \
  -e NEON_DATABASE_URL=... \
  rag-system
```

## System Architecture

1. **RAG Agent with OpenAI Agents SDK**:
   - Uses OpenAI's Assistant API for intelligent responses
   - Retrieves context from Qdrant vector database
   - Generates contextual answers based on textbook content

2. **Vector Storage & Retrieval**:
   - Qdrant Cloud for vector similarity search
   - Cohere embeddings for semantic search
   - Metadata storage with content and source info

3. **Database & Logging**:
   - Neon Serverless Postgres for interaction logging
   - Usage statistics and performance metrics
   - Query/response logging with timestamps

4. **API Layer**:
   - FastAPI web framework with async support
   - Request/response validation with Pydantic
   - Comprehensive error handling and logging
```