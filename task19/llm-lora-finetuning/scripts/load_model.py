"""scripts/load_model.py — Loads the base model + tokenizer, and wraps
the model with a LoRA adapter configuration.

Run this on its own to sanity-check that the base model loads correctly
and to see exactly how many parameters LoRA makes trainable, before
moving on to the full training script in Step 4:

    python scripts/load_model.py

This step downloads TinyLlama-1.1B (~2.2GB) from Hugging Face on first
run, and caches it locally afterward — later runs won't re-download it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch  # noqa: E402
from peft import LoraConfig, get_peft_model, PeftModel  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizerBase,
)

import config  # noqa: E402


def get_device_and_dtype() -> tuple[str, torch.dtype]:
    """Picks the best available device and a matching, safe dtype.

    float32 on CPU is slower but numerically stable and universally
    supported. On GPU, bfloat16 is preferred when available (better
    numerical range than float16, and doesn't need loss-scaling), falling
    back to float16 on older GPUs that lack bfloat16 support.
    """
    if torch.cuda.is_available():
        if torch.cuda.is_bf16_supported():
            return "cuda", torch.bfloat16
        return "cuda", torch.float16
    return "cpu", torch.float32


def load_tokenizer(model_name: str) -> PreTrainedTokenizerBase:
    """Loads the tokenizer for the base model.

    TinyLlama's tokenizer (like many Llama-derived tokenizers) has no
    pad token defined by default. Training requires one (to pad shorter
    sequences up to a common batch length), so we fall back to using the
    end-of-sequence token as the pad token — a standard, safe convention.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return tokenizer


def load_base_model(model_name: str, device: str, dtype: torch.dtype) -> PreTrainedModel:
    """Downloads (or loads from cache) the base model's architecture and
    pretrained weights."""
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
    )
    model.to(device)
    return model


def build_lora_config() -> LoraConfig:
    """Builds the LoRA configuration from the settings in config.py.

    task_type=CAUSAL_LM tells PEFT this is a text-generation model
    (as opposed to e.g. sequence classification), which affects how it
    wraps the model internally.
    """
    return LoraConfig(
        r=config.LORA_R,
        lora_alpha=config.LORA_ALPHA,
        target_modules=config.LORA_TARGET_MODULES,
        lora_dropout=config.LORA_DROPOUT,
        bias="none",
        task_type="CAUSAL_LM",
    )


def apply_lora(model: PreTrainedModel, lora_config: LoraConfig) -> PeftModel:
    """Wraps the base model with LoRA adapters, freezing all original
    weights and leaving only the small adapter matrices trainable."""
    return get_peft_model(model, lora_config)


def count_parameters(model: torch.nn.Module) -> tuple[int, int]:
    """Returns (trainable_params, total_params) for any PyTorch model.

    This is the concrete proof that LoRA is working as advertised — if
    trainable_params is a tiny fraction of total_params, the freeze
    actually took effect.
    """
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    return trainable, total


def print_parameter_summary(model: torch.nn.Module, label: str) -> None:
    trainable, total = count_parameters(model)
    percentage = (trainable / total * 100) if total > 0 else 0.0
    print(f"\n{label}")
    print(f"  Trainable parameters: {trainable:,}")
    print(f"  Total parameters:     {total:,}")
    print(f"  Trainable percentage: {percentage:.4f}%")


def main() -> None:
    device, dtype = get_device_and_dtype()
    print(f"Device: {device}, dtype: {dtype}")

    print(f"\nLoading tokenizer: {config.BASE_MODEL_NAME}")
    tokenizer = load_tokenizer(config.BASE_MODEL_NAME)
    print(f"Tokenizer loaded. Vocab size: {tokenizer.vocab_size:,}")

    print(f"\nLoading base model: {config.BASE_MODEL_NAME}")
    print("(first run downloads ~2.2GB — this may take a while)")
    base_model = load_base_model(config.BASE_MODEL_NAME, device, dtype)
    print_parameter_summary(base_model, "BEFORE LoRA (base model, all weights trainable by default):")

    lora_config = build_lora_config()
    print(f"\nApplying LoRA config: r={lora_config.r}, alpha={lora_config.lora_alpha}, "
          f"target_modules={lora_config.target_modules}")
    peft_model = apply_lora(base_model, lora_config)
    print_parameter_summary(peft_model, "AFTER LoRA (base weights frozen, only adapters trainable):")

    print("\nModel + LoRA setup complete. Ready for Step 4 (training).")


if __name__ == "__main__":
    main()