"""
Jarvis-Lite — Streamlit UI (FIXED)
Supports text chat + voice I/O (microphone + TTS with proper error handling).

Run with:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import logging
import sys
import os
import io
from datetime import datetime
from typing import Optional
import traceback

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ── page config must be the very first Streamlit call ──────────────────────
st.set_page_config(
    page_title="Jarvis-Lite",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Prevent duplicated imports ──────────────────────────────────────────────
@st.cache_resource
def _load_agent():
    """Load agent with caching."""
    try:
        from app.agent.agent import IntelligentAgent
        agent = IntelligentAgent(verbose=False)
        logger.info("✅ Agent loaded successfully")
        return agent, True, None
    except Exception as e:
        logger.error(f"❌ Agent loading failed: {e}")
        logger.debug(traceback.format_exc())
        return None, False, str(e)

@st.cache_resource
def _load_tts():
    """Load TTS with caching."""
    try:
        from app.voice.text_to_speech import TextToSpeech
        tts = TextToSpeech(backend="pyttsx3", language="en")
        logger.info("✅ TTS (pyttsx3) loaded successfully")
        return tts, True, None
    except Exception as e:
        logger.warning(f"⚠️  TTS pyttsx3 failed, trying gtts: {e}")
        try:
            from app.voice.text_to_speech import TextToSpeech
            tts = TextToSpeech(backend="gtts", language="en")
            logger.info("✅ TTS (gtts) loaded successfully")
            return tts, True, None
        except Exception as e2:
            logger.error(f"❌ Both TTS backends failed: {e2}")
            return None, False, str(e2)

@st.cache_resource
def _load_sr():
    """Load speech recognizer with caching."""
    try:
        from app.voice.speech_recognition import SpeechRecognizer
        sr = SpeechRecognizer()
        logger.info("✅ Speech Recognizer loaded successfully")
        return sr, True, None
    except Exception as e:
        logger.error(f"❌ Speech Recognizer loading failed: {e}")
        logger.debug(traceback.format_exc())
        return None, False, str(e)

# Load all components
agent, AGENT_OK, _AGENT_ERR = _load_agent()
tts, TTS_OK, _TTS_ERR = _load_tts()
sr, SR_OK, _SR_ERR = _load_sr()

# ── custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global dark theme tweaks */
.stApp { background-color: #0a0e27; color: #e0e0e0; }

/* Header */
.jarvis-header {
    text-align: center;
    color: #00d9ff;
    font-size: 2.6em;
    font-family: 'Courier New', monospace;
    letter-spacing: 3px;
    text-shadow: 0 0 20px rgba(0,217,255,.6), 0 0 40px rgba(0,217,255,.3);
    margin-bottom: 4px;
}
.jarvis-sub {
    text-align: center;
    color: #888;
    font-size: 1em;
    letter-spacing: 1px;
    margin-bottom: 20px;
}

/* Chat bubbles */
.bubble-user {
    background: linear-gradient(135deg,rgba(0,217,255,.18),rgba(0,217,255,.08));
    border-left: 3px solid #00d9ff;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 6px 0 6px 40px;
    color: #00d9ff;
    font-family: 'Courier New', monospace;
}
.bubble-assistant {
    background: linear-gradient(135deg,rgba(0,255,65,.12),rgba(0,255,65,.04));
    border-left: 3px solid #00ff41;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 6px 40px 6px 0;
    color: #00ff41;
    font-family: 'Courier New', monospace;
}
.bubble-time {
    font-size: 0.72em;
    color: #555;
    margin-top: 3px;
}

/* Metric cards */
.metric-card {
    background: rgba(15,28,64,.9);
    border: 1px solid #1a3a52;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    font-family: 'Courier New', monospace;
}
.metric-label { color: #888; font-size: 0.78em; text-transform: uppercase; }
.metric-value { color: #00d9ff; font-size: 1.4em; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ── session-state init ──────────────────────────────────────────────────────
def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages: list[dict] = []
    if "agent" not in st.session_state:
        st.session_state.agent = agent
    if "tts" not in st.session_state:
        st.session_state.tts = tts
    if "sr" not in st.session_state:
        st.session_state.sr = sr
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0
    if "tts_backend" not in st.session_state:
        st.session_state.tts_backend = "pyttsx3"
    if "tts_lang" not in st.session_state:
        st.session_state.tts_lang = "en"

_init_state()


# ── helpers ─────────────────────────────────────────────────────────────────
def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _bubble(role: str, content: str, ts: str) -> None:
    css_class = "bubble-user" if role == "user" else "bubble-assistant"
    icon = "👤" if role == "user" else "🤖"
    st.markdown(
        f'<div class="{css_class}">'
        f"<strong>{icon} {'You' if role == 'user' else 'Jarvis'}</strong><br>"
        f"{content}"
        f'<div class="bubble-time">{ts}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _process(query: str) -> dict:
    """Run agent and return result dict."""
    agent_inst = st.session_state.agent
    if agent_inst is None:
        return {
            "answer": f"❌ Agent not available: {_AGENT_ERR if not AGENT_OK else 'unknown error'}",
            "tool_used": None,
            "confidence": 0.0,
            "sources": [],
        }
    try:
        result = agent_inst.process_query(query)
        logger.info(f"✅ Query processed: {query[:50]}...")
        return result
    except Exception as e:
        logger.error(f"❌ Query processing failed: {e}")
        logger.debug(traceback.format_exc())
        return {
            "answer": f"❌ Error processing query: {str(e)}",
            "tool_used": None,
            "confidence": 0.0,
            "sources": [],
        }

def _play_tts(text: str) -> None:
    """Generate TTS audio and stream it (like Siri - instant playback)."""
    tts_inst = st.session_state.tts
    if tts_inst is None:
        st.error("❌ TTS not available. Install pyttsx3 or gtts:\n\n```pip install pyttsx3 gtts```")
        return
    
    try:
        # Use streaming for fast playback
        audio_chunks = list(tts_inst.speak_to_chunks(text))
        
        if audio_chunks:
            # Combine all chunks into single audio file
            combined_audio = io.BytesIO()
            
            # Write all chunks
            for chunk in audio_chunks:
                combined_audio.write(chunk)
            
            combined_audio.seek(0)
            audio_bytes = combined_audio.getvalue()
            
            if audio_bytes and len(audio_bytes) > 0:
                st.audio(audio_bytes, format="audio/mp3")
                logger.info(f"✅ Streamed audio ({len(audio_bytes)} bytes from {len(audio_chunks)} chunks)")
            else:
                st.warning("⚠️  Could not generate audio bytes.")
        else:
            st.warning("⚠️  Could not generate audio chunks.")
    except Exception as e:
        logger.error(f"❌ TTS error: {e}")
        logger.debug(traceback.format_exc())
        st.error(f"❌ TTS error: {e}")

def _listen_microphone() -> Optional[str]:
    """Listen from microphone and transcribe."""
    sr_inst = st.session_state.sr
    if sr_inst is None:
        st.error("❌ Speech Recognizer not available. Install it:\n\n```pip install SpeechRecognition```")
        return None
    
    try:
        with st.spinner("🎤 Listening... speak now (5 seconds timeout)"):
            text = sr_inst.recognize_from_microphone(timeout=5)
        
        if text:
            logger.info(f"✅ Recognized: {text[:50]}...")
            return text
        else:
            st.warning("⚠️  Could not recognize speech. Please try again.")
            logger.warning("Speech not recognized")
            return None
    
    except Exception as e:
        logger.error(f"❌ Microphone error: {e}")
        logger.debug(traceback.format_exc())
        st.error(f"❌ Microphone error: {e}\n\nMake sure your microphone is connected and working.")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="jarvis-header">🤖 JARVIS-LITE</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="jarvis-sub">Next-Generation AI Voice Assistant · '
    'Memory · Agent Routing · RAG · Voice I/O</div>',
    unsafe_allow_html=True,
)

if not AGENT_OK:
    st.error(f"⚠️ Agent failed to initialise: `{_AGENT_ERR}`")
    st.info("Make sure all dependencies are installed:\n\n```pip install -r requirements.txt```")

if not TTS_OK:
    st.warning(f"⚠️ TTS unavailable: `{_TTS_ERR}`. Install pyttsx3 for offline TTS:\n\n```pip install pyttsx3```")

if not SR_OK:
    st.warning(f"⚠️ Microphone unavailable: `{_SR_ERR}`. Install SpeechRecognition:\n\n```pip install SpeechRecognition PyAudio```")

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Settings")

    # --- Memory ---
    st.markdown("### Memory")
    mem_type = st.radio("Type", ["buffer", "summary"], horizontal=True)
    max_ctx  = st.slider("Max context messages", 3, 20, 5)

    if st.button("🗑️ New Conversation", use_container_width=True):
        st.session_state.messages = []
        if st.session_state.agent:
            st.session_state.agent.memory.clear()
        st.success("✅ Conversation cleared!")

    # --- Voice Settings ---
    st.divider()
    st.markdown("### 🎙️ Voice Settings")
    
    if TTS_OK:
        tts_backend = st.radio("TTS Backend", ["pyttsx3", "gtts"], horizontal=True, 
                               help="pyttsx3 = offline, gtts = online (requires internet)")
        lang = st.selectbox("Language", ["en", "hi", "es", "fr", "de"],
                           help="Language for text-to-speech")
        auto_audio = st.checkbox("Auto-play audio response", value=True)
        
        # Update TTS if settings changed
        if (tts_backend != st.session_state.tts_backend or 
            lang != st.session_state.tts_lang):
            from app.voice.text_to_speech import TextToSpeech
            try:
                st.session_state.tts = TextToSpeech(backend=tts_backend, language=lang)
                st.session_state.tts_backend = tts_backend
                st.session_state.tts_lang = lang
                st.success(f"✅ TTS updated: {tts_backend} ({lang})")
            except Exception as e:
                st.error(f"❌ Failed to update TTS: {e}")
    else:
        st.warning("⚠️ TTS unavailable. Install pyttsx3:\n\n```pip install pyttsx3```")
        auto_audio = False

    if not SR_OK:
        st.warning("⚠️ Microphone unavailable. Install:\n\n```pip install SpeechRecognition PyAudio```")

    # --- Stats ---
    st.divider()
    st.markdown("### Session Stats")
    msg_count   = len(st.session_state.messages)
    agent_ready = "✅" if AGENT_OK else "❌"
    tts_ready   = "✅" if TTS_OK   else "❌"
    sr_ready    = "✅" if SR_OK    else "❌"

    mem_count = (
        st.session_state.agent.memory.get_message_count()
        if st.session_state.agent else 0
    )

    col_a, col_b = st.columns(2)
    col_a.metric("Messages", msg_count // 2)
    col_b.metric("Memory ctx", mem_count)

    st.markdown(
        f"Agent: {agent_ready} &nbsp; TTS: {tts_ready} &nbsp; STT: {sr_ready}",
        unsafe_allow_html=True,
    )

    # --- Tools ---
    st.divider()
    st.markdown("### Available Tools")
    st.markdown("🧮 **Calculator** — math expressions")
    st.markdown("🌍 **Weather** — current weather")
    st.markdown("📚 **Document Search** — RAG over uploads")
    st.markdown("🤖 **Gemini LLM** — general reasoning")

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN CHAT AREA
# ══════════════════════════════════════════════════════════════════════════════
chat_col, info_col = st.columns([3, 1])

with chat_col:
    # ── quick-action chips ──────────────────────────────────────────────────
    st.markdown("**Quick Actions**")
    qa_cols = st.columns(4)
    quick_actions = [
        ("🧮", "Calculate 15 * 8"),
        ("🌍", "Weather in London"),
        ("📚", "Search my documents"),
        ("💡", "What can you do?"),
    ]
    qa_trigger: Optional[str] = None
    for col, (icon, label) in zip(qa_cols, quick_actions):
        if col.button(f"{icon} {label.split()[0]}", use_container_width=True):
            qa_trigger = label

    st.divider()

    # ── input section ───────────────────────────────────────────────────────
    input_method = st.radio("Input Method", ["Text", "Voice"], horizontal=True)

    user_input: Optional[str] = None

    if input_method == "Text":
        with st.form("chat_form", clear_on_submit=True):
            text_val = st.text_input(
                "Your message",
                placeholder="Ask me anything — try 'Calculate 2+2' or 'Weather in Tokyo'…",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Send ➤", use_container_width=True)
        if submitted and text_val.strip():
            user_input = text_val.strip()

    else:  # Voice
        if not SR_OK:
            st.error("❌ Microphone not available. Install SpeechRecognition:\n\n```pip install SpeechRecognition PyAudio```")
        else:
            st.info("🎤 **Click 'Record Voice Input' → Speak clearly → Wait for transcription**")
            
            if st.button("🎙️ Record Voice Input", use_container_width=True, key="voice_btn"):
                user_input = _listen_microphone()
                if user_input:
                    st.success(f"✅ Recognized: *{user_input}*")

    # Quick-action overrides text input
    if qa_trigger:
        user_input = qa_trigger

    # ── process message ─────────────────────────────────────────────────────
    if user_input:
        ts = _ts()
        st.session_state.messages.append(
            {"role": "user", "content": user_input, "ts": ts}
        )

        with st.spinner("Thinking…"):
            result = _process(user_input)

        answer    = result.get("answer", "No response generated.")
        tool_used = result.get("tool_used") or "Gemini LLM"
        confidence = result.get("confidence", 0.0)
        sources   = result.get("sources", [])

        ts2 = _ts()
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "ts": ts2,
                "tool_used": tool_used,
                "confidence": confidence,
                "sources": sources,
            }
        )

        # TTS auto-play
        if auto_audio and TTS_OK:
            st.markdown("---")
            st.subheader("🔊 Audio Response")
            _play_tts(answer)
        elif auto_audio and not TTS_OK:
            st.info("💡 Enable TTS in settings to hear responses.")

        # Execution details
        with st.expander("📊 Execution Details", expanded=False):
            d1, d2, d3 = st.columns(3)
            d1.metric("Tool Used",   tool_used)
            d2.metric("Confidence",  f"{confidence:.0%}")
            d3.metric("Sources",     len(sources))
            if sources:
                st.write("**Sources:**")
                for s in sources:
                    pg = f", p.{s['page']}" if s.get("page") else ""
                    st.write(f"  • {s['document_name']}{pg}")

    # ── conversation history ─────────────────────────────────────────────────
    st.divider()
    st.markdown("### Conversation")

    if not st.session_state.messages:
        st.markdown(
            '<p style="color:#555;font-style:italic;text-align:center;">'
            "No messages yet — say hello!</p>",
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.messages:
            _bubble(msg["role"], msg["content"], msg["ts"])

# ── right info panel ─────────────────────────────────────────────────────────
with info_col:
    st.markdown("#### Last Response")
    last_assistant = next(
        (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"),
        None,
    )
    if last_assistant:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">Tool</div>'
            f'<div class="metric-value" style="font-size:1em;">'
            f'{last_assistant.get("tool_used","—")}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="metric-card" style="margin-top:8px;">'
            f'<div class="metric-label">Confidence</div>'
            f'<div class="metric-value">'
            f'{last_assistant.get("confidence",0):.0%}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No response yet.")

    st.divider()
    st.markdown("#### How to Use")
    st.markdown("""
- Type any question and hit **Send**
- Try **Quick Actions** above
- Switch to **Voice** input for hands-free chat
- Enable **Auto-play** to hear responses
- Upload docs via CLI then ask about them
    """)

# ── footer ───────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    '<p style="text-align:center;color:#555;font-size:0.82em;">'
    "Jarvis-Lite v1.0 &nbsp;|&nbsp; Gemini + ChromaDB + LangChain"
    "</p>",
    unsafe_allow_html=True,
)
