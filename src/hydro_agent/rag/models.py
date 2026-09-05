"""Traceable RAG data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class KnowledgeSection:
    source: str
    text: str
    page: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    text: str
    page: int | None = None
    section: str | None = None


@dataclass(frozen=True)
class SearchResult:
    chunk: KnowledgeChunk
    score: float

    def to_dict(self) -> dict[str, object]:
        data = asdict(self.chunk)
        data["score"] = round(float(self.score), 4)
        location = f"第 {self.chunk.page} 页" if self.chunk.page else self.chunk.section or "全文"
        data["location"] = location
        return data

