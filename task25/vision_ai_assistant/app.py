"""
app.py
======
Vision AI Assistant — Main Streamlit Application Entry Point

Production-ready ChatGPT-style multimodal document understanding system.
Run with:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import streamlit as st

# ── Add project root to sys.path so relative imports work correctly ──────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Project imports ──────────────────────────────────────────────────────────
from config.logging_config import setup_logging
from config.constants import (
    PROMPT_CARDS, THEME, DOCUMENT_TYPE_ICONS,
    DOCUMENT_TYPE_LABELS, EXPORT_FORMAT_LABELS, APP_ICON,
    SUPPORTED_IMAGE_FORMATS,
)
from config.settings import get_settings

from models.chat import ChatSession, ChatMessage, ConversationHistory
from models.document import UploadedImage, DocumentAnalysis, ExtractionResult

from services.vision_service import VisionService, process_uploaded_file
from services.llm_service import (
    LLMService, create_llm_service, get_openai_client, validate_api_key,
)
from services.json_extractor import (
    process_extraction_response, format_json_for_display,
)

from utils.helpers import (
    SSKey, ss_init, ss_get, ss_set,
    truncate, time_ago, document_type_badge, confidence_badge,
)
from utils.image_utils import make_display_image, get_image_info
from utils.export_utils import export
from utils.css_styles import get_main_css, get_loading_css

from frontend.components.sidebar import render_sidebar

# ── Logging ──────────────────────────────────────────────────────────────────
setup_logging()
from loguru import logger

# ── Page config (MUST be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Vision AI Assistant",
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Vision AI Assistant — Multimodal Document Understanding",
    },
)


# ═══════════════════════════════════════════════════════════════════════════════
# Session State Initialisation
# ═══════════════════════════════════════════════════════════════════════════════

def init_session_state() -> None:
    """Initialise all session state keys with defaults on first load."""
    ss_init(SSKey.CURRENT_SESSION,  ChatSession())
    ss_init(SSKey.CURRENT_IMAGE,    None)
    ss_init(SSKey.CURRENT_ANALYSIS, None)
    ss_init(SSKey.CURRENT_RESULT,   None)
    ss_init(SSKey.HISTORY,          ConversationHistory())
    ss_init(SSKey.ALL_SESSIONS,     {})
    ss_init(SSKey.IS_PROCESSING,    False)
    ss_init(SSKey.IS_STREAMING,     False)
    ss_init(SSKey.LAST_ERROR,       None)
    ss_init(SSKey.UPLOAD_KEY,       0)
    ss_init(SSKey.PENDING_PROMPT,   None)
    ss_init("llm_service",          None)
    ss_init("vision_service",       None)
    ss_init(SSKey.SELECTED_MODEL,   get_settings().default_model)
    ss_init(SSKey.API_KEY_VALID,    get_settings().api_key_configured)


# ═══════════════════════════════════════════════════════════════════════════════
# Service Factories
# ═══════════════════════════════════════════════════════════════════════════════

def get_llm_service() -> Optional[LLMService]:
    """Return (or create) the LLMService singleton stored in session state."""
    svc = ss_get("llm_service")
    if svc is not None:
        return svc
    model = ss_get(SSKey.SELECTED_MODEL, get_settings().default_model)
    svc = create_llm_service(model=model)
    if svc:
        ss_set("llm_service", svc)
    return svc


def get_vision_service() -> Optional[VisionService]:
    """Return (or create) the VisionService singleton stored in session state."""
    svc = ss_get("vision_service")
    if svc is not None:
        return svc
    try:
        settings = get_settings()
        if not settings.api_key_configured:
            return None
        svc = VisionService()   # resolves client internally from settings
        ss_set("vision_service", svc)
        return svc
    except Exception as exc:
        logger.warning("VisionService unavailable: {}", exc)
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Image Upload Handler
# ═══════════════════════════════════════════════════════════════════════════════

def handle_image_upload(uploaded_file) -> None:
    """
    Process a newly uploaded image file:
      1. Validate & build UploadedImage
      2. Run VLM classification + initial analysis
      3. Store results in session state
      4. Add AI's initial analysis as the first chat message
    """
    if uploaded_file is None:
        return

    # Avoid re-processing the same file
    current_image: Optional[UploadedImage] = ss_get(SSKey.CURRENT_IMAGE)
    if current_image and current_image.metadata.filename == uploaded_file.name:
        return

    with st.spinner("🔍 Processing image…"):
        # --- Step 1: Process the uploaded bytes ---
        file_bytes = uploaded_file.read()
        image, error = process_uploaded_file(file_bytes, uploaded_file.name)

        if error:
            ss_set(SSKey.LAST_ERROR, error)
            st.error(f"❌ {error}")
            return

        ss_set(SSKey.CURRENT_IMAGE, image)
        ss_set(SSKey.LAST_ERROR, None)
        logger.info("Image uploaded: {}", uploaded_file.name)

    # --- Step 2: Run VLM analysis ---
    vision_svc = get_vision_service()
    session: ChatSession = ss_get(SSKey.CURRENT_SESSION, ChatSession())

    if vision_svc is None:
        # No API key — still show image, just no AI analysis
        session.image_filename = uploaded_file.name
        _add_no_api_message(session, uploaded_file.name)
        ss_set(SSKey.CURRENT_SESSION, session)
        return

    with st.spinner("🤖 Analysing document with Vision AI…"):
        try:
            analysis, summary = vision_svc.full_pipeline(
                image=image,
                session_id=session.id,
            )
            ss_set(SSKey.CURRENT_ANALYSIS, analysis)

            # Update session metadata
            session.image_filename = uploaded_file.name
            session.document_type  = analysis.document_type

            # Add user's upload as a message
            session.add_user_message(
                content=f"📎 Uploaded: **{uploaded_file.name}**",
                image_attached=True,
                image_filename=uploaded_file.name,
            )

            # Add AI's initial analysis as a message
            if summary:
                session.add_assistant_message(
                    content=summary,
                    metadata={
                        "model":      analysis.model_used,
                        "tokens_used": analysis.tokens_used,
                        "latency_ms": analysis.latency_ms,
                        "document_type": analysis.document_type,
                    },
                )

            ss_set(SSKey.CURRENT_SESSION, session)
            logger.info(
                "Analysis complete: type={} conf={:.0%}",
                analysis.document_type,
                analysis.document_type_confidence,
            )

        except Exception as exc:
            logger.error("Analysis pipeline failed: {}", exc)
            st.error(f"⚠️ Analysis failed: {exc}")
            session.add_assistant_message(
                content=f"⚠️ I couldn't analyse this image: {exc}\n\n"
                        f"Please check your API key in the Settings panel, "
                        f"or try uploading a different image.",
            )
            ss_set(SSKey.CURRENT_SESSION, session)


def _add_no_api_message(session: ChatSession, filename: str) -> None:
    """Add a message explaining the API key is missing."""
    session.add_user_message(
        content=f"📎 Uploaded: **{filename}**",
        image_attached=True,
        image_filename=filename,
    )
    session.add_assistant_message(
        content=(
            "👋 Image uploaded successfully! I can see your file.\n\n"
            "⚠️ **API Key Required** — To analyse this image with AI, "
            "please add your OpenAI API key in the **⚙️ Settings** panel "
            "in the sidebar.\n\n"
            "You can get a free key at: https://platform.openai.com/api-keys"
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Chat Handler
# ═══════════════════════════════════════════════════════════════════════════════

def handle_chat_message(user_input: str) -> None:
    """
    Process a user's chat message:
      1. Add user message to session
      2. Stream the AI response token-by-token
      3. Append the complete response to session
    """
    if not user_input.strip():
        return

    image: Optional[UploadedImage] = ss_get(SSKey.CURRENT_IMAGE)
    session: ChatSession = ss_get(SSKey.CURRENT_SESSION, ChatSession())
    llm_svc = get_llm_service()

    # Add user message
    session.add_user_message(content=user_input)
    ss_set(SSKey.CURRENT_SESSION, session)

    if image is None:
        session.add_assistant_message(
            content="⚠️ Please upload an image first before asking questions."
        )
        ss_set(SSKey.CURRENT_SESSION, session)
        return

    if llm_svc is None:
        session.add_assistant_message(
            content="⚠️ OpenAI API key not configured. Please add your key in the Settings panel."
        )
        ss_set(SSKey.CURRENT_SESSION, session)
        return

    # Stream the response
    ss_set(SSKey.IS_STREAMING, True)
    full_response = ""

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        placeholder.markdown("▌")

        try:
            for chunk in llm_svc.stream_answer(image, user_input, session):
                full_response += chunk
                placeholder.markdown(full_response + "▌")

            # Final render without cursor
            placeholder.markdown(full_response)

        except Exception as exc:
            full_response = f"❌ Error: {exc}"
            placeholder.markdown(full_response)

    # Save to session
    session.add_assistant_message(content=full_response)
    ss_set(SSKey.CURRENT_SESSION, session)
    ss_set(SSKey.IS_STREAMING, False)


# ═══════════════════════════════════════════════════════════════════════════════
# UI Components
# ═══════════════════════════════════════════════════════════════════════════════

def render_image_panel() -> None:
    """Render the left panel: image preview + metadata."""
    image: Optional[UploadedImage] = ss_get(SSKey.CURRENT_IMAGE)
    analysis: Optional[DocumentAnalysis] = ss_get(SSKey.CURRENT_ANALYSIS)
    upload_key: int = ss_get(SSKey.UPLOAD_KEY, 0)

    st.markdown(
        '<div style="font-size:0.85rem; font-weight:600; '
        f'color:{THEME["text_secondary"]}; margin-bottom:8px;">'
        '📁 IMAGE VIEWER</div>',
        unsafe_allow_html=True,
    )

    # ── File uploader ─────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=SUPPORTED_IMAGE_FORMATS,
        help="Upload a PNG, JPG, JPEG, or WEBP image",
        label_visibility="collapsed",
        key=f"file_uploader_{upload_key}",
    )

    if uploaded_file is not None:
        handle_image_upload(uploaded_file)
        image = ss_get(SSKey.CURRENT_IMAGE)   # refresh after upload
        analysis = ss_get(SSKey.CURRENT_ANALYSIS)

    # ── Image preview ─────────────────────────────────────────────────────
    if image is not None:
        # Re-decode to display
        try:
            import base64
            raw = base64.b64decode(image.base64_data)
            display_bytes = make_display_image(raw, max_width=700, max_height=560)
            st.image(display_bytes, use_container_width=True)
        except Exception as exc:
            st.warning(f"Preview error: {exc}")

        # ── Document type badge ───────────────────────────────────────────
        if analysis:
            doc_type = analysis.document_type
            icon     = DOCUMENT_TYPE_ICONS.get(doc_type, "📄")
            label    = DOCUMENT_TYPE_LABELS.get(doc_type, "Unknown")
            conf_pct = int(analysis.document_type_confidence * 100)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(
                    document_type_badge(doc_type),
                    unsafe_allow_html=True,
                )
            with col_b:
                st.markdown(
                    confidence_badge(analysis.document_type_confidence),
                    unsafe_allow_html=True,
                )

        # ── Image metadata ────────────────────────────────────────────────
        with st.expander("📐 Image Details", expanded=False):
            info = get_image_info(
                base64.b64decode(image.base64_data),
                image.metadata.filename,
            )
            for k, v in info.items():
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:0.78rem;padding:3px 0;">'
                    f'<span style="color:{THEME["text_muted"]}">{k}</span>'
                    f'<span style="color:{THEME["text_secondary"]}">{v}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── Export section ────────────────────────────────────────────────
        result: Optional[ExtractionResult] = ss_get(SSKey.CURRENT_RESULT)
        session: ChatSession = ss_get(SSKey.CURRENT_SESSION, ChatSession())

        if analysis:
            st.markdown("---")
            st.markdown(
                f'<div style="font-size:0.78rem; color:{THEME["text_muted"]}; '
                f'margin-bottom:6px;">📥 EXPORT</div>',
                unsafe_allow_html=True,
            )
            export_fmt = st.selectbox(
                "Format",
                options=list(EXPORT_FORMAT_LABELS.keys()),
                format_func=lambda k: EXPORT_FORMAT_LABELS[k],
                label_visibility="collapsed",
                key="export_format_select",
            )

            if st.button(
                "⬇️ Download",
                use_container_width=True,
                key="btn_export",
                help=f"Export as {export_fmt.upper()}",
            ):
                _do_export(export_fmt, image, analysis, session)

    else:
        # Empty state — drag-and-drop prompt
        st.markdown(
            f"""
            <div style="border: 2px dashed {THEME['border']}; border-radius:16px;
                        padding: 3rem 1.5rem; text-align:center; 
                        background:{THEME['surface']}; margin-top:1rem;">
                <div style="font-size:3rem; margin-bottom:12px;">📸</div>
                <div style="font-size:1rem; font-weight:600; 
                            color:{THEME['text_primary']}; margin-bottom:6px;">
                    Drop your document here
                </div>
                <div style="font-size:0.82rem; color:{THEME['text_muted']};">
                    PNG · JPG · JPEG · WEBP · Max 20 MB
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _do_export(fmt: str, image: UploadedImage,
               analysis: DocumentAnalysis, session: ChatSession) -> None:
    """Build and trigger a download for the selected export format."""
    try:
        # Build a minimal ExtractionResult for export
        result = ExtractionResult(
            session_id=session.id,
            image=image,
            analysis=analysis,
        )
        data, filename, mime = export(fmt, result, session)
        st.download_button(
            label=f"📄 {filename}",
            data=data,
            file_name=filename,
            mime=mime,
            key=f"download_{fmt}_{int(time.time())}",
        )
    except Exception as exc:
        st.error(f"Export failed: {exc}")
        logger.error("Export error: {}", exc)


def render_chat_panel() -> None:
    """Render the right panel: chat messages + input."""
    session: ChatSession = ss_get(SSKey.CURRENT_SESSION, ChatSession())
    image: Optional[UploadedImage] = ss_get(SSKey.CURRENT_IMAGE)
    analysis: Optional[DocumentAnalysis] = ss_get(SSKey.CURRENT_ANALYSIS)

    # ── Header ────────────────────────────────────────────────────────────
    col_title, col_regen = st.columns([5, 1])
    with col_title:
        st.markdown(
            f'<div style="font-size:0.85rem; font-weight:600; '
            f'color:{THEME["text_secondary"]}; margin-bottom:8px;">'
            f'💬 AI CHAT</div>',
            unsafe_allow_html=True,
        )
    with col_regen:
        if (
            image is not None
            and session.messages
            and session.messages[-1].is_assistant
        ):
            if st.button("🔄", help="Regenerate last response", key="btn_regen"):
                _handle_regenerate()

    # ── Welcome / empty state ─────────────────────────────────────────────
    visible_messages = [m for m in session.messages if m.role != "system"]

    if not visible_messages:
        _render_welcome(image)
    else:
        # ── Chat history ──────────────────────────────────────────────────
        for msg in visible_messages:
            _render_message(msg)

    # ── Suggested questions (post-upload) ─────────────────────────────────
    if image is not None and analysis is not None and len(visible_messages) <= 2:
        _render_suggestions(analysis.document_type)

    # ── Chat input ────────────────────────────────────────────────────────
    _render_chat_input(image)


def _render_welcome(image: Optional[UploadedImage]) -> None:
    """Render the welcome state (no messages yet)."""
    st.markdown(
        f"""
        <div class="welcome-container">
            <div class="welcome-logo">🔍</div>
            <div class="welcome-title">Vision AI Assistant</div>
            <div class="welcome-subtitle">
                Upload a document image to get started.<br>
                I can analyse invoices, receipts, diagrams, handwritten notes, 
                business cards, bank statements, and much more.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if image is None:
        # Prompt cards
        st.markdown("---")
        st.markdown(
            f'<div style="text-align:center; font-size:0.85rem; '
            f'color:{THEME["text_muted"]}; margin-bottom:12px;">'
            f'Try one of these after uploading an image</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(4)
        for i, card in enumerate(PROMPT_CARDS[:8]):
            with cols[i % 4]:
                if st.button(
                    f"{card['icon']} {card['title']}",
                    use_container_width=True,
                    key=f"prompt_card_{i}",
                    help=card["prompt"],
                ):
                    ss_set(SSKey.PENDING_PROMPT, card["prompt"])
                    st.rerun()


def _render_message(msg: ChatMessage) -> None:
    """Render a single chat message in ChatGPT style."""
    if msg.is_user:
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg.content)
            st.caption(msg.formatted_time)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(msg.content)
            # Action buttons
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button(
                    "📋",
                    key=f"copy_{msg.id}",
                    help="Copy to clipboard",
                ):
                    st.code(msg.content, language=None)
            with col2:
                st.caption(msg.formatted_time)


def _render_suggestions(doc_type: str) -> None:
    """Show clickable suggested questions based on detected document type."""
    from prompts.analysis_prompts import get_suggestions_for_document
    suggestions = get_suggestions_for_document(doc_type)

    if not suggestions:
        return

    st.markdown("---")
    st.markdown(
        f'<div style="font-size:0.78rem; color:{THEME["text_muted"]}; '
        f'margin-bottom:8px;">💡 Suggested questions</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(min(len(suggestions), 3))
    for i, suggestion in enumerate(suggestions[:3]):
        with cols[i % 3]:
            if st.button(
                truncate(suggestion, 50),
                key=f"suggestion_{i}_{doc_type}",
                use_container_width=True,
                help=suggestion,
            ):
                ss_set(SSKey.PENDING_PROMPT, suggestion)
                st.rerun()


def _render_chat_input(image: Optional[UploadedImage]) -> None:
    """Render the chat input bar at the bottom."""
    # Handle pending prompt from card/suggestion clicks
    pending = ss_get(SSKey.PENDING_PROMPT)
    if pending:
        ss_set(SSKey.PENDING_PROMPT, None)
        handle_chat_message(pending)
        st.rerun()

    placeholder_text = (
        "Ask a question about the document…"
        if image is not None
        else "Upload an image first, then ask questions here…"
    )

    user_input = st.chat_input(
        placeholder=placeholder_text,
        key="chat_input_main",
        disabled=ss_get(SSKey.IS_STREAMING, False),
    )

    if user_input:
        handle_chat_message(user_input)
        st.rerun()


def _handle_regenerate() -> None:
    """Regenerate the last AI response."""
    image: Optional[UploadedImage] = ss_get(SSKey.CURRENT_IMAGE)
    session: ChatSession = ss_get(SSKey.CURRENT_SESSION, ChatSession())
    llm_svc = get_llm_service()

    if not image or not llm_svc:
        return

    # Remove last assistant message
    if session.messages and session.messages[-1].is_assistant:
        session.messages.pop()
        ss_set(SSKey.CURRENT_SESSION, session)

    # Re-run last user question
    last_user = None
    for msg in reversed(session.messages):
        if msg.is_user:
            last_user = msg.content
            break

    if last_user:
        handle_chat_message(last_user)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# No-API Key Banner
# ═══════════════════════════════════════════════════════════════════════════════

def render_api_key_banner() -> None:
    """Show a warning banner if no API key is configured."""
    settings = get_settings()
    api_valid = ss_get(SSKey.API_KEY_VALID, settings.api_key_configured)

    if not api_valid:
        st.warning(
            "⚠️ **No API key configured.** "
            "Open **⚙️ Settings** in the sidebar, enter your **Groq** key (`gsk_...`) "
            "and click **Apply Key**. "
            "Get a free key at: https://console.groq.com/keys",
            icon="🔑",
        )
    else:
        provider = settings.active_provider.upper()
        model = settings.default_model.split("/")[-1]  # short name
        st.success(f"✅ Connected via **{provider}** · Model: `{model}`", icon="🤖")


# ═══════════════════════════════════════════════════════════════════════════════
# Main Layout
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Main application entry point."""

    # ── Init ─────────────────────────────────────────────────────────────
    init_session_state()

    # ── CSS injection ─────────────────────────────────────────────────────
    st.markdown(get_main_css(), unsafe_allow_html=True)
    st.markdown(get_loading_css(), unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────
    render_sidebar()

    # ── Main header ───────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; 
                    padding-bottom:0.5rem; border-bottom:1px solid {THEME['border']}; 
                    margin-bottom:1rem;">
            <span style="font-size:1.8rem;">🔍</span>
            <div>
                <div style="font-size:1.3rem; font-weight:700; 
                            color:{THEME['text_primary']}; line-height:1.2;">
                    Vision AI Assistant
                </div>
                <div style="font-size:0.78rem; color:{THEME['text_muted']};">
                    Multimodal Document Understanding · Powered by GPT-4o Vision
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── API Key warning ───────────────────────────────────────────────────
    render_api_key_banner()

    # ── Two-column layout ─────────────────────────────────────────────────
    left_col, right_col = st.columns([2, 3], gap="medium")

    with left_col:
        render_image_panel()

    with right_col:
        render_chat_panel()


# ═══════════════════════════════════════════════════════════════════════════════
# Entry
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
