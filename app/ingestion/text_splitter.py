from __future__ import annotations

import re
from typing import Iterable

from app.ingestion.types import DocumentChunk

_DEFAULT_CHUNK_SIZE = 1000
_DEFAULT_CHUNK_OVERLAP = 200


def _yield_chunks(text: str, chunk_size: int, chunk_overlap: int) -> Iterable[str]:
    paragraphs = re.split(r"\n\s*\n", text)
    buffer = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if buffer:
            buffer += "\n\n" + paragraph
        else:
            buffer = paragraph
        while len(buffer) >= chunk_size:
            yield buffer[:chunk_size]
            buffer = buffer[chunk_size - chunk_overlap :]
    if buffer:
        yield buffer


def split_text(
    *,
    text: str,
    source: str,
    metadata: dict[str, str] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """Split raw text into manageable chunks for embeddings."""

    if not text.strip():
        return []

    chunk_size = chunk_size or _DEFAULT_CHUNK_SIZE
    chunk_overlap = chunk_overlap or _DEFAULT_CHUNK_OVERLAP

    base_metadata = metadata or {}

    chunks = list(_yield_chunks(text, chunk_size, chunk_overlap))
    return [
        DocumentChunk(
            content=chunk.strip(),
            source=source,
            metadata={**base_metadata, "chunk_index": index},
        )
        for index, chunk in enumerate(chunks)
        if chunk.strip()
    ]
