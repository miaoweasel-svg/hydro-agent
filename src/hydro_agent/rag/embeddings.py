"""Optional OpenAI embedding adapter, isolated from the RAG service."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np


class DenseEmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Embed a batch of texts into a dense matrix."""


class OpenAIEmbeddingProvider:
    """Generate embeddings through the current OpenAI Python SDK."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("使用 OpenAI embedding 需要安装 openai。") from exc
        self._client = OpenAI(api_key=api_key)
        self.model = model

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        response = self._client.embeddings.create(
            model=self.model,
            input=list(texts),
            encoding_format="float",
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return np.asarray([item.embedding for item in ordered], dtype=np.float32)

