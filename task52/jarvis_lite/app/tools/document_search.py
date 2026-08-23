"""
Document Search Tool — searches ingested documents using RAG.

This tool wraps the RAG pipeline for the agent to use.
"""

import logging
from typing import Any, Dict, Optional

from app.core.exceptions import ToolError
from app.rag.rag_service_with_memory import RAGServiceWithMemory
from app.tools.base import BaseTool, ToolOutput

logger = logging.getLogger(__name__)


class DocumentSearchTool(BaseTool):
    """Tool for searching documents using RAG."""

    def __init__(self, rag_service: Optional[RAGServiceWithMemory] = None) -> None:
        """
        Initialize document search tool.
        
        Args:
            rag_service: RAGServiceWithMemory instance
        """
        super().__init__(
            name="search_documents",
            description="Searches through ingested documents using semantic similarity. "
                       "Returns relevant document excerpts with sources. "
                       "Example: 'search documents for: refund policy'"
        )
        self.rag_service = rag_service

    def set_rag_service(self, rag_service: RAGServiceWithMemory) -> None:
        """Set the RAG service instance."""
        self.rag_service = rag_service

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find in documents"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top results to return (default: 4)",
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str, top_k: Optional[int] = None, **kwargs) -> ToolOutput:
        """
        Search documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            ToolOutput with search results
        """
        try:
            if not self.rag_service:
                raise ToolError("RAG service not initialized")
            
            if not isinstance(query, str):
                raise ToolError(f"Query must be a string, got {type(query)}")
            
            if not query.strip():
                raise ToolError("Query cannot be empty")
            
            # Call RAG service but don't use LLM generation
            # Just return the retrieved chunks
            retrieved = self.rag_service._retriever.retrieve(query, top_k or 4)
            
            if not retrieved:
                logger.info(f"No documents found for query: {query}")
                return ToolOutput(
                    tool_name=self.name,
                    success=True,
                    result={
                        "query": query,
                        "found": False,
                        "results": [],
                        "message": "No relevant documents found"
                    },
                    metadata={"query": query}
                )
            
            # Format results
            results = []
            seen_sources = set()
            
            for chunk in retrieved:
                source_key = (
                    chunk.metadata.get("document_name", "unknown"),
                    chunk.metadata.get("page")
                )
                
                results.append({
                    "document": chunk.metadata.get("document_name", "unknown"),
                    "page": chunk.metadata.get("page"),
                    "relevance_score": round(chunk.score, 4),
                    "excerpt": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    "chunk_id": chunk.metadata.get("chunk_id")
                })
                
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
            
            logger.info(f"Document search: found {len(results)} results for '{query}'")
            
            return ToolOutput(
                tool_name=self.name,
                success=True,
                result={
                    "query": query,
                    "found": True,
                    "result_count": len(results),
                    "results": results,
                    "sources": list(seen_sources)
                },
                metadata={"query": query, "result_count": len(results)}
            )
        
        except ToolError as e:
            logger.warning(f"Document search error: {e}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=str(e)
            )
        except Exception as e:
            error = f"Document search failed: {e}"
            logger.exception(f"Document search exception: {e}")
            return ToolOutput(
                tool_name=self.name,
                success=False,
                result=None,
                error=error
            )
