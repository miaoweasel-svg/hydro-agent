from __future__ import annotations

from hydro_agent.rag import RAGService, chunk_sections, parse_document


def test_markdown_chunking_preserves_section_and_source():
    content = ("# 数据检查\n" + "先检查时间戳、缺失值和单位。" * 30).encode("utf-8")
    sections = parse_document(content, "demo.md")
    chunks = chunk_sections(sections, chunk_size=120, overlap=20)

    assert len(chunks) > 1
    assert all(chunk.source == "demo.md" for chunk in chunks)
    assert all(chunk.section == "数据检查" for chunk in chunks)


def test_local_rag_retrieves_relevant_cited_chunk():
    service = RAGService()
    service.ingest_bytes(
        "# 异常复核\n发现水位异常后应检查相邻时刻和传感器记录。\n"
        "# 日报\n日报需要列出均值和极值。".encode("utf-8"),
        "guide.md",
    )

    results = service.search("水位异常如何复核", top_k=1)

    assert results[0].chunk.source == "guide.md"
    assert results[0].chunk.section == "异常复核"
    assert "传感器" in results[0].chunk.text

