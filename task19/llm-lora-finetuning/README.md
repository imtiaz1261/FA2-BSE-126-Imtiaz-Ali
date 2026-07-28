# Fine-Tuning a Small Open-Source LLM Using LoRA (PEFT)

> This README is a placeholder for Step 1. The complete, professional
> README (project overview, setup, usage, results, and comparison
> tables) will be written in the final step of this guided project.

## Project structure (so far)

```
llm-lora-finetuning/
├── config.py              # (added in a later step)
├── requirements.txt        # Pinned dependencies
├── .gitignore
├── data/                    # Training/validation datasets (gitignored)
├── scripts/
│   └── check_environment.py  # Verifies your setup is ready
├── models/
│   └── fine_tuned/           # Fine-tuned model output (gitignored)
└── logs/                     # Training logs / TensorBoard (gitignored)
```

## Step 1 status: Environment setup

See the main chat response for full explanation. Quick start:

```
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
python scripts/check_environment.py
```
