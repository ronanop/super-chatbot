from __future__ import annotations

from pathlib import Path

from app.ingestion.text_splitter import split_text
from app.ingestion.types import DocumentChunk, IngestedDocument


class TextIngestionError(RuntimeError):
    pass


def ingest_text_file(path: str | Path, *, encoding: str = "utf-8") -> IngestedDocument:
    text_path = Path(path)
    if not text_path.exists():
        raise FileNotFoundError(f"Text file not found: {text_path}")

    try:
        raw_text = text_path.read_text(encoding=encoding)
    except Exception as exc:  # pragma: no cover - surfacing ingestion issues
        raise TextIngestionError(f"Failed to read text file {text_path}: {exc}") from exc

    chunks: list[DocumentChunk] = split_text(
        text=raw_text,
        source=text_path.name,
        metadata={"path": str(text_path.resolve())},
    )

    return IngestedDocument(path=text_path, source=str(text_path), chunks=chunks)
