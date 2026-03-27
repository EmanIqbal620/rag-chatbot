# Humanoid Robotics RAG API

This is a production-ready Retrieval-Augmented Generation (RAG) chatbot using the OpenAI Agents SDK and FastAPI that can answer questions about the humanoid robotics textbook.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new?template=https://github.com/YOUR_REPO)

## Quick Deploy to Railway

See [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) for complete deployment instructions.

## Prerequisites

- Python 3.11+
- OpenAI API key
- Cohere API key
- Qdrant Cloud URL and API key
- Neon Postgres database URL

## Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd <repo-name>/backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
```

Edit the `.env` file with your API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here
COHERE_API_KEY=your_cohere_api_key_here
QDRANT_URL=your_qdrant_url_here
QDRANT_API_KEY=your_qdrant_api_key_here
NEON_DATABASE_URL=your_neon_database_url_here
QDRANT_COLLECTION_NAME=humanoid_ai_book
```

## Running Locally

### Start the FastAPI Server
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Chat Endpoint
`POST /api/v1/chat`

Request body:
```json
{
  "query": "Your question here",
  "user_id": "optional_user_id",
  "max_tokens": 1000,
  "temperature": 0.7,
  "top_k": 5,
  "user_selected_text": "optional selected text"
}
```

### Health Check
`GET /api/v1/health`

### Usage Statistics
`GET /api/v1/stats`

## Docker Deployment

### Build the Image
```bash
docker build -t rag-system .
```

### Run the Container
```bash
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=... \
  -e COHERE_API_KEY=... \
  -e QDRANT_URL=... \
  -e QDRANT_API_KEY=... \
  -e NEON_DATABASE_URL=... \
  rag-system
```

## Environment Configuration

### Development
- Use `--reload` flag with uvicorn for auto-reload on code changes
- Enable detailed logging for debugging

### Production
- Set appropriate environment variables for production
- Configure reverse proxy (nginx, etc.) for SSL termination
- Set up proper logging aggregation
- Configure monitoring and alerting"# rag-chatbot" 
"# rag-chatbot"  
