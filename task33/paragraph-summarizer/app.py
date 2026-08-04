"""
app.py
------
Streamlit app: paste a paragraph, pick a summary length, get a 3-line
summary back.

Run with:
    streamlit run app.py
"""

import streamlit as st

from summarizer import summarize, SummarizerError, LENGTH_PRESETS

st.set_page_config(page_title="3-Line Summarizer", page_icon="\U0001F4DD", layout="centered")

st.title("\U0001F4DD 3-Line Paragraph Summarizer")
st.caption("Paste a paragraph, pick a length, get a 3-line summary powered by Groq.")

paragraph = st.text_area(
    "Paste your paragraph here",
    height=220,
    placeholder="Paste any paragraph of text...",
)

length = st.radio(
    "Summary length",
    options=list(LENGTH_PRESETS.keys()),
    index=1,  # medium by default
    horizontal=True,
    format_func=lambda x: x.capitalize(),
)

if st.button("Summarize", type="primary"):
    try:
        with st.spinner("Summarizing..."):
            result = summarize(paragraph, length=length)
        st.subheader("Summary")
        st.write(result)
    except SummarizerError as exc:
        st.error(str(exc))
