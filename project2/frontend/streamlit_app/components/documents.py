"""
Premium Document Manager — Knowledge Base UI.
Drag-drop upload, status badges, indexing progress, auto-refresh.
"""
import time
import streamlit as st
from api_client.client import api_client
from ui_components import status_badge, toast_success, toast_error

ACCEPTED = ["pdf", "docx", "txt", "md"]

_EXT_COLORS = {
    "PDF": ("#ef4444", "rgba(239,68,68,0.1)"),
    "DOCX": ("#4f8ef7", "rgba(79,142,247,0.1)"),
    "TXT": ("#22c55e", "rgba(34,197,94,0.1)"),
    "MD": ("#8b5cf6", "rgba(139,92,246,0.1)"),
}

_DOC_CSS = """
<style>
.doc-stats {
    display: flex; gap: 16px; margin-bottom: 12px;
}
.doc-stat {
    background: #0f1629; border: 1px solid #1e2d47; border-radius: 10px;
    padding: 10px 14px; flex: 1; text-align: center;
}
.doc-stat-num { color: #f0f4ff; font-size: 1.2rem; font-weight: 700; }
.doc-stat-lbl { color: #4a5568; font-size: 0.72rem; }
.doc-row {
    display: flex; align-items: center; gap: 12px;
    background: #131d32; border: 1px solid #1e2d47;
    border-radius: 12px; padding: 12px 14px; margin: 6px 0;
    transition: all 0.15s ease;
}
.doc-row:hover { border-color: #2a3d63; background: #1a2540; }
.doc-ext {
    font-size: 0.65rem; font-weight: 700; padding: 5px 7px;
    border-radius: 7px; min-width: 38px; text-align: center;
    flex-shrink: 0;
}
.doc-name { color: #f0f4ff; font-weight: 600; font-size: 0.88rem; }
.doc-meta { color: #4a5568; font-size: 0.74rem; margin-top: 2px; }
</style>
"""


def _load_docs(token: str) -> None:
    result = api_client.list_documents(token)
    st.session_state["documents"] = result.data if result.ok else []


def _doc_stats_html(docs: list) -> str:
    total   = len(docs)
    ready   = sum(1 for d in docs if d.get("status") == "ready")
    pending = sum(1 for d in docs if d.get("status") in ("processing","uploaded"))
    failed  = sum(1 for d in docs if d.get("status") == "failed")
    total_kb = sum(d.get("size_bytes",0) for d in docs) / 1024
    return (
        '<div class="doc-stats">'
        f'<div class="doc-stat"><div class="doc-stat-num">{total}</div>'
        f'<div class="doc-stat-lbl">Total</div></div>'
        f'<div class="doc-stat"><div class="doc-stat-num" style="color:#22c55e;">{ready}</div>'
        f'<div class="doc-stat-lbl">Ready</div></div>'
        f'<div class="doc-stat"><div class="doc-stat-num" style="color:#f59e0b;">{pending}</div>'
        f'<div class="doc-stat-lbl">Indexing</div></div>'
        f'<div class="doc-stat"><div class="doc-stat-num">{total_kb:.0f}</div>'
        f'<div class="doc-stat-lbl">KB</div></div>'
        '</div>'
    )


def render_document_manager() -> None:
    token = st.session_state["access_token"]
    st.markdown(_DOC_CSS, unsafe_allow_html=True)

    # ── Upload ────────────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Drop a file or click to browse",
        type=ACCEPTED,
        accept_multiple_files=False,
        key="doc_uploader",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        if st.button("⬆ Index Document", type="primary",
                     use_container_width=True, key="confirm_upload"):
            with st.spinner(f"Uploading {uploaded.name}…"):
                result = api_client.upload_document(
                    token, uploaded.name, uploaded.type, uploaded.getvalue()
                )
            if result.ok:
                toast_success(f"{uploaded.name} uploaded — indexing in background…")
                _load_docs(token)
                st.rerun()
            else:
                toast_error(result.error or "Upload failed.")

    # ── Document list ─────────────────────────────────────────────────────────
    if "documents" not in st.session_state:
        _load_docs(token)

    docs = st.session_state.get("documents", [])

    if not docs:
        st.markdown(
            '<div style="text-align:center;padding:20px 8px;">'
            '<div style="font-size:2rem;margin-bottom:8px;">📂</div>'
            '<div style="color:#4a5568;font-size:0.82rem;">No documents yet</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(_doc_stats_html(docs), unsafe_allow_html=True)

    in_progress = [d for d in docs if d.get("status") in ("uploaded","processing")]

    for doc in docs:
        status  = doc.get("status","unknown")
        name    = doc.get("filename","Unknown")
        size_kb = doc.get("size_bytes",0) / 1024
        ext     = name.rsplit(".",1)[-1].upper() if "." in name else "FILE"
        col, bg = _EXT_COLORS.get(ext, ("#94a3b8","rgba(148,163,184,0.1)"))

        c1, c2 = st.columns([8, 1])
        with c1:
            st.markdown(
                f'<div class="doc-row">'
                f'<div class="doc-ext" style="color:{col};background:{bg};">{ext}</div>'
                f'<div style="flex:1;min-width:0;">'
                f'<div class="doc-name" style="white-space:nowrap;overflow:hidden;'
                f'text-overflow:ellipsis;">{name}</div>'
                f'<div class="doc-meta">{size_kb:.0f} KB</div></div>'
                f'<div>{status_badge(status)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with c2:
            if st.button("✕", key=f"del_d_{doc['id']}", help="Delete"):
                res = api_client.delete_document(token, doc["id"])
                if res.ok:
                    _load_docs(token)
                    st.rerun()
                else:
                    toast_error(res.error or "Delete failed.")

        if status == "failed":
            st.markdown(
                '<div style="color:#ef4444;font-size:0.76rem;'
                'margin:-4px 0 4px 52px;">Indexing failed — delete and re-upload</div>',
                unsafe_allow_html=True,
            )

    if in_progress:
        st.markdown(
            f'<div style="color:#f59e0b;font-size:0.76rem;margin-top:6px;">'
            f'⟳ {len(in_progress)} document(s) indexing…</div>',
            unsafe_allow_html=True,
        )
        time.sleep(4)
        _load_docs(token)
        st.rerun()
