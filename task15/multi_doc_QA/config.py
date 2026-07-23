"""
config.py
---------
Central configuration for the Multi-Document QA System.

All tunable parameters (paths, chunking, embeddings, vector store, LLM)
live here so the rest of the codebase never hardcodes a "magic value".
Values are read from environment variables (via a .env file) with
sensible defaults, so the app runs out-of-the-box for a beginner while
remaining fully configurable for advanced users.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present)
load_dotenv()


# --------------------------------------------------------------------------
# Path configuration
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_DIR", BASE_DIR / "chroma_db"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
LOG_FILE = LOG_DIR / "app.log"

# Make sure required directories exist
for _dir in (DATA_DIR, VECTOR_DB_DIR, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Supported file types
# --------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


# --------------------------------------------------------------------------
# Text splitting configuration
# --------------------------------------------------------------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))


# --------------------------------------------------------------------------
# Embedding configuration
# --------------------------------------------------------------------------
# "sentence_transformers" (default, local, free) or "openai"
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers")
SENTENCE_TRANSFORMER_MODEL = os.getenv(
    "SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"
)
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# --------------------------------------------------------------------------
# Vector store configuration
# --------------------------------------------------------------------------
# "chroma" (default) or "faiss"
VECTOR_STORE_PROVIDER = os.getenv("VECTOR_STORE_PROVIDER", "chroma")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "multi_doc_qa")
FAISS_INDEX_DIR = Path(os.getenv("FAISS_INDEX_DIR", BASE_DIR / "faiss_index"))


# --------------------------------------------------------------------------
# Retrieval configuration
# --------------------------------------------------------------------------
TOP_K = int(os.getenv("TOP_K", 4))


# --------------------------------------------------------------------------
# LLM configuration (used by qa_chain.py to generate the final answer)
# --------------------------------------------------------------------------
# "groq" (free, fast, hosted), "openai", or "ollama" (local).
# Defaults to groq; falls back gracefully if no API key is configured
# (see qa_chain.py).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.0))

# Standard fallback message when the answer isn't in the documents
NO_ANSWER_MESSAGE = "I couldn't find the answer in the provided documents."