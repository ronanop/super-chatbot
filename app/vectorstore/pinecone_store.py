from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable
import uuid

from dotenv import load_dotenv
from pinecone import Pinecone

from app.ingestion.types import DocumentChunk
from app.services.embeddings import embed_texts

_pc: Pinecone | None = None
_index = None


def _ensure_index():
    global _pc, _index

    if _index is not None:
        return _index

    load_dotenv()

    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX")
    if not api_key or not index_name:
        raise RuntimeError("PINECONE_API_KEY and PINECONE_INDEX must be set in environment variables.")

    _pc = Pinecone(api_key=api_key)
    _index = _pc.Index(index_name)
    return _index


def upsert_chunks(
    chunks: Iterable[DocumentChunk],
    *,
    batch_size: int = 100,
    progress_callback: Callable[[int, int], None] | None = None,
    embedding_callback: Callable[[int, int], None] | None = None,
) -> None:
    index = _ensure_index()

    chunk_list = [chunk for chunk in chunks if chunk.content.strip()]
    if not chunk_list:
        if embedding_callback:
            try:
                embedding_callback(0, 0)
            except Exception:
                pass
        if progress_callback:
            try:
                progress_callback(0, 0)
            except Exception:
                pass
        return

    embeddings = embed_texts(
        (chunk.content for chunk in chunk_list),
        progress_callback=embedding_callback,
    )

    vectors = []
    total = len(chunk_list)
    processed = 0

    if progress_callback:
        try:
            progress_callback(processed, total)
        except Exception:
            pass

    for chunk, embedding in zip(chunk_list, embeddings, strict=False):
        vector_id = chunk.metadata.get("id") or str(uuid.uuid4())
        meta = {
            "source": chunk.source,
            "text": chunk.content,
            **{k: v for k, v in chunk.metadata.items() if k not in {"id"}},
        }
        vectors.append({"id": vector_id, "values": embedding, "metadata": meta})

    for start in range(0, len(vectors), batch_size):
        batch = vectors[start : start + batch_size]
        index.upsert(vectors=batch)
        processed = min(total, processed + len(batch))
        if progress_callback:
            try:
                progress_callback(processed, total)
            except Exception:
                pass


def query_similar(text: str, *, top_k: int = 5, min_score: float = 0.0) -> list[dict]:
    """
    Query similar vectors from Pinecone.
    
    Args:
        text: Text to find similar vectors for
        top_k: Number of results to return
        min_score: Minimum similarity score (0.0 to 1.0). Lower values = more lenient matching.
                   For cosine similarity, scores typically range from -1 to 1, but Pinecone normalizes to 0-1.
    """
    index = _ensure_index()
    embeddings = embed_texts([text])
    if not embeddings:
        return []

    result = index.query(vector=embeddings[0], top_k=top_k, include_metadata=True)
    matches = getattr(result, "matches", [])
    
    # Filter by minimum score if specified
    if min_score > 0.0:
        filtered_matches = []
        for match in matches:
            score = getattr(match, "score", 0.0)
            # Pinecone cosine similarity scores are typically normalized to 0-1 range
            # Adjust threshold based on your needs (0.5-0.7 is usually good)
            if score >= min_score:
                filtered_matches.append(match)
        return filtered_matches
    
    return matches


def delete_by_path(path: str) -> None:
    index = _ensure_index()
    targets = {path}
    try:
        targets.add(str(Path(path).resolve()))
    except Exception:
        pass
    for target in targets:
        try:
            index.delete(filter={"path": target})
        except Exception:
            continue


def delete_all() -> int:
    """Delete all vectors from Pinecone index. Returns number of vectors deleted."""
    index = _ensure_index()
    try:
        # Get stats to see how many vectors exist
        stats = index.describe_index_stats()
        total_vectors = stats.get("total_vector_count", 0)
        
        if total_vectors == 0:
            return 0
        
        # Pinecone delete_all - delete all vectors in the index
        # Note: This deletes ALL vectors, not just ones with metadata
        try:
            # Try delete_all parameter (newer API)
            index.delete(delete_all=True)
        except TypeError:
            # If delete_all parameter doesn't work, try deleting by empty filter
            # Empty filter {} should match all vectors
            try:
                index.delete(filter={})
            except Exception:
                # Last resort: delete by namespace (if using default namespace)
                try:
                    index.delete(delete_all=True, namespace="")
                except Exception:
                    # Final fallback: get all IDs and delete (slower but works)
                    # This is a workaround if other methods fail
                    raise RuntimeError("Could not delete all vectors. Please check Pinecone API version.")
        
        return total_vectors
    except Exception as e:
        raise RuntimeError(f"Failed to delete all vectors: {e}")
