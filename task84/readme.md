# Task 84 — AI Token & Cost Monitoring Logger

A custom LangChain callback handler that monitors LLM usage by capturing token consumption and calculating the estimated cost of each model request. The results are automatically stored in a text log with timestamps for easy tracking and analysis.

## What it demonstrates

* Creating a custom callback handler by extending `BaseCallbackHandler`.
* Using `on_llm_end` to capture information after an LLM request completes.
* Extracting prompt, completion, and total token usage from the model response.
* Calculating estimated API costs using configurable per-model pricing.
* Recording usage information with timestamps in a persistent log file.
* Monitoring multiple LLM calls using the same callback handler.

## Files

| File               | Purpose                                        |
| ------------------ | ---------------------------------------------- |
| `usage_monitor.py` | Main application script                        |
| `requirements.txt` | Required Python dependencies                   |
| `secret_key.py`    | Stores the API key locally                     |
| `.gitignore`       | Excludes sensitive and generated files         |
| `usage_log.txt`    | Automatically generated usage and cost history |

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure the API key

Add your API key to `secret_key.py`.

For Groq:

https://console.groq.com/keys

## Usage

### Command-Line Mode

```powershell
python usage_monitor.py --question "Explain artificial intelligence in simple words."
```

### Interactive Mode

```powershell
python usage_monitor.py
```

The application will prompt you to enter a question.

After each successful LLM request, a new usage record is added to `usage_log.txt`.

## Example Log

```text
[2026-08-26 14:32:07] model=llama-3.3-70b-versatile prompt_tokens=18 completion_tokens=42 total_tokens=60 cost=$0.000000
```

## Why Token Monitoring Matters

Tracking token usage helps developers understand how much data their applications send to and receive from LLMs. It is especially useful for monitoring application performance, estimating API expenses, optimizing prompts, and controlling usage in production systems.

## Extending the Project

* Add additional models and their current pricing to the pricing configuration.
* Track usage across multiple LLM calls in a LangChain chain or agent.
* Store usage data in a database instead of a text file.
* Add daily, weekly, or monthly usage summaries.
* Extend the callback handler to record prompts, responses, latency, and errors.

**Task 84 demonstrates how LangChain callbacks can be used to build practical LLM observability and usage-monitoring features.**
