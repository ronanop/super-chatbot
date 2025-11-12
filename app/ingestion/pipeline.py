from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.ingestion.crawler import crawl_urls
from app.ingestion.pdf_loader import ingest_pdf
from app.ingestion.text_loader import ingest_text_file
from app.vectorstore.pinecone_store import upsert_chunks


def ingest_pdfs_to_pinecone(paths: Iterable[str | Path]) -> int:
    total_chunks = 0
    for path in paths:
        document = ingest_pdf(path)
        upsert_chunks(document.chunks)
        total_chunks += len(document.chunks)
    return total_chunks


def ingest_texts_to_pinecone(paths: Iterable[str | Path]) -> int:
    total_chunks = 0
    for path in paths:
        document = ingest_text_file(path)
        upsert_chunks(document.chunks)
        total_chunks += len(document.chunks)
    return total_chunks


def crawl_and_ingest(urls: Iterable[str], *, limit_per_domain: int = 20) -> int:
    documents = crawl_urls(urls, limit_per_domain=limit_per_domain)
    total_chunks = 0
    for document in documents:
        upsert_chunks(document.chunks)
        total_chunks += len(document.chunks)
    return total_chunks
