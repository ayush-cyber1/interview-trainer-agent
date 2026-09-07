"""
backend/retrieval/vector_store.py
─────────────────────────────────────────────────────────────────────────────
Query the persisted JSON vector store using numpy cosine similarity.
No chromadb, no onnxruntime, no sentence-transformers at runtime.
Embeddings are pre-computed at build time and loaded once into memory.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np

# lazy singleton — loaded once on first use
_lock = threading.Lock()
_store: dict[str, Any] | None = None  # {"model": str, "chunks": [...]}
_embeddings: np.ndarray | None = None  # shape (N, D), float32, L2-normalised


def _load_store(db_path: Path) -> tuple[dict, np.ndarray]:
    global _store, _embeddings
    if _store is None:
        with _lock:
            if _store is None:
                if not db_path.exists():
                    raise FileNotFoundError(
                        f"Vector store not found at {db_path}. "
                        "Run: cd backend && python -m ingestion.build_vector_store"
                    )
                data = json.loads(db_path.read_text(encoding="utf-8"))
                _store = data
                _embeddings = np.array(
                    [c["embedding"] for c in data["chunks"]], dtype=np.float32
                )
    return _store, _embeddings  # type: ignore[return-value]


def _embed_query(query: str, model_name: str) -> np.ndarray:
    """
    Embed the query at runtime using a tiny TF-IDF-style bag-of-words so we
    never load sentence-transformers in the server process.

    Because the corpus embeddings were produced by sentence-transformers we
    cannot use a perfect cosine match here — instead we fall back to a simple
    keyword overlap score that works well enough for the small corpora used in
    this project and fits comfortably within Render's 512 MB free tier.

    The score array is normalised to unit length so it can be compared with
    the stored normalised embeddings via dot product.
    """
    # We embed the query into the same dimension as the stored embeddings by
    # computing dot-product relevance directly from text rather than projecting
    # into embedding space.  This function is intentionally NOT used for the
    # cosine path — see retrieve() below.
    raise NotImplementedError  # pragma: no cover


def _text_score(query: str, chunks: list[dict]) -> np.ndarray:
    """
    Keyword overlap score: fraction of query tokens present in chunk text.
    Fast, zero-dependency, good enough for a small fixed corpus.
    """
    q_tokens = set(query.lower().split())
    scores = np.zeros(len(chunks), dtype=np.float32)
    for i, chunk in enumerate(chunks):
        text_tokens = set(chunk["text"].lower().split())
        if q_tokens:
            scores[i] = len(q_tokens & text_tokens) / len(q_tokens)
    return scores


def retrieve(
    query: str,
    role: str,
    level: str,
    top_k: int,
    embedding_model: str,
    db_path: Path,
) -> list[dict]:
    """
    Score all chunks by keyword overlap, apply optional role/level filter,
    and return the top_k metadata dicts.

    Each returned dict contains: question, model_answer, tip, role, level, type
    """
    store, _ = _load_store(db_path)
    chunks: list[dict] = store["chunks"]

    # ── filter by role and level ──────────────────────────────────────────
    def _matches(meta: dict) -> bool:
        role_ok = (not role) or meta.get("role", "").lower() == role.lower()
        level_ok = (not level) or meta.get("level", "").lower() == level.lower()
        return role_ok and level_ok

    filtered = [c for c in chunks if _matches(c["metadata"])]

    # Fall back to full corpus if filter is too narrow
    working = filtered if len(filtered) >= top_k else chunks

    scores = _text_score(query, working)
    top_indices = np.argsort(scores)[::-1][:top_k]

    return [working[i]["metadata"] for i in top_indices]
