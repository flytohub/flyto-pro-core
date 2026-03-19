"""
Built-in provider implementations for flyto-pro interfaces.

Each provider wraps a specific backend (OpenAI, Qdrant, etc.)
behind the abstract interfaces defined in src.pro.interfaces.

All providers are optional — install the corresponding extra
to use them:
    pip install flyto-pro[openai]    # OpenAI LLM + Embeddings
    pip install flyto-pro[qdrant]    # Qdrant vector store
    pip install flyto-pro[full]      # Everything
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .openai_llm import OpenAILLMService, OpenAIEmbeddingService
    from .qdrant_store import QdrantVectorStore

__all__ = [
    "OpenAILLMService",
    "OpenAIEmbeddingService",
    "QdrantVectorStore",
]
