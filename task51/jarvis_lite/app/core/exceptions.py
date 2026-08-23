"""Exception hierarchy shared across every Jarvis-Lite module.

Each stage of the pipeline raises a specific subclass of
`JarvisLiteError` so callers (and, later, FastAPI exception handlers)
can catch precisely what they care about instead of bare `Exception`.
"""


class JarvisLiteError(Exception):
    """Base class for all Jarvis-Lite errors."""


class UnsupportedFileTypeError(JarvisLiteError):
    """Raised when a file extension has no registered loader."""


class DocumentLoadError(JarvisLiteError):
    """Raised when a document exists but its content can't be extracted."""


class EmptyDocumentError(JarvisLiteError):
    """Raised when a document contains no usable text after cleaning."""


class ChunkingError(JarvisLiteError):
    """Raised when chunking fails or produces zero chunks."""


class EmbeddingError(JarvisLiteError):
    """Raised when embedding generation fails (bad key, provider error, etc.)."""


class VectorStoreError(JarvisLiteError):
    """Raised for vector database failures (create/add/search/delete)."""


class RetrievalError(JarvisLiteError):
    """Raised when retrieval itself fails (distinct from 'zero results', which is not an error)."""


class GenerationError(JarvisLiteError):
    """Raised when the LLM call to generate a final answer fails."""


class MemoryError(JarvisLiteError):
    """Raised when memory management fails."""


class ToolError(JarvisLiteError):
    """Raised when a tool execution fails."""


class AgentError(JarvisLiteError):
    """Raised when agent routing or execution fails."""

