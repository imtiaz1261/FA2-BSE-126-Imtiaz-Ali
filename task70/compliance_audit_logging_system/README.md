# Compliance-Ready LLM Audit Logging System

Python 3.11 reference implementation.

Features: SHA-256 hash chaining, timestamp/user/prompt/response/tool/document/token logging,
PII masking before persistence, user/date search, Streamlit dashboard, chain verification,
90-day retention/archive, 25 seeded interactions and tests.

This is a reference/demo implementation, not a certification of HIPAA, PCI DSS, GDPR,
FINRA, SOC 2 or other regulations. Production requires compliance/legal review,
authentication, encryption, immutable/WORM storage, key management, access control,
monitoring and backups.

## Windows setup
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

## Seed 25 records
python -m app.seed

## Verify
python -m app.verify

## API
uvicorn app.api:app --reload --port 8000
Open http://127.0.0.1:8000/docs

## Dashboard
streamlit run app/dashboard.py
Open http://localhost:8501

## Search
GET /audit/search?user_id=user-1001&start=2026-08-01&end=2026-08-31

## Retention
python -m app.retention --days 90 --action archive
