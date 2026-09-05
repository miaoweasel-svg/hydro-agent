"""Replaceable local vector-index implementations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from hydro_agent.rag.embeddings import DenseEmbeddingProvider
from hydro_agent.rag.models import KnowledgeChunk, SearchResult


class VectorStore(Protocol):
    def build(self, chunks: Sequence[KnowledgeChunk]) -> None: ...

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]: ...


class TfidfVectorStore:
    """Offline character n-gram embedding and cosine vector index."""

    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), min_df=1)
        self._matrix = None
        self._chunks: list[KnowledgeChunk] = []

    def build(self, chunks: Sequence[KnowledgeChunk]) -> None:
        self._chunks = list(chunks)
        self._matrix = (
            self._vectorizer.fit_transform([chunk.text for chunk in self._chunks])
            if self._chunks
            else None
        )

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        if not self._chunks or self._matrix is None or not query.strip():
            return []
        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix)[0]
        indices = np.argsort(scores)[::-1][: min(top_k, len(self._chunks))]
        return [SearchResult(self._chunks[index], float(scores[index])) for index in indices]


class DenseVectorStore:
    """Dense cosine index backed by an interchangeable embedding provider."""

    def __init__(self, embedding_provider: DenseEmbeddingProvider) -> None:
        self._provider = embedding_provider
        self._vectors = np.empty((0, 0), dtype=np.float32)
        self._chunks: list[KnowledgeChunk] = []

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)

    def build(self, chunks: Sequence[KnowledgeChunk]) -> None:
        self._chunks = list(chunks)
        self._vectors = (
            self._normalize(self._provider.embed([chunk.text for chunk in self._chunks]))
            if self._chunks
            else np.empty((0, 0), dtype=np.float32)
        )

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        if not self._chunks or not query.strip():
            return []
        query_vector = self._normalize(self._provider.embed([query]))[0]
        scores = self._vectors @ query_vector
        indices = np.argsort(scores)[::-1][: min(top_k, len(self._chunks))]
        return [SearchResult(self._chunks[index], float(scores[index])) for index in indices]

