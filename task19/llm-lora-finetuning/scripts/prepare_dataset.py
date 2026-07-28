"""scripts/prepare_dataset.py — Loads the raw instruction dataset,
formats every example into the project's prompt template, splits it into
train/validation sets, and saves the result to disk for Step 3 (training)
to consume directly.

Run this after check_environment.py confirms your setup is ready:

    python scripts/prepare_dataset.py

Use --preview to print a few formatted examples without saving anything,
useful for sanity-checking the prompt template before committing to it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running this script directly (python scripts/prepare_dataset.py)
# by adding the project root to the import path, so `import config` works
# regardless of the current working directory.
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import Dataset, DatasetDict  # noqa: E402

import config  # noqa: E402


def load_raw_examples(path: Path) -> list[dict[str, str]]:
    """Reads the raw JSONL dataset file into a list of dicts.

    Raises a clear error immediately if the file is missing, rather than
    letting a later step fail with a confusing "file not found" deep
    inside the datasets library.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at '{path}'. Make sure "
            f"'novatech_support.jsonl' (or your own dataset file) exists "
            f"in the data/ folder."
        )

    examples: list[dict[str, str]] = []
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                example = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}: {e}"
                ) from e

            if "instruction" not in example or "response" not in example:
                raise ValueError(
                    f"Line {line_number} of {path} is missing required "
                    f"'instruction' or 'response' key: {example}"
                )
            examples.append(example)

    return examples


def format_example(example: dict[str, str]) -> dict[str, str]:
    """Formats one raw (instruction, response) pair into the project's
    prompt template, producing the exact text the model will be trained
    on.

    Keeping this as a pure function (input dict -> output dict, no side
    effects) makes it trivial to unit test and to apply across the whole
    dataset with `.map()`.
    """
    formatted_text = config.PROMPT_TEMPLATE.format(
        instruction=example["instruction"],
        response=example["response"],
    )
    return {"text": formatted_text}


def build_dataset(raw_examples: list[dict[str, str]]) -> DatasetDict:
    """Converts raw examples into a formatted, train/validation-split
    Hugging Face DatasetDict.

    A DatasetDict (rather than two separate Dataset objects) is the
    standard Hugging Face convention — later scripts can access
    `dataset["train"]` and `dataset["validation"]` directly.
    """
    dataset = Dataset.from_list(raw_examples)
    dataset = dataset.map(format_example)

    split = dataset.train_test_split(
        test_size=config.VALIDATION_SPLIT_RATIO,
        seed=config.RANDOM_SEED,
    )
    # train_test_split names the held-out portion "test" by default;
    # rename it to "validation", which is the more accurate name for how
    # it's actually used in this project (checking training progress, not
    # a final held-out test set).
    return DatasetDict(
        {
            "train": split["train"],
            "validation": split["test"],
        }
    )


def preview_examples(dataset: DatasetDict, num_examples: int = 3) -> None:
    """Prints a few formatted examples so you can visually confirm the
    prompt template looks correct before training on it."""
    print(f"\n{'=' * 60}")
    print(f"PREVIEW: {num_examples} formatted training example(s)")
    print(f"{'=' * 60}")
    for i in range(min(num_examples, len(dataset["train"]))):
        print(f"\n--- Example {i + 1} ---")
        print(dataset["train"][i]["text"])
    print(f"\n{'=' * 60}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the fine-tuning dataset")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print a few formatted examples and exit, without saving anything",
    )
    parser.add_argument(
        "--num-preview",
        type=int,
        default=3,
        help="How many examples to show with --preview (default: 3)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print(f"Loading raw dataset from: {config.RAW_DATASET_PATH}")
    raw_examples = load_raw_examples(config.RAW_DATASET_PATH)
    print(f"Loaded {len(raw_examples)} raw example(s).")

    dataset = build_dataset(raw_examples)
    print(
        f"Split into {len(dataset['train'])} training and "
        f"{len(dataset['validation'])} validation example(s) "
        f"({config.VALIDATION_SPLIT_RATIO:.0%} held out, seed={config.RANDOM_SEED})."
    )

    preview_examples(dataset, num_examples=args.num_preview)

    if args.preview:
        print("(--preview mode: nothing was saved)")
        return

    config.PROCESSED_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    dataset.save_to_disk(str(config.PROCESSED_DATASET_DIR))
    print(f"Saved processed dataset to: {config.PROCESSED_DATASET_DIR}")
    print("Ready for Step 3 (training).")


if __name__ == "__main__":
    main()
