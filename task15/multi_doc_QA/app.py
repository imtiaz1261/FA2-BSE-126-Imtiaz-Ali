"""
app.py
------
Main entry point for the Multi-Document Question Answering System.

Complete RAG workflow:
    1. Load documents (PDF / DOCX / TXT) from the data/ directory.
    2. Split them into overlapping chunks.
    3. Embed the chunks and store them in a vector database
       (reusing a persisted store if one already exists).
    4. Build a retriever + RetrievalQA chain.
    5. Loop: take a user question, retrieve relevant chunks, generate
       an answer grounded only in that context, and display the answer
       plus its sources.

Run with:
    python app.py
    python app.py --rebuild      # force a fresh rebuild of the vector store
    python app.py --show-context # also print retrieved chunks per answer
"""

import argparse
import sys

from config import DATA_DIR, TOP_K, NO_ANSWER_MESSAGE
from utils import get_logger, clean_query
from loader import load_documents_from_directory, DocumentLoadError
from splitter import split_documents
from embeddings import get_embedding_model, EmbeddingModelError
from vector_store import get_or_build_vector_store, VectorStoreError
from retriever import get_retriever, retrieve_context
from qa_chain import build_qa_chain, answer_question, QAChainError

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-Document QA System")
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Force rebuilding the vector store from scratch, ignoring any "
             "existing persisted database.",
    )
    parser.add_argument(
        "--show-context", action="store_true",
        help="Print the retrieved context chunks alongside each answer.",
    )
    parser.add_argument(
        "--data-dir", type=str, default=str(DATA_DIR),
        help="Directory containing PDF/DOCX/TXT files to index.",
    )
    return parser.parse_args()


def print_sources(source_documents) -> None:
    """Pretty-print the provenance of an answer: file name + page/paragraph."""
    if not source_documents:
        print("Sources: (none)")
        return

    print("Sources:")
    seen = set()
    for doc in source_documents:
        file_name = doc.metadata.get("file_name", "unknown")
        if "page" in doc.metadata:
            label = f"  - {file_name} (page {doc.metadata['page']})"
        elif "paragraph" in doc.metadata:
            label = f"  - {file_name} (paragraph {doc.metadata['paragraph']})"
        else:
            label = f"  - {file_name}"
        if label not in seen:
            print(label)
            seen.add(label)


def build_pipeline(data_dir: str, force_rebuild: bool):
    """Run steps 1-4 of the RAG workflow and return a ready-to-use QA chain."""
    logger.info("=== Step 1/4: Loading documents ===")

    def _load_and_split():
        docs = load_documents_from_directory(data_dir)
        return split_documents(docs)

    logger.info("=== Step 2/4: Preparing embedding model ===")
    embedding_model = get_embedding_model()

    logger.info("=== Step 3/4: Loading or building vector store ===")
    vector_store = get_or_build_vector_store(
        chunks_provider=_load_and_split,
        embedding_model=embedding_model,
        force_rebuild=force_rebuild,
    )

    logger.info("=== Step 4/4: Building retriever + QA chain ===")
    retriever = get_retriever(vector_store, top_k=TOP_K)
    qa_chain = build_qa_chain(retriever)

    return vector_store, qa_chain


def run_interactive_loop(vector_store, qa_chain, show_context: bool) -> None:
    print("\nMulti-Document QA System is ready.")
    print("Type your question, or 'exit' / 'quit' to stop.\n")

    while True:
        try:
            raw_query = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if raw_query.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        try:
            query = clean_query(raw_query)
        except ValueError as exc:
            print(f"  ! {exc}\n")
            continue

        if show_context:
            context_chunks = retrieve_context(vector_store, query, top_k=TOP_K)
            print("\nRetrieved context:")
            for i, chunk in enumerate(context_chunks, start=1):
                snippet = chunk.page_content[:200].replace("\n", " ")
                print(f"  [{i}] {snippet}...")
            print()

        try:
            result = answer_question(qa_chain, query)
        except Exception as exc:
            logger.error("Error while generating answer: %s", exc)
            print(f"  ! An error occurred while generating the answer: {exc}\n")
            continue

        print(f"\nAnswer: {result['answer']}\n")
        if result["answer"].strip() != NO_ANSWER_MESSAGE:
            print_sources(result["source_documents"])
        print()


def main() -> int:
    args = parse_args()

    try:
        vector_store, qa_chain = build_pipeline(args.data_dir, args.rebuild)
    except DocumentLoadError as exc:
        logger.error("Document loading failed: %s", exc)
        print(f"\nError loading documents: {exc}")
        print(f"Add PDF, DOCX, or TXT files to '{args.data_dir}' and try again.")
        return 1
    except EmbeddingModelError as exc:
        logger.error("Embedding model error: %s", exc)
        print(f"\nError preparing the embedding model: {exc}")
        return 1
    except VectorStoreError as exc:
        logger.error("Vector store error: %s", exc)
        print(f"\nError preparing the vector store: {exc}")
        return 1
    except QAChainError as exc:
        logger.error("QA chain error: %s", exc)
        print(f"\nError preparing the LLM / QA chain: {exc}")
        return 1

    run_interactive_loop(vector_store, qa_chain, args.show_context)
    return 0


if __name__ == "__main__":
    sys.exit(main())