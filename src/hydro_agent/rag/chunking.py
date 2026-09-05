"""Small, explainable character-based document chunker."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from hydro_agent.rag.models import KnowledgeChunk, KnowledgeSection


def _normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()


def chunk_sections(
    sections: Iterable[KnowledgeSection], chunk_size: int = 500, overlap: int = 80
) -> list[KnowledgeChunk]:
    """Split sections with overlap and retain file/page/section citations."""

    if chunk_size < 100:
        raise ValueError("chunk_size 至少为 100。")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap 必须大于等于 0 且小于 chunk_size。")

    chunks: list[KnowledgeChunk] = []
    for section in sections:
        text = _normalize(section.text)
        start = 0
        chunk_number = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                candidates = [text.rfind(mark, start + chunk_size // 2, end) for mark in "。！？；\n"]
                boundary = max(candidates)
                if boundary > start:
                    end = boundary + 1
            body = text[start:end].strip()
            if body:
                raw_id = f"{section.source}|{section.page}|{section.section}|{chunk_number}|{body}"
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=hashlib.sha1(raw_id.encode("utf-8")).hexdigest()[:12],
                        source=section.source,
                        text=body,
                        page=section.page,
                        section=section.section,
                    )
                )
                chunk_number += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks

