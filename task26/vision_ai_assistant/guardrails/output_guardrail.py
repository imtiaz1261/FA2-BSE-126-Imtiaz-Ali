"""Output guardrail for model response safety validation."""

from __future__ import annotations

from config.settings import AppSettings
from models.security_models import GuardrailDecision, RiskCategory, SecurityAction


UNSAFE_OUTPUT_PATTERNS: dict[RiskCategory, tuple[str, ...]] = {
    RiskCategory.CONFIDENTIAL_INFO: (
        "api_key",
        "password",
        "secret token",
    ),
    RiskCategory.SYSTEM_PROMPT_EXTRACTION: (
        "system prompt",
        "hidden instructions",
    ),
    RiskCategory.HARMFUL_CONTENT: (
        "here is how to build malware",
        "steps to exploit",
    ),
}


class OutputGuardrail:
    """Validate model output before rendering it to users."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def validate(self, assistant_text: str) -> GuardrailDecision:
        """Return a safety decision for outgoing assistant text."""
        normalized = assistant_text.lower().strip()

        if not self.settings.output_guardrail_enabled:
            return GuardrailDecision(action=SecurityAction.ALLOW, is_safe=True)

        for category, patterns in UNSAFE_OUTPUT_PATTERNS.items():
            if any(pattern in normalized for pattern in patterns):
                return GuardrailDecision(
                    action=SecurityAction.REPLACE,
                    is_safe=False,
                    category=category,
                    reason=f"Output blocked by category: {category.value}.",
                    user_message=(
                        "⚠️ Response Withheld\n\n"
                        "The generated response was blocked by safety policies. "
                        "Please rephrase your question."
                    ),
                )

        return GuardrailDecision(action=SecurityAction.ALLOW, is_safe=True)
