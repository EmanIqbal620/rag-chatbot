from fastapi import APIRouter, BackgroundTasks
from api.models import IngestRequest, APIResponse
from ingestion.scraper import scrape_urls
from ingestion.chunker import chunk_document
from ingestion.embedder import embed_chunks
from ingestion.vector_store import init_collection, upsert_chunks
from ingestion.db_store import init_table, insert_chunks

router = APIRouter()

@router.post("/ingest", response_model=APIResponse)
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    def run():
        print(f"[INGEST BG] Starting ingestion for {len(request.urls)} URLs")
        init_collection()
        init_table()
        total = 0
        for url in request.urls:
            print(f"[INGEST BG] Processing: {url}")
            docs = scrape_urls([url])
            for doc in docs:
                chunks = chunk_document(doc)
                chunks = embed_chunks(chunks)
                upsert_chunks(chunks)
                insert_chunks(chunks)
                total += len(chunks)
        print(f"[INGEST BG] Done: {total} chunks ingested")

    background_tasks.add_task(run)
    return APIResponse(
        status="ok",
        data={"message": f"Ingesting {len(request.urls)} URLs in background"}
    )
