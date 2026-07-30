"""
Loading and saving utilities for the evaluation dataset.

Kept separate from schema.py so that I/O concerns (file paths, JSON
encoding) don't bleed into the pure data model.
"""

from __future__ import annotations

import json
from pathlib import Path

from dataset.schema import EvalDataset
from utils.logger import get_logger

logger = get_logger(__name__)


def load_dataset(path: str | Path) -> EvalDataset:
    """Load and validate the evaluation dataset from a JSON file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    dataset = EvalDataset.model_validate(raw)
    logger.info("Loaded %d evaluation records from %s", len(dataset), path)
    return dataset


def save_dataset(dataset: EvalDataset, path: str | Path) -> None:
    """Persist the (possibly runtime-enriched) dataset back to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    logger.info("Saved %d evaluation records to %s", len(dataset), path)
