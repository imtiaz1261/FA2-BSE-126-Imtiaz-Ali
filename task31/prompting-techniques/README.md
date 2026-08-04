# Prompting Technique Comparison

Compares 5 prompting techniques — zero-shot, few-shot, role-based,
step-by-step, and format-specific — applied to the same task, to see
which produces the best result and why.

## Structure
```
prompting-techniques/
├── prompts.py               # the task + all 5 prompt variants
├── run_comparison.py         # calls Groq for each prompt, saves outputs
├── comparison_note.md         # the analysis: what changed, which wins, why
├── outputs/
│   ├── claude_demo/            # 5 example outputs, generated immediately
│   └── groq/                    # generated when you run run_comparison.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup & run
```bash
pip install -r requirements.txt
cp .env.example .env       # paste your GROQ_API_KEY in
python run_comparison.py
```
This produces 5 files in `outputs/groq/`, one per technique, each
containing the exact prompt used and the model's output — read them
side by side, then compare against `comparison_note.md`.

## The task
> Write an email to a client informing them their order is delayed by
> one week, apologizing and offering a 10% discount on their next
> purchase.

## The 5 techniques (see `prompts.py` for exact wording)
1. **Zero-shot** — the bare instruction, no examples, no persona, no format
2. **Few-shot** — two example emails provided, then asked to match that style
3. **Role-based** — LLM is given a persona ("senior customer experience manager...")
4. **Step-by-step** — instruction broken into an explicit ordered checklist
5. **Format-specific** — exact structural constraints (subject length, paragraph count, word limit)

## Result summary
See `comparison_note.md` for the full analysis. Short version: there's
no universal winner — role-based produced the most human, send-as-is
output for *this* task, step-by-step guaranteed completeness, and
format-specific guaranteed reusability in a fixed template. Which one
"wins" depends on what you're optimizing for.
