"""
exceptions.py
-------------
Custom exception hierarchy for the vector search module, so callers
can catch precise failure modes instead of bare Exception.
"""


class VectorSearchError(Exception):
    """Base class for all errors raised by this module."""


class ConfigurationError(VectorSearchError):
    """Raised when required configuration/environment variables are missing or invalid."""


class ValidationError(VectorSearchError):
    """Raised when input (query, document, metadata) fails validation."""


class EmbeddingError(VectorSearchError):
    """Raised when embedding generation fails."""


class VectorStoreError(VectorSearchError):
    """Raised when a vector database operation (add/query/delete) fails."""


class DocumentLoadError(VectorSearchError):
    """Raised when documents cannot be read or parsed from disk."""
