from __future__ import annotations

import os
from typing import Callable, Iterable, Sequence

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

client = OpenAI(api_key=api_key)

_DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


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

    # OpenAI embeddings API accepts multiple texts at once (up to 2048)
    batch_size = 2048
    for i in range(0, len(texts_list), batch_size):
        batch = texts_list[i:i + batch_size]
        
        try:
            response = client.embeddings.create(
                model=_DEFAULT_EMBEDDING_MODEL,
                input=batch
            )
            
            for embedding_obj in response.data:
                embeddings.append(embedding_obj.embedding)
                processed += 1
                if progress_callback:
                    try:
                        progress_callback(processed, total)
                    except Exception:
                        pass
        except Exception as e:
            raise RuntimeError(f"Embedding API error: {e}")

    return embeddings
