"""
components/chat_input.py
------------------------
Chat input component using Streamlit's native ``st.chat_input``.

``st.chat_input`` renders a sticky bottom input bar that:
- Stays fixed at the page bottom automatically (no CSS hacks needed)
- Submits on Enter (Shift+Enter for newline)
- Returns the submitted string and clears itself on submit
- Can be disabled while the backend is processing

Returns
-------
``get_user_input()`` → str | None
    The submitted query this rerun, or None.

Pre-fill (suggestion cards)
---------------------------
Suggestion cards set ``st.session_state.pending_input``.
This component consumes that value and returns it as if the user
had typed it, so the chat submission flow is identical.

Regenerate
----------
When ``st.session_state.regenerate_trigger`` is True the last user
query is returned so ``app.py`` can re-submit it.
"""

from __future__ import annotations

import streamlit as st

from utils.session import get_last_user_query, pop_regenerate_trigger


def render_chat_input() -> str | None:
    """
    Render the sticky chat input bar and return a query string when
    the user submits something.

    Priority order:
    1. Regenerate trigger  (re-submit last query)
    2. Pending input       (set by suggestion cards)
    3. Native chat_input   (user typed something)

    Returns ``None`` when there is no new input this rerun.
    """
    is_processing = st.session_state.get("is_processing", False)

    # ── 1. Regenerate trigger ─────────────────────────────────────────────────
    if pop_regenerate_trigger():
        last = get_last_user_query()
        if last:
            return last

    # ── 2. Consume suggestion-card pre-fill ───────────────────────────────────
    pending = st.session_state.get("pending_input", "")
    if pending:
        st.session_state.pending_input = ""   # consume once
        return pending.strip()

    # ── 3. Native Streamlit chat input ────────────────────────────────────────
    # st.chat_input is always rendered (even while processing) but
    # setting disabled=True greys it out and blocks submission.
    prompt = st.chat_input(
        placeholder="Ask anything…",
        disabled=is_processing,
        key="main_chat_input",
    )

    if prompt and prompt.strip() and not is_processing:
        return prompt.strip()

    return None
