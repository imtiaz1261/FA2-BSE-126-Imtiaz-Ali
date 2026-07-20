"""
app.py — Main entry point. Run this to ask questions about your PDF(s):

    python app.py

Assumes you've already run `python ingest.py` at least once to build the
vector database from your PDFs in data/.
"""

from retriever import answer_question, build_qa_chain, load_vector_store
from utils import get_logger, load_environment, validate_vector_store_exists

logger = get_logger("app")

SHOW_RETRIEVED_CHUNKS = True  # set False to hide the "retrieved chunks" section
EXIT_WORDS = {"exit", "quit"}


def print_result(result: dict) -> None:
    """Displays the question, (optionally) retrieved chunks, final
    answer, and source page numbers — matching the project's display
    requirements."""
    print("\n" + "=" * 70)
    print(f"Question: {result['question']}")
    print("=" * 70)

    if SHOW_RETRIEVED_CHUNKS and result["sources"]:
        print("\nRetrieved chunks:")
        for i, src in enumerate(result["sources"], start=1):
            print(f"\n  [{i}] {src['source_file']} (page {src['page']})")
            print(f"      {src['content_preview']}")

    print(f"\nAnswer:\n  {result['answer']}")

    if result["sources"] and "couldn't find" not in result["answer"].lower():
        pages = sorted({str(src["page"]) for src in result["sources"]})
        print(f"\nSource page(s): {', '.join(pages)}")

    print("=" * 70 + "\n")


def main() -> None:
    # Fail fast with clear messages for the two most common setup mistakes:
    # missing API key, and asking questions before ever running ingest.py.
    try:
        api_key = load_environment()
        validate_vector_store_exists()
    except (EnvironmentError, FileNotFoundError) as e:
        logger.error(str(e))
        return

    logger.info("Loading vector store...")
    vector_store = load_vector_store()

    logger.info("Building QA chain...")
    qa_chain = build_qa_chain(vector_store, api_key=api_key)

    print("\nPDF Question Answering System ready. Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            question = input("Ask a question about your PDF: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in EXIT_WORDS:
            print("Goodbye!")
            break

        try:
            result = answer_question(qa_chain, question)
        except ValueError as e:
            # empty question — validate_question() raises this
            print(f"[Error] {e}")
            continue
        except Exception as e:
            print(f"[Error] Something went wrong answering that question: {e}")
            continue

        print_result(result)


if __name__ == "__main__":
    main()