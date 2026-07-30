"""
Core evaluator: runs the RAG chatbot over the evaluation dataset, then scores
each answer using either real RAGAS metrics (production) or the heuristic
fallback (offline/dev — see metrics/heuristic_metrics.py).

Usage:
    evaluator = RagasEvaluator(chatbot, use_ragas=True)
    results_df = evaluator.run(dataset)
"""

from __future__ import annotations

import pandas as pd

from dataset.schema import EvalDataset
from metrics.heuristic_metrics import compute_all_heuristic_metrics
from rag_pipeline.chatbot import RAGChatbot
from utils.logger import get_logger

logger = get_logger(__name__)


class RagasEvaluator:
    """Evaluates a RAG chatbot against an EvalDataset."""

    def __init__(self, chatbot: RAGChatbot, use_ragas: bool = False, k: int = 3):
        """
        Args:
            chatbot: The RAG chatbot under evaluation.
            use_ragas: If True, score with real RAGAS metrics (requires the
                `ragas` package and a configured LLM — OpenAI or Groq, per
                `settings.llm_provider`). If False, use the offline heuristic
                approximation instead.
            k: Number of context chunks to retrieve per question.
        """
        self.chatbot = chatbot
        self.use_ragas = use_ragas
        self.k = k

    def run(self, dataset: EvalDataset) -> pd.DataFrame:
        """Run the chatbot over every record, then score every answer."""
        logger.info(
            "Starting evaluation of %d questions (scoring backend: %s)",
            len(dataset),
            "RAGAS" if self.use_ragas else "heuristic (offline)",
        )

        for record in dataset.records:
            generated_answer, retrieved_context = self.chatbot.answer(
                record.question, k=self.k
            )
            record.generated_answer = generated_answer
            record.retrieved_context = retrieved_context
            logger.debug("Answered [%s]: %s", record.id, record.question)

        if self.use_ragas:
            return self._score_with_ragas(dataset)
        return self._score_with_heuristics(dataset)

    def _score_with_heuristics(self, dataset: EvalDataset) -> pd.DataFrame:
        rows = []
        for record in dataset.records:
            scores = compute_all_heuristic_metrics(
                question=record.question,
                generated_answer=record.generated_answer,
                retrieved_context=record.retrieved_context,
                ground_truth=record.ground_truth,
                expected_context=record.expected_context,
            )
            rows.append(
                {
                    "id": record.id,
                    "category": record.category.value,
                    "question": record.question,
                    "ground_truth": record.ground_truth,
                    "generated_answer": record.generated_answer,
                    "retrieved_context": " | ".join(record.retrieved_context),
                    **scores,
                }
            )
        return pd.DataFrame(rows)

    def _score_with_ragas(self, dataset: EvalDataset) -> pd.DataFrame:
        """Production scoring path using the real RAGAS library.

        RAGAS needs both an LLM (to judge faithfulness/relevancy/etc.) and an
        embeddings model (for the similarity-based metrics). Which ones it
        uses depends on `settings.llm_provider`:

          - openai: RAGAS's own OpenAI defaults (LLM + embeddings both OpenAI).
          - groq: Groq's LLM (OpenAI-compatible endpoint) wrapped for RAGAS,
            paired with local sentence-transformers embeddings — Groq itself
            has no embeddings endpoint.
        """
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_correctness,
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        from config.settings import LLMProvider, settings

        hf_dataset = Dataset.from_dict(
            {
                "question": [r.question for r in dataset.records],
                "answer": [r.generated_answer for r in dataset.records],
                "contexts": [r.retrieved_context for r in dataset.records],
                "ground_truth": [r.ground_truth for r in dataset.records],
            }
        )

        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        ]

        eval_kwargs: dict = {}
        if settings.llm_provider == LLMProvider.GROQ:
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_openai import ChatOpenAI
            from ragas.embeddings import LangchainEmbeddingsWrapper
            from ragas.llms import LangchainLLMWrapper

            ragas_llm = ChatOpenAI(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                temperature=0,
            )
            eval_kwargs["llm"] = LangchainLLMWrapper(ragas_llm)
            eval_kwargs["embeddings"] = LangchainEmbeddingsWrapper(
                HuggingFaceEmbeddings(model_name=settings.embedding_model)
            )

        result = evaluate(hf_dataset, metrics=metrics, **eval_kwargs)
        scores_df = result.to_pandas()
        scores_df.insert(0, "id", [r.id for r in dataset.records])
        scores_df.insert(1, "category", [r.category.value for r in dataset.records])
        return scores_df
