"""
vector_stores/factory.py
---------------------------
Builds the configured vector store backend so the rest of the app
depends only on the BaseVectorStore interface.
"""
from config import Config
from vector_stores.base import BaseVectorStore
from exceptions import ConfigurationError
from logger import get_logger

logger = get_logger(__name__)


def get_vector_store(config: Config, embedding_dimension: int) -> BaseVectorStore:
    provider = config.vector_db_provider

    if provider == "chroma":
        from vector_stores.chroma_store import ChromaVectorStore
        return ChromaVectorStore(
            persist_directory=str(config.resolved_persist_path()),
            collection_name=config.collection_name,
        )

    if provider == "pinecone":
        from vector_stores.pinecone_store import PineconeVectorStore
        return PineconeVectorStore(
            api_key=config.pinecone_api_key,
            index_name=config.pinecone_index_name,
            dimension=embedding_dimension,
            cloud=config.pinecone_cloud,
            region=config.pinecone_region,
        )

    if provider == "memory":
        from vector_stores.memory_store import InMemoryVectorStore
        logger.warning("Using in-memory vector store — dev/testing only, not persistent.")
        return InMemoryVectorStore(collection_name=config.collection_name)

    raise ConfigurationError(f"Unknown vector store provider: {provider}")
