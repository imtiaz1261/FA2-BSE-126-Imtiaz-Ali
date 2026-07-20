"""
retriever.py — Loads the persisted vector store and builds a
RetrievalQA chain that answers questions using ONLY the retrieved PDF
content.

Pipeline for every question:

    User question
        v
    Retriever (similarity search against ChromaDB)
        |  embeds the question with the SAME embedding model used during
        |  ingestion, then finds the K most similar chunks by vector
        |  distance — these are the chunks most likely to contain the answer
        v
    Prompt assembly
        |  the retrieved chunks are inserted into a strict prompt template
        |  that instructs the LLM to answer ONLY from that context
        v
    LLM (Groq's Llama model)
        |  generates the final answer, grounded in the retrieved text
        v
    Answer + source chunks + page numbers returned together
"""

from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from ingest import EMBEDDING_MODEL_NAME
from utils import CHROMA_DIR, get_logger, validate_question

logger = get_logger("retriever")

CHAT_MODEL_NAME = "llama-3.3-70b-versatile"
RETRIEVAL_K = 4  # how many chunks to retrieve per question

# This prompt is the single most important piece of "Retrieval-Augmented
# GENERATION" — it's what forces the LLM to answer only from the
# retrieved context instead of its own general knowledge, and to say a
# specific fallback phrase when the context doesn't contain the answer.
QA_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions \
using ONLY the context below, which was extracted from a PDF document. \
Do not use any outside knowledge, and do not guess.

If the answer cannot be found in the context, respond with EXACTLY this \
sentence and nothing else:
"I couldn't find the answer in the provided document."

Context:
{context}

Question: {question}

Answer:"""


def load_vector_store(persist_directory: str = CHROMA_DIR) -> Chroma:
    """Reopens the persisted ChromaDB collection created by ingest.py.

    Note: the SAME embedding model used during ingestion must be used
    here too — embeddings from two different models aren't comparable,
    since each model maps text into its own distinct vector space.
    """
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    return Chroma(persist_directory=persist_directory, embedding_function=embeddings)


def build_qa_chain(vector_store: Chroma, api_key: str, k: int = RETRIEVAL_K) -> RetrievalQA:
    """Builds a RetrievalQA chain wiring together the retriever, the
    grounding prompt, and the LLM.

    - `search_kwargs={"k": k}` controls how many chunks come back per
      question — more chunks give the LLM more context but cost more
      tokens and can dilute relevance; k=4 is a reasonable default.
    - `return_source_documents=True` makes the chain also hand back the
      exact chunks it used, which is what lets app.py display retrieved
      chunks and source page numbers.
    - `chain_type="stuff"` means all retrieved chunks are concatenated
      ("stuffed") directly into the prompt's {context} — simple and
      effective for a small number of chunks like k=4.
    """
    llm = ChatGroq(model=CHAT_MODEL_NAME, api_key=api_key, temperature=0)

    prompt = PromptTemplate(
        template=QA_PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": k})

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    return qa_chain


def answer_question(qa_chain: RetrievalQA, question: str) -> dict:
    """Runs a question through the QA chain and returns a clean result
    dict with the answer and formatted source information.

    Validates the question isn't empty before spending an API call on it
    — this is the "empty question" error case from the project spec.
    """
    question = validate_question(question)

    result = qa_chain.invoke({"query": question})

    sources = []
    for doc in result.get("source_documents", []):
        sources.append(
            {
                "source_file": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page", "unknown"),
                "content_preview": doc.page_content[:200].strip() + "...",
            }
        )

    return {
        "question": question,
        "answer": result["result"].strip(),
        "sources": sources,
    }