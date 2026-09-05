"""Parse PDF, TXT, and Markdown files while preserving citation metadata."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from hydro_agent.rag.models import KnowledgeSection


class DocumentParseError(ValueError):
    """Raised for unsupported or unreadable knowledge documents."""


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentParseError("文本编码无法识别，请使用 UTF-8 编码。")


def _parse_markdown(text: str, filename: str) -> list[KnowledgeSection]:
    sections: list[KnowledgeSection] = []
    heading = "文档开头"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append(KnowledgeSection(filename, body, section=heading))

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            buffer.clear()
            heading = stripped.lstrip("#").strip() or "未命名章节"
        else:
            buffer.append(line)
    flush()
    return sections


def parse_document(content: bytes, filename: str) -> list[KnowledgeSection]:
    """Parse document bytes into source-aware sections."""

    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise DocumentParseError("解析 PDF 需要安装 pypdf。") from exc
        try:
            reader = PdfReader(BytesIO(content))
            sections = []
            for index, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    sections.append(KnowledgeSection(filename, text, page=index))
            return sections
        except Exception as exc:
            raise DocumentParseError(f"PDF 解析失败: {exc}") from exc
    if suffix == ".md":
        return _parse_markdown(_decode_text(content), filename)
    if suffix == ".txt":
        text = _decode_text(content).strip()
        return [KnowledgeSection(filename, text, section="全文")] if text else []
    raise DocumentParseError("知识库仅支持 PDF、TXT 和 Markdown 文件。")


def load_document(path: str | Path) -> list[KnowledgeSection]:
    """Load and parse a document from disk."""

    document_path = Path(path)
    return parse_document(document_path.read_bytes(), document_path.name)
