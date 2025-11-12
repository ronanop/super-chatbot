from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DocumentChunk:
    """Represents a chunk of text ready for embedding/storage."""

    content: str
    source: str
    metadata: dict[str, Any]

    def with_additional_metadata(self, **extra: Any) -> "DocumentChunk":
        merged = {**self.metadata, **extra}
        return DocumentChunk(content=self.content, source=self.source, metadata=merged)


@dataclass(slots=True)
class IngestedDocument:
    """High-level representation of an ingested file or URL."""

    path: Path | None
    source: str
    chunks: list[DocumentChunk]


@dataclass(slots=True)
class ScrapedPage:
    """Represents raw scraped content before chunking."""

    url: str
    text: str
