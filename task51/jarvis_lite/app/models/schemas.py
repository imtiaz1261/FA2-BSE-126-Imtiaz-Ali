"""Pydantic schemas — shared response shapes, ready to reuse as FastAPI response_models
once the API layer is added in a later phase."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SourceOut(BaseModel):
    document_name: str
    page: Optional[int] = None
    chunk_id: Optional[str] = None


class RetrievedChunkOut(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float


class RAGQueryResult(BaseModel):
    answer: str
    sources: List[SourceOut]
    retrieved_chunks: List[RetrievedChunkOut]


class IngestionResult(BaseModel):
    filename: str
    document_units: int
    chunks_created: int
