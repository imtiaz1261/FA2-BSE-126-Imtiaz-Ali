"""config.py — Central configuration shared across every module in this
project."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
INDEX_DIR = PROJECT_ROOT / "data" / "index"
FAISS_INDEX_PATH = INDEX_DIR / "faiss_index"
BM25_INDEX_PATH = INDEX_DIR / "bm25_index.pkl"
EVAL_QUERIES_PATH = PROJECT_ROOT / "eval" / "eval_queries.json"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL_NAME = "llama-3.3-70b-versatile"  # via Groq's free API

# ---------------------------------------------------------------------------
# Retrieval settings
# ---------------------------------------------------------------------------
TOP_K_BM25 = 5          # candidates retrieved from BM25
TOP_K_VECTOR = 5         # candidates retrieved from vector search
TOP_K_HYBRID = 5         # candidates kept after hybrid fusion
TOP_K_RERANKED = 3       # final candidates kept after cross-encoder reranking

# Hybrid fusion weighting: how much weight BM25 vs. vector search scores
# get after normalization. Must sum to 1.0. Configurable per the project
# spec's "adjustable hybrid retrieval weights" bonus feature.
BM25_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5

# ---------------------------------------------------------------------------
# Evaluation settings
# ---------------------------------------------------------------------------
EVAL_K = 3  # the "K" in Precision@K, Recall@K, NDCG@K for evaluation
