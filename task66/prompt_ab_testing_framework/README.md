# Prompt A/B Testing Framework

Python + Streamlit framework for randomized A/B testing of two prompts.

Features:
- Random 50/50 assignment
- Prompt A and B
- Groq LLM integration
- Thumbs up/down and task completion tracking
- Response length and optional quality score
- SQLite persistence
- Streamlit dashboard
- Chi-square significance test
- 95% confidence interval for B-A
- 120 synthetic demo interactions
- Pytest tests

## Setup
Python 3.11+ recommended.

    pip install -r requirements.txt

Create `.env`:

    GROQ_API_KEY=your_key
    GROQ_MODEL=llama-3.1-8b-instant

Run:

    streamlit run app/streamlit_app.py

Generate demo data:

    python app/generate_demo_data.py --n 120

Run tests:

    pytest -q

IMPORTANT: the included 120 interactions are synthetic demo data, not real-user evidence.
