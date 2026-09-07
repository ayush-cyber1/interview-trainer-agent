"""
backend/ingestion/build_vector_store.py
─────────────────────────────────────────────────────────────────────────────
Run this script ONCE (or whenever you add corpus files) to embed all corpus
questions and persist them to a lightweight JSON vector store.

Uses sentence-transformers locally to produce embeddings, then saves them as
a plain JSON file (vector_store/embeddings.json).  The FastAPI server loads
that file at startup using only numpy — no chromadb, no onnxruntime.

Usage:
    cd backend
    python -m ingestion.build_vector_store
─────────────────────────────────────────────────────────────────────────────
"""

import json
import sys
from pathlib import Path

# ── resolve paths via config ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings


def _flatten_corpus(corpus_dir: Path) -> list[dict]:
    """Walk all JSON files in corpus_dir and return a flat list of chunks.

    Supports two corpus schemas:

    Schema A — nested dict (software_engineer.json):
        { "role": "...", "levels": { "fresher": { "technical": [...], "behavioral": [...] }, ... } }

    Schema B — flat list (all other files):
        { "role": "...", "levels": [...], "questions": [ { "type": "...", "level": "...", ... } ] }
    """
    chunks: list[dict] = []
    for json_file in sorted(corpus_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        role = data.get("role", json_file.stem)
        levels_data = data.get("levels", {})

        # ── Schema A: levels is a dict of { level_name: { "technical": [], "behavioral": [] } }
        if isinstance(levels_data, dict):
            for level_name, level_content in levels_data.items():
                for q_type in ("technical", "behavioral"):
                    for q in level_content.get(q_type, []):
                        chunk_text = (
                            f"Role: {role}\n"
                            f"Level: {level_name}\n"
                            f"Type: {q_type}\n"
                            f"Question: {q['question']}\n"
                            f"Answer: {q['model_answer']}\n"
                            f"Tip: {q.get('tip', '')}"
                        )
                        chunks.append(
                            {
                                "id": q.get("id", f"{json_file.stem}_{q_type}_{len(chunks)}"),
                                "text": chunk_text,
                                "metadata": {
                                    "role": role,
                                    "level": level_name,
                                    "type": q_type,
                                    "question": q["question"],
                                    "model_answer": q["model_answer"],
                                    "tip": q.get("tip", ""),
                                },
                            }
                        )

        # ── Schema B: levels is a list; questions are in a top-level "questions" array
        else:
            for q in data.get("questions", []):
                q_type = q.get("type", "technical")
                level_name = q.get("level", "Fresher").lower()
                chunk_text = (
                    f"Role: {role}\n"
                    f"Level: {level_name}\n"
                    f"Type: {q_type}\n"
                    f"Question: {q['question']}\n"
                    f"Answer: {q['model_answer']}\n"
                    f"Tip: {q.get('tip', '')}"
                )
                chunks.append(
                    {
                        "id": q.get("id", f"{json_file.stem}_{q_type}_{len(chunks)}"),
                        "text": chunk_text,
                        "metadata": {
                            "role": role,
                            "level": level_name,
                            "type": q_type,
                            "question": q["question"],
                            "model_answer": q["model_answer"],
                            "tip": q.get("tip", ""),
                        },
                    }
                )

    return chunks


def build() -> None:
    # sentence-transformers is only needed at build time, not at server runtime
    from sentence_transformers import SentenceTransformer

    corpus_dir: Path = settings.CORPUS_DIR
    out_path: Path = settings.VECTOR_STORE_PATH

    if not corpus_dir.exists():
        print(f"[ERROR] Corpus directory not found: {corpus_dir}")
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Loading embedding model: {settings.EMBEDDING_MODEL}")
    model = SentenceTransformer(settings.EMBEDDING_MODEL)

    print("[2/4] Flattening corpus …")
    chunks = _flatten_corpus(corpus_dir)
    if not chunks:
        print("[ERROR] No questions found in corpus. Check your JSON files.")
        sys.exit(1)
    print(f"       Found {len(chunks)} chunks across {len(list(corpus_dir.glob('*.json')))} files.")

    print("[3/4] Embedding …")
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    print(f"[4/4] Saving vector store to {out_path} …")
    store = {
        "model": settings.EMBEDDING_MODEL,
        "chunks": [
            {
                "id": c["id"],
                "text": c["text"],
                "metadata": c["metadata"],
                "embedding": embeddings[i].tolist(),
            }
            for i, c in enumerate(chunks)
        ],
    }
    out_path.write_text(json.dumps(store), encoding="utf-8")

    print(f"\nDone! Vector store saved: {out_path}")
    print(f"  Total chunks indexed: {len(chunks)}")


if __name__ == "__main__":
    build()
