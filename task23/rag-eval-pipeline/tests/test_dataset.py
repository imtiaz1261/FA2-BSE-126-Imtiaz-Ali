"""Unit tests for dataset/schema.py and dataset/loader.py.

Requires pydantic — install project requirements before running
(these tests cannot execute in a pydantic-free environment).
"""

from __future__ import annotations

from pathlib import Path

from dataset.loader import load_dataset, save_dataset
from dataset.schema import EvalDataset, EvalRecord, QuestionCategory

DATASET_PATH = Path(__file__).parent.parent / "dataset" / "evaluation_dataset.json"


def test_load_dataset_has_20_records():
    dataset = load_dataset(DATASET_PATH)
    assert len(dataset) == 20


def test_load_dataset_covers_all_categories():
    dataset = load_dataset(DATASET_PATH)
    categories_present = {r.category for r in dataset.records}
    assert categories_present == set(QuestionCategory)


def test_record_ids_are_unique():
    dataset = load_dataset(DATASET_PATH)
    ids = [r.id for r in dataset.records]
    assert len(ids) == len(set(ids))


def test_by_category_filters_correctly():
    dataset = load_dataset(DATASET_PATH)
    fact_based = dataset.by_category(QuestionCategory.FACT_BASED)
    assert all(r.category == QuestionCategory.FACT_BASED for r in fact_based)
    assert len(fact_based) > 0


def test_save_and_reload_roundtrip(tmp_path):
    original = load_dataset(DATASET_PATH)
    original.records[0].generated_answer = "A test answer"
    original.records[0].retrieved_context = ["some retrieved chunk"]

    out_path = tmp_path / "roundtrip.json"
    save_dataset(original, out_path)

    reloaded = load_dataset(out_path)
    assert reloaded.records[0].generated_answer == "A test answer"
    assert reloaded.records[0].retrieved_context == ["some retrieved chunk"]


def test_eval_record_defaults_are_empty():
    record = EvalRecord(
        id="q_test",
        category=QuestionCategory.FACT_BASED,
        question="Q?",
        ground_truth="A.",
    )
    assert record.retrieved_context == []
    assert record.generated_answer == ""
