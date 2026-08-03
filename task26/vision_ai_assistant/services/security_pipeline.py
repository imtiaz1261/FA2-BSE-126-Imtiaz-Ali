"""Security pipeline orchestration for guarded chat flow."""

from __future__ import annotations

from guardrails.input_guardrail import InputGuardrail
from guardrails.output_guardrail import OutputGuardrail
from models.security_models import GuardrailDecision, SecurityAction
from services.llm_service import LLMService


class SecurityPipeline:
    """Apply input/output guardrails around LLM inference."""

    def __init__(
        self,
        input_guardrail: InputGuardrail,
        output_guardrail: OutputGuardrail,
        llm_service: LLMService,
    ) -> None:
        self.input_guardrail = input_guardrail
        self.output_guardrail = output_guardrail
        self.llm_service = llm_service

    async def run(self, user_text: str) -> tuple[str, GuardrailDecision]:
        """Run secure assistant flow for a single user message."""
        input_decision = self.input_guardrail.validate(user_text)
        if input_decision.action == SecurityAction.BLOCK:
            return input_decision.user_message, input_decision

        generated = await self.llm_service.generate_response(user_text)
        output_decision = self.output_guardrail.validate(generated)
        if output_decision.action == SecurityAction.REPLACE:
            return output_decision.user_message, output_decision

        return generated, output_decision
