from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken
import uuid
from typing import List, Dict

ENCODER = tiktoken.get_encoding("cl100k_base")

def token_len(text: str) -> int:
    return len(ENCODER.encode(text))

# Smaller chunks for precise answers - 400 tokens, 50 overlap
splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    length_function=token_len,
    separators=["\n\n", "\n", ". ", " ", ""]
)

def extract_chapter_name(url: str, title: str) -> str:
    """Extract clean chapter name from URL and title."""
    # Remove common suffixes from title
    clean_title = title.replace(" | Physical AI & Humanoid Robotics", "")
    clean_title = clean_title.replace("Physical AI & Humanoid Robotics: ", "")
    
    # If title is too long, use URL path
    if len(clean_title) > 50:
        parts = url.strip("/").split("/")
        if "docs" in parts:
            idx = parts.index("docs")
            if idx + 1 < len(parts):
                chapter = parts[idx + 1].replace("-", " ").title()
                return chapter
    
    return clean_title if clean_title else "Unknown Chapter"

def chunk_document(doc: Dict) -> List[Dict]:
    """Split a scraped document into chunks with metadata."""
    if not doc["raw_text"]:
        return []

    texts = splitter.split_text(doc["raw_text"])
    chunks = []
    chapter_name = extract_chapter_name(doc["url"], doc["title"])

    for i, text in enumerate(texts):
        chunks.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "chunk_index": i,
            "source_url": doc["url"],
            "page_title": doc["title"],
            "chapter_name": chapter_name,
            "source_short": chapter_name
        })
    return chunks
