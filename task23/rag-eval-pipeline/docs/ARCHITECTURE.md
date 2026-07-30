# Architecture

## Overview

This pipeline evaluates a RAG chatbot's answer quality using RAGAS-style
metrics. It is split into independent layers so each can be tested, replaced,
or extended without touching the others.

```
dataset/        -> evaluation questions + Pydantic schema + JSON I/O
rag_pipeline/    -> the chatbot under test (retriever + answer generator)
evaluator/       -> orchestrates: run chatbot over dataset, then score answers
metrics/         -> scoring logic (RAGAS metrics or offline heuristic fallback)
reports/         -> turns scored results into CSV / JSON / Markdown / PDF
visualizations/  -> matplotlib charts embedded in the reports
config/          -> Pydantic Settings, single source of truth for all env vars
utils/           -> shared logger factory
tests/           -> pytest unit tests for schema, metrics, aggregator, retriever
main.py          -> CLI entry point wiring all layers together
```

## Two execution backends

Every layer that would normally require an API key (retriever, chatbot,
evaluator) supports **two backends behind the same interface**:

| Layer | Production backend | Offline/dev backend |
|---|---|---|
| Retriever | `openai_faiss` — FAISS + OpenAIEmbeddings | `tfidf` — scikit-learn TF-IDF cosine similarity |
| Chatbot | `openai` — ChatOpenAI with a grounded RAG prompt | `extractive` — sentence-overlap extraction, no LLM call |
| Evaluator | Real RAGAS metrics (LLM-judged) | Heuristic lexical-overlap approximations |

Run with `python main.py --backend openai` for real evaluation results, or
`python main.py --backend offline` (the default) to exercise the whole
pipeline with zero API keys and zero network calls — useful for CI, local
development, and demos.

**The offline backend is not a substitute for RAGAS.** RAGAS's real metrics
use an LLM to reason about faithfulness and relevancy semantically; the
heuristic fallback only measures lexical token overlap. Treat offline scores
as a smoke test that the pipeline runs, not as a judgment of chatbot quality.

## Why Pydantic for the dataset schema

`EvalRecord` validates every question at load time — a malformed dataset
file (missing field, wrong type) fails immediately with a clear error
instead of crashing deep inside a 20-question evaluation run or, worse,
silently producing a garbage score.

## Why a pluggable metrics aggregator

`MetricsAggregator` only operates on a plain DataFrame of `{metric: score}`
columns. It doesn't know or care whether those scores came from RAGAS or the
heuristic fallback — this is what let us build and test the full
reporting/visualization pipeline without ever calling an LLM.

## Extending this project

- **Add a metric**: implement it in `metrics/heuristic_metrics.py` (offline)
  and add the corresponding RAGAS metric import in
  `evaluator/ragas_evaluator.py::_score_with_ragas`.
- **Point at your real chatbot**: replace `rag_pipeline/knowledge_base.py`
  and `rag_pipeline/retriever.py` with calls into your actual document
  store, and replace `RAGChatbot._generate_openai` with a call into your
  actual chatbot's API.
- **Add the Streamlit dashboard (bonus)**: read `reports/output/evaluation_results.json`
  and render it with `st.dataframe` / `st.bar_chart` — the JSON already
  contains `overall_score`, `metric_averages`, `category_breakdown`, and
  `per_question_results` in a dashboard-ready shape.
