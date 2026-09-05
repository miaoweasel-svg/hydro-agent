"""Local retrieval-augmented generation components."""

from hydro_agent.rag.chunking import chunk_sections
from hydro_agent.rag.embeddings import OpenAIEmbeddingProvider
from hydro_agent.rag.loader import load_document, parse_document
from hydro_agent.rag.models import KnowledgeChunk, KnowledgeSection, SearchResult
from hydro_agent.rag.service import RAGService
from hydro_agent.rag.vector_store import DenseVectorStore, TfidfVectorStore

__all__ = [
    "DenseVectorStore",
    "KnowledgeChunk",
    "KnowledgeSection",
    "OpenAIEmbeddingProvider",
    "RAGService",
    "SearchResult",
    "TfidfVectorStore",
    "chunk_sections",
    "load_document",
    "parse_document",
]
