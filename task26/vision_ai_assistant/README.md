# Secure AI Assistant with Input and Output Guardrails

Production-ready secure AI assistant built with Streamlit, OpenAI models, and layered guardrails for malicious input and unsafe output detection.

## Step-by-Step Build Plan

This repository is intentionally built incrementally, one professional step at a time.

- Step 1: Secure project foundation (architecture, config, logging, and module scaffolding).
- Step 2: ChatGPT-style Streamlit shell and chat workflow wiring.
- Step 3: Input guardrails for prompt injection, jailbreak, and malicious content.
- Step 4: LLM service integration with token streaming.
- Step 5: Output guardrails for unsafe or confidential response filtering.
- Step 6: Session conversation history and sidebar controls.
- Step 7: Export features and operational logging.
- Step 8: Testing and hardening.
- Step 9: Deployment-ready configuration.

## Project Structure

vision_ai_assistant/
- app.py
- requirements.txt
- .env.example
- README.md
- frontend/
- pages/
- components/
- guardrails/
- services/
- prompts/
- models/
- utils/
- config/
- assets/
- exports/
- logs/
- tests/
- docs/

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your local env file:
   - Copy `.env.example` to `.env`
   - Add your API keys
4. Run Streamlit:
   ```bash
   streamlit run app.py
   ```

## Engineering Standards

- Python 3.11+
- PEP 8, type hints, and docstrings
- Modular services and testable architecture
- Environment-based configuration
- Centralized structured logging
- Security-first request/response validation

## Security Notes

- Never commit `.env`.
- Use secret management for production deployments.
- Block malicious prompts before they reach the LLM.
- Validate model responses before rendering them to users.
