# Architecture Overview

This project follows a modular architecture:

- app.py: Streamlit entrypoint and high-level orchestration for secure chat flow.
- frontend/: Chat-oriented UI composition and styling helpers.
- components/: Reusable UI blocks and controls.
- guardrails/: Input and output security validation modules.
- services/: LLM integration and orchestration logic.
- models/: Typed schemas for message events and guardrail decisions.
- utils/: Shared helpers including structured logging.
- config/: Environment and runtime configuration.
- logs/: Runtime logs for auditability.
- tests/: Unit and integration tests for security and behavior.

Security pipeline target flow:

1. User submits query in Streamlit chat.
2. Input guardrail validates request.
3. Unsafe request is blocked with a professional warning.
4. Safe request is sent to the LLM.
5. Output guardrail validates generated response.
6. Unsafe output is replaced with a safe fallback response.

Future steps will keep presentation, domain logic, and integration boundaries clearly separated.
