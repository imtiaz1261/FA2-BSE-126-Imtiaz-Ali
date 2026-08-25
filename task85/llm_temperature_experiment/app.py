import os
import tempfile
from pathlib import Path

import streamlit as st

from services.tts_service import TTSService, TTSServiceError
from utils.validators import MAX_CHARACTERS, validate_text

st.set_page_config(
    page_title="AI Text-to-Speech",
    page_icon="🎙️",
    layout="centered",
)

st.markdown("""
<style>
    .main-title {
        text-align:center;
        font-size:2.5rem;
        font-weight:800;
        margin-bottom:0.2rem;
    }
    .subtitle {
        text-align:center;
        color:#718096;
        margin-bottom:2rem;
    }
    .counter {
        color:#718096;
        font-size:0.85rem;
        text-align:right;
    }
    .info-card {
        padding:1rem 1.2rem;
        border-radius:14px;
        background:rgba(128,128,128,.08);
        border:1px solid rgba(128,128,128,.15);
        margin-bottom:1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎙️ AI Text-to-Speech</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Convert your text into clear speech — locally, privately, and easily.</div>',
    unsafe_allow_html=True,
)

# Keep generated audio between reruns.
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

tts = TTSService()

with st.container():
    st.subheader("📝 Enter your text")
    text = st.text_area(
        "Text",
        placeholder="Type or paste the text you want to hear...",
        height=220,
        max_chars=MAX_CHARACTERS,
        label_visibility="collapsed",
    )

    words = len(text.split()) if text.strip() else 0
    st.markdown(
        f'<div class="counter">{len(text):,} / {MAX_CHARACTERS:,} characters · {words:,} words</div>',
        unsafe_allow_html=True,
    )

st.divider()

st.subheader("🎛️ Voice Controls")

try:
    voices = tts.get_voices()
except TTSServiceError as exc:
    voices = []
    st.warning(str(exc))

voice_options = {"Default voice": None}
for voice in voices:
    voice_options[voice["label"]] = voice["id"]

col1, col2 = st.columns(2)

with col1:
    selected_voice_label = st.selectbox(
        "Voice",
        list(voice_options.keys()),
    )
    selected_voice = voice_options[selected_voice_label]

    rate = st.slider(
        "Speech speed",
        min_value=80,
        max_value=240,
        value=165,
        step=5,
        help="Words-per-minute style rate used by the local TTS engine.",
    )

with col2:
    volume = st.slider(
        "Volume",
        min_value=0.0,
        max_value=1.0,
        value=1.0,
        step=0.05,
    )

    st.caption("Language")
    st.info("Uses the voices/languages installed on your operating system.")

button_col1, button_col2 = st.columns(2)

with button_col1:
    generate = st.button(
        "🔊 Generate Speech",
        type="primary",
        use_container_width=True,
    )

with button_col2:
    clear = st.button(
        "🗑️ Clear Text",
        use_container_width=True,
    )

if clear:
    st.session_state.audio_path = None
    st.session_state.audio_bytes = None
    st.rerun()

if generate:
    error = validate_text(text)

    if error:
        st.error(error)
    else:
        with st.spinner("Generating speech..."):
            try:
                output_dir = Path(tempfile.gettempdir()) / "devmind_tts"
                output_dir.mkdir(exist_ok=True)

                output_path = output_dir / "speech.wav"

                tts.generate(
                    text=text.strip(),
                    output_path=output_path,
                    voice_id=selected_voice,
                    rate=rate,
                    volume=volume,
                )

                audio_bytes = output_path.read_bytes()

                if not audio_bytes:
                    raise TTSServiceError("The generated audio file is empty.")

                st.session_state.audio_path = str(output_path)
                st.session_state.audio_bytes = audio_bytes

                st.success("Speech generated successfully.")

            except TTSServiceError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected error while generating speech: {exc}")

if st.session_state.audio_bytes:
    st.divider()
    st.subheader("🎧 Generated Audio")

    st.audio(
        st.session_state.audio_bytes,
        format="audio/wav",
    )

    st.download_button(
        label="⬇️ Download Audio",
        data=st.session_state.audio_bytes,
        file_name="generated_speech.wav",
        mime="audio/wav",
        use_container_width=True,
    )

st.divider()

st.markdown(
    '<div class="info-card"><b>🔒 Privacy:</b> pyttsx3 uses your operating system speech engine, so the text does not need to be sent to a cloud TTS API.</div>',
    unsafe_allow_html=True,
)

st.caption("Built with Python • Streamlit • pyttsx3")
