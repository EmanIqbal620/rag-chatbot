import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.scraper import scrape_urls
from ingestion.chunker import chunk_document
from ingestion.embedder import embed_chunks
from ingestion.vector_store import init_collection, upsert_chunks
from ingestion.db_store import init_table, insert_chunks

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
