"""
CLI entry point for exercising the Phase 1 RAG engine end to end.

This exists so the pipeline is testable without a web framework —
Phase 2 wraps `IngestionService` and `RAGService` in FastAPI routes
without changing either class.

Usage:
    python main.py ingest data/uploads/handbook.pdf
    python main.py query "What is the refund policy?"
    python main.py query "What is the refund policy?" --top-k 6
"""

import argparse
import json
import sys

from app.core.exceptions import JarvisLiteError
from app.core.logging_config import configure_logging
from app.rag.rag_service import RAGService
from app.services.ingestion_service import IngestionService


def _cmd_ingest(args: argparse.Namespace) -> None:
    service = IngestionService()
    result = service.ingest_file(args.file_path)
    print(json.dumps(result, indent=2))


def _cmd_query(args: argparse.Namespace) -> None:
    service = RAGService()
    result = service.query(args.question, top_k=args.top_k)
    print(f"\nAnswer:\n{result['answer']}\n")
    print("Sources:")
    for source in result["sources"]:
        page = f", page {source['page']}" if source.get("page") else ""
        print(f"  - {source['document_name']}{page}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis-lite", description="Jarvis-Lite Phase 1 RAG engine CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a PDF/DOCX/TXT file into the vector store")
    ingest_parser.add_argument("file_path", help="Path to the file to ingest")
    ingest_parser.set_defaults(func=_cmd_ingest)

    query_parser = subparsers.add_parser("query", help="Ask a question against ingested documents")
    query_parser.add_argument("question", help="The question to ask")
    query_parser.add_argument("--top-k", type=int, default=None, help="Override RETRIEVAL_TOP_K")
    query_parser.set_defaults(func=_cmd_query)

    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
    except JarvisLiteError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
