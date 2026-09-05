"""High-level ingestion and retrieval service."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from hydro_agent.rag.chunking import chunk_sections
from hydro_agent.rag.loader import load_document, parse_document
from hydro_agent.rag.models import KnowledgeChunk, KnowledgeSection, SearchResult
from hydro_agent.rag.vector_store import TfidfVectorStore, VectorStore


class RAGService:
    """Manage source-aware document chunks and a replaceable vector index."""

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self.vector_store = vector_store or TfidfVectorStore()
        self.sections: list[KnowledgeSection] = []
        self.chunks: list[KnowledgeChunk] = []

    @property
    def sources(self) -> list[str]:
        return sorted({section.source for section in self.sections})

    def _rebuild(self) -> None:
        self.chunks = chunk_sections(self.sections)
        self.vector_store.build(self.chunks)

    def ingest_paths(self, paths: Iterable[str | Path]) -> None:
        for path in paths:
            self.sections.extend(load_document(path))
        self._rebuild()

    def ingest_bytes(self, content: bytes, filename: str) -> None:
        self.sections = [section for section in self.sections if section.source != filename]
        self.sections.extend(parse_document(content, filename))
        self._rebuild()

    def ingest_directory(self, directory: str | Path) -> None:
        root = Path(directory)
        paths = sorted(
            path for path in root.iterdir() if path.suffix.lower() in {".pdf", ".txt", ".md"}
        ) if root.exists() else []
        self.ingest_paths(paths)

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        if not 1 <= top_k <= 10:
            raise ValueError("top_k 必须位于 1 到 10 之间。")
        return self.vector_store.search(query, top_k)

