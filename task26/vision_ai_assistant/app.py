"""Streamlit entrypoint for the Secure AI Assistant application."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from config.settings import get_settings
from guardrails.input_guardrail import InputGuardrail
from guardrails.output_guardrail import OutputGuardrail
from services.llm_service import LLMService
from services.security_pipeline import SecurityPipeline
from utils.logger import configure_logging, get_logger

import streamlit as st


configure_logging()
logger = get_logger(__name__)


def initialize_session_state() -> None:
    """Initialize required Streamlit session variables."""
    defaults = {
        "chat_history": [],
        "active_model": None,
        "theme": "Light",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def start_new_chat() -> None:
    """Reset chat history for a fresh conversation."""
    st.session_state["chat_history"] = []


def clear_chat() -> None:
    """Clear existing chat and keep current app preferences."""
    st.session_state["chat_history"] = []


def build_security_pipeline() -> SecurityPipeline:
    """Build the guarded chat pipeline from current application settings."""
    settings = get_settings()
    input_guardrail = InputGuardrail(settings)
    output_guardrail = OutputGuardrail(settings)
    llm_service = LLMService(settings)
    return SecurityPipeline(input_guardrail, output_guardrail, llm_service)


def main() -> None:
    """Run the Streamlit application."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.logs_dir)
    initialize_session_state()

    st.set_page_config(
        page_title=settings.app_name,
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title(settings.app_name)
    st.caption("Security-first ChatGPT-style assistant with input and output guardrails")

    with st.sidebar:
        st.subheader("Secure AI Assistant")
        if st.button("New Chat", use_container_width=True):
            start_new_chat()
        if st.button("Clear Chat", use_container_width=True):
            clear_chat()

        st.divider()
        st.markdown("### Settings")
        model_options = [settings.openai_chat_model]
        if settings.fallback_local_model:
            model_options.append(settings.fallback_local_model)
        st.session_state["active_model"] = st.selectbox(
            "Model",
            options=model_options,
            index=0,
        )
        st.session_state["theme"] = st.radio("Theme", options=["Light", "Dark"], horizontal=True)

        st.divider()
        st.markdown("### About")
        st.caption("Step 1 foundation: secure architecture, config, logging, and guardrail scaffolding.")

    st.info("Step 1 complete: secure foundation is ready. Step 2 will implement full chat workflow and live guardrail orchestration.")

    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            st.caption(message["timestamp"])

    placeholder = "Ask anything..."
    user_prompt = st.chat_input(placeholder)
    if user_prompt:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        st.session_state["chat_history"].append(
            {"role": "user", "content": user_prompt, "timestamp": timestamp}
        )
        with st.chat_message("user"):
            st.markdown(user_prompt)
            st.caption(timestamp)

        security_pipeline = build_security_pipeline()
        assistant_message, pipeline_decision = asyncio.run(security_pipeline.run(user_prompt))

        if pipeline_decision.is_safe:
            logger.info("Accepted user request for processing: %s", user_prompt)
        else:
            logger.warning(
                "Blocked user request category=%s reason=%s",
                pipeline_decision.category,
                pipeline_decision.reason,
            )

        st.session_state["chat_history"].append(
            {"role": "assistant", "content": assistant_message, "timestamp": timestamp}
        )
        with st.chat_message("assistant"):
            if pipeline_decision.is_safe:
                streamed_response = st.write_stream(
                    security_pipeline.llm_service.stream_chunks(assistant_message)
                )
                st.session_state["chat_history"][-1]["content"] = streamed_response
            else:
                st.markdown(assistant_message)
            st.caption(timestamp)

    logger.info("Application started with environment: %s", settings.environment)


if __name__ == "__main__":
    main()
