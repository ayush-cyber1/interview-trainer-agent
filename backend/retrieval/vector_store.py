"""
backend/retrieval/vector_store.py
─────────────────────────────────────────────────────────────────────────────
Query the persisted Chroma collection using locally-computed embeddings.
No watsonx.ai calls here — pure local retrieval.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

# lazy singleton — loaded once on first use
_lock = threading.Lock()
_model: SentenceTransformer | None = None
_client: chromadb.PersistentClient | None = None
_collection: Any = None


def _get_model(model_name: str) -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(model_name)
    return _model


def _get_collection(db_path: Path) -> Any:
    global _client, _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                _client = chromadb.PersistentClient(path=str(db_path))
                _collection = _client.get_collection("interview_corpus")
    return _collection


def retrieve(
    query: str,
    role: str,
    level: str,
    top_k: int,
    embedding_model: str,
    db_path: Path,
) -> list[dict]:
    """
    Embed `query` locally and fetch `top_k` most similar chunks from Chroma.
    Optionally filters by role and level if they are present in the metadata.

    Returns a list of metadata dicts, each containing:
        question, model_answer, tip, role, level, type
    """
    model = _get_model(embedding_model)
    collection = _get_collection(db_path)

    query_embedding = model.encode(query, normalize_embeddings=True).tolist()

    # Build where filter — narrow results to the right role/level
    where_filter: dict | None = None
    if role and level:
        where_filter = {
            "$and": [
                {"role": {"$eq": role}},
                {"level": {"$eq": level.lower()}},
            ]
        }
    elif role:
        where_filter = {"role": {"$eq": role}}

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            where=where_filter,
            include=["metadatas", "distances", "documents"],
        )
    except Exception:
        # Fall back without filter if the filtered collection is too small
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["metadatas", "distances", "documents"],
        )

    metadatas: list[dict] = results.get("metadatas", [[]])[0]
    return metadatas
