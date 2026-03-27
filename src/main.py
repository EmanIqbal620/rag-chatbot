from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="RAG Chatbot API",
    description="API for the textbook RAG chatbot system",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"Hello": "RAG Chatbot"}

# Include API routes
from backend.api import chat
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
