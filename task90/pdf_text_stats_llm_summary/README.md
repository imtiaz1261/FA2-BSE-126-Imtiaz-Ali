# PDF Text Analyzer + LLM 3-Line Summary

Streamlit app that extracts PDF text with PyMuPDF, calculates total words/characters/pages locally, and uses Groq for an exactly 3-line summary.

## Install (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```
Set `GROQ_API_KEY` and optionally `GROQ_MODEL` in `.env`.

## Run
```powershell
streamlit run app.py
```

## Test
```powershell
pytest -q
```

## Structure
```text
pdf_text_stats_llm_summary/
├── app.py
├── pdf_utils.py
├── llm_summary.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── tests/
    └── test_pdf_utils.py
```

Scanned/image-only PDFs may require OCR because normal PDF text extraction cannot read embedded page images.
