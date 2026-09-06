"""
backend/config.py
─────────────────────────────────────────────────────────────────────────────
Central configuration loaded from environment variables / .env file.

To use:
  1. Copy .env.example → backend/.env
  2. Fill in your WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_MODEL_ID,
     and WATSONX_URL values.
  3. The ONLY value you need to change to switch to a Granite model is
     WATSONX_MODEL_ID — no other code logic depends on which model family
     the ID belongs to.
─────────────────────────────────────────────────────────────────────────────
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # ── watsonx.ai ────────────────────────────────────────────────────────────
    # Leave these empty here; fill them in your .env file.
    # Example WATSONX_MODEL_ID : meta-llama/llama-3-3-70b-instruct
    # Example WATSONX_URL      : https://eu-gb.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29
    WATSONX_API_KEY: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_MODEL_ID: str = ""
    WATSONX_URL: str = ""

    # ── Local paths ───────────────────────────────────────────────────────────
    CORPUS_DIR: Path = BASE_DIR / "ingestion" / "corpus"
    CHROMA_DB_PATH: Path = BASE_DIR / "vector_store" / "chroma_db"

    # ── Retrieval ─────────────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 6

    # ── Embedding (local, no API key needed) ──────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
