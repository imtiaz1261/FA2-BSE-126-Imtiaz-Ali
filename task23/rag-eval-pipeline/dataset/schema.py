"""
Data schema for the RAG evaluation dataset.

Every evaluation record captures everything RAGAS needs (question, retrieved
context, generated answer, ground truth) plus metadata used for grouping and
reporting (category, difficulty). Using Pydantic here means a malformed
dataset file fails validation immediately, with a clear error, instead of
crashing deep inside the evaluation run.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QuestionCategory(str, Enum):
    FACT_BASED = "fact_based"
    DEFINITION = "definition"
    MULTI_HOP = "multi_hop"
    SUMMARIZATION = "summarization"
    COMPARATIVE = "comparative"
    EDGE_CASE = "edge_case"
    OUT_OF_CONTEXT = "out_of_context"
    AMBIGUOUS = "ambiguous"


class EvalRecord(BaseModel):
    """A single test case in the evaluation dataset."""

    id: str = Field(..., description="Unique identifier, e.g. 'q001'")
    category: QuestionCategory
    question: str
    ground_truth: str = Field(..., description="Reference / ideal answer")
    expected_context: list[str] = Field(
        default_factory=list,
        description="The context chunk(s) the retriever SHOULD return for this question",
    )
    # The following two fields are populated at runtime by the RAG pipeline,
    # not hand-authored in the dataset file. They default to empty so the
    # same schema serves both the static dataset and the runtime-enriched copy.
    retrieved_context: list[str] = Field(default_factory=list)
    generated_answer: str = Field(default="")


class EvalDataset(BaseModel):
    """The full collection of evaluation records."""

    records: list[EvalRecord]

    def __len__(self) -> int:
        return len(self.records)

    def by_category(self, category: QuestionCategory) -> list[EvalRecord]:
        return [r for r in self.records if r.category == category]
