"""config.py — Central configuration shared across every script in this
project.

Keeping paths, the prompt template, and model settings here (instead of
duplicated in each script) means changing them once updates the whole
pipeline consistently.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATASET_PATH = DATA_DIR / "novatech_support.jsonl"
PROCESSED_DATASET_DIR = DATA_DIR / "processed"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "models" / "fine_tuned"
LOGS_DIR = PROJECT_ROOT / "logs"

# ---------------------------------------------------------------------------
# Base model (defined here since Step 2's tokenization preview needs to
# know which tokenizer to use)
# ---------------------------------------------------------------------------
BASE_MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# ---------------------------------------------------------------------------
# LoRA configuration
#
# r (rank): size of the LoRA adapter matrices. Higher = more trainable
#   capacity but more parameters and slower training. 8 is a common,
#   reasonable default for small fine-tuning tasks like this one.
# lora_alpha: scaling factor applied to the adapter's output. The
#   effective strength of the adapter is (lora_alpha / r), so alpha=16
#   with r=8 gives a scaling factor of 2x — a common starting ratio.
# target_modules: which weight matrices inside the model get adapters.
#   For Llama-architecture models (TinyLlama included), the attention
#   projections are the standard, well-tested choice.
# lora_dropout: regularization to reduce overfitting — matters more here
#   since our dataset is small (only 25 training examples).
# ---------------------------------------------------------------------------
LORA_R = 8
LORA_ALPHA = 16
LORA_DROPOUT = 0.05
LORA_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj"]

# ---------------------------------------------------------------------------
# Dataset split
# ---------------------------------------------------------------------------
VALIDATION_SPLIT_RATIO = 0.15  # 15% of examples held out for validation
RANDOM_SEED = 42  # fixed seed so the split is reproducible across runs

# ---------------------------------------------------------------------------
# Prompt template
#
# Every training example is formatted into this exact shape. Consistency
# here matters a lot — the model learns to associate THIS pattern with
# "now generate a response," so the same template must be used at
# inference time too (Step 11), or the model won't recognize the prompt.
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE = """### Instruction:
{instruction}

### Response:
{response}"""

# Same template but without the response filled in — used at inference
# time when we want the model to GENERATE the response.
INFERENCE_PROMPT_TEMPLATE = """### Instruction:
{instruction}

### Response:
"""