"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Runtime settings with safe defaults for the local demo."""

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    rag_embedding_provider: str = os.getenv("RAG_EMBEDDING_PROVIDER", "local")
    openai_embedding_model: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    demo_data_path: Path = PROJECT_ROOT / "data" / "synthetic_gate_operation.csv"
    knowledge_dir: Path = PROJECT_ROOT / "docs" / "knowledge"


settings = Settings()

