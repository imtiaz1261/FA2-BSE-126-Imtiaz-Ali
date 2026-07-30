# RAG Chatbot Evaluation Pipeline (RAGAS)

A production-ready, modular pipeline for evaluating a RAG chatbot's answer
quality: Faithfulness, Answer Relevancy, Context Precision, Context Recall,
and Answer Correctness — with a 20-question evaluation dataset, automated
reporting (CSV/JSON/Markdown/PDF), and charts.

See `docs/ARCHITECTURE.md` for design details.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in OPENAI_API_KEY if using --backend openai

# Zero-API-key demo run (TF-IDF retrieval + heuristic metrics):
python main.py --backend offline

# Production run (real RAGAS scoring, requires OPENAI_API_KEY in .env):
python main.py --backend openai
```

Reports land in `reports/output/`:
- `evaluation_results.csv`
- `evaluation_results.json`
- `evaluation_report.md`
- `evaluation_report.pdf`
- `metric_averages.png`, `category_breakdown.png`

## Run the tests

```bash
pytest
```

`tests/test_dataset.py` requires the full `requirements.txt` (Pydantic) to
be installed. `tests/test_aggregator.py`, `tests/test_heuristic_metrics.py`,
and `tests/test_retriever.py` only need pandas/scikit-learn and run in any
environment.

## Project layout

```
config/          Pydantic settings (env-var driven)
dataset/         20-question evaluation dataset + schema + loader
rag_pipeline/    RAG chatbot under test (retriever + answer generator)
evaluator/       Orchestrates chatbot runs + RAGAS/heuristic scoring
metrics/         Metric computation + aggregation
reports/         CSV/JSON/Markdown/PDF report generation
visualizations/  Matplotlib charts
utils/           Shared logger
tests/           Pytest unit tests
docs/            Architecture documentation
main.py          CLI entry point
```

## Extending to your real chatbot

Replace `rag_pipeline/knowledge_base.py` and the OpenAI branches in
`rag_pipeline/retriever.py` / `rag_pipeline/chatbot.py` with calls into your
actual document store and chatbot API. Everything downstream (evaluator,
metrics, reports, charts) works unchanged since it only depends on
`(question, generated_answer, retrieved_context, ground_truth)`.
.\venv\Scripts\streamlit.exe run streamlit_ui/app.py
