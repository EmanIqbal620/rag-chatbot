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
                chapter_name TEXT,
                chunk_index INT,
                chunk_text TEXT,
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
        (c["id"], c["source_url"], c["page_title"], 
         c.get("chapter_name", c["page_title"]), c["chunk_index"], c["text"])
        for c in chunks
    ]
    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO chunks (id, source_url, page_title, chapter_name,
                                chunk_index, chunk_text)
            VALUES %s
            ON CONFLICT (source_url, chunk_index) DO NOTHING;
        """, rows)
    conn.commit()
    conn.close()
    print(f"[NEON] Inserted {len(rows)} chunks")
