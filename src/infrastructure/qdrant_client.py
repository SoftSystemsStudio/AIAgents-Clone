"""Qdrant client initializer for dependency injection."""

from typing import Optional

from src.config import VectorStoreConfig
from src.infrastructure.vector_stores import QdrantVectorStore


def init_qdrant_vector_store(config: VectorStoreConfig) -> Optional[QdrantVectorStore]:
    """Initialize a Qdrant vector store when host info is provided.

    The function is defensive and will return ``None`` if configuration is
    missing instead of raising, keeping startup resilient in environments
    where Qdrant is optional.
    """

    if not config.qdrant_host:
        return None

    return QdrantVectorStore(
        host=config.qdrant_host,
        port=config.qdrant_port,
        api_key=config.qdrant_api_key,
        https=config.qdrant_use_https,
        timeout=config.qdrant_timeout_seconds,
    )
