from __future__ import annotations

import os
from typing import Callable, Iterable, Sequence

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

genai.configure(api_key=api_key)

_DEFAULT_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")


def embed_texts(
    texts: Iterable[str],
    *,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    texts_list = [text for text in texts if text.strip()]
    if not texts_list:
        return []

    embeddings: list[list[float]] = []
    total = len(texts_list)
    processed = 0

    if progress_callback:
        try:
            progress_callback(processed, total)
        except Exception:
            pass

    for text in texts_list:
        response = genai.embed_content(model=_DEFAULT_EMBEDDING_MODEL, content=text)
        embedding = response.get("embedding")
        if not embedding:
            raise RuntimeError("Embedding API returned no embedding vector.")
        embeddings.append(list(embedding))
        processed += 1
        if progress_callback:
            try:
                progress_callback(processed, total)
            except Exception:
                pass

    return embeddings
