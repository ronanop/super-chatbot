from __future__ import annotations

from pathlib import Path

import pdfplumber

from app.ingestion.text_splitter import split_text
from app.ingestion.types import DocumentChunk, IngestedDocument


class PDFIngestionError(RuntimeError):
    pass


def extract_text_from_pdf(path: Path) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:  # pragma: no cover - surfacing ingestion issues
        raise PDFIngestionError(f"Failed to read PDF {path}: {exc}") from exc

    combined = "\n\n".join(pages)
    return combined.strip()


def ingest_pdf(path: str | Path) -> IngestedDocument:
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    raw_text = extract_text_from_pdf(pdf_path)
    chunks: list[DocumentChunk] = split_text(
        text=raw_text,
        source=pdf_path.name,
        metadata={"path": str(pdf_path.resolve())},
    )

    return IngestedDocument(path=pdf_path, source=str(pdf_path), chunks=chunks)
