"""
frontend/pages/documents_page.py — Document Management (3D glassmorphism)
"""

import sys
from pathlib import Path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import requests
from backend.core.config import settings
from frontend.utils.session_state import get_auth_headers


_EXT_ICON = {
    "pdf": "📕", "txt": "📝", "md": "📋",
    "docx": "📘", "doc": "📘", "csv": "📊",
}


def _fetch_docs() -> list:
    try:
        r = requests.get(
            f"{settings.BACKEND_URL}/api/v1/documents/list",
            headers=get_auth_headers(),
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("documents", [])
    except Exception:
        pass
    return []


def _status_badge(status: str) -> str:
    mapping = {
        "ready":      ("badge-green",  "Ready"),
        "processing": ("badge-orange", "Processing"),
        "pending":    ("badge-blue",   "Pending"),
        "failed":     ("badge-red",    "Failed"),
    }
    cls, label = mapping.get(status, ("badge-blue", status.title()))
    return f'<span class="badge {cls}">{label}</span>'


def render_documents_page() -> None:
    st.markdown("""
    <div class="page-header">
        <div class="page-title">📄 Documents</div>
        <div class="page-subtitle">Upload files to use as context in your AI conversations</div>
    </div>
    """, unsafe_allow_html=True)

    tab_upload, tab_library = st.tabs(["⬆️  Upload", "📚  Library"])

    # ── Upload ────────────────────────────────────────────────
    with tab_upload:
        st.markdown("""
        <div class="glass-card" style="text-align:center;
             border-style:dashed;border-color:rgba(99,102,241,0.3);
             padding:2.5rem">
            <div style="font-size:2.5rem;margin-bottom:8px">📂</div>
            <div style="font-weight:600;color:var(--text-primary);
                        font-size:0.9375rem">Drop a file here or click Browse</div>
            <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px">
                Supported: PDF, TXT, MD, DOCX, CSV &nbsp;·&nbsp; Max 20 MB
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Choose file",
            type=["pdf", "txt", "md", "docx", "csv"],
            label_visibility="collapsed",
        )

        if uploaded:
            c1, c2 = st.columns([3, 1])
            with c1:
                ext  = uploaded.name.rsplit(".", 1)[-1].lower()
                icon = _EXT_ICON.get(ext, "📄")
                size_mb = uploaded.size / (1024 * 1024)
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:12px;
                            padding:12px 16px;background:rgba(255,255,255,0.03);
                            border:1px solid var(--border-glass);border-radius:12px">
                    <span style="font-size:1.5rem">{icon}</span>
                    <div>
                        <div style="font-weight:600;color:var(--text-primary);
                                    font-size:0.875rem">{uploaded.name}</div>
                        <div style="font-size:0.75rem;color:var(--text-muted)">
                            {size_mb:.2f} MB
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                if st.button("Upload  →", type="primary", use_container_width=True, key="do_upload"):
                    with st.spinner("Uploading…"):
                        try:
                            r = requests.post(
                                f"{settings.BACKEND_URL}/api/v1/documents/upload",
                                headers={
                                    k: v for k, v in get_auth_headers().items()
                                    if k != "Content-Type"
                                },
                                files={"file": (uploaded.name, uploaded.getvalue())},
                                timeout=60,
                            )
                            if r.status_code == 200:
                                st.success("Document uploaded and queued for processing!")
                                st.rerun()
                            else:
                                st.error(r.json().get("detail", "Upload failed"))
                        except Exception as exc:
                            st.error(f"Connection error: {exc}")

    # ── Library ───────────────────────────────────────────────
    with tab_library:
        docs = _fetch_docs()

        if not docs:
            st.markdown("""
            <div style="text-align:center;padding:4rem 1rem">
                <div style="font-size:3rem;margin-bottom:8px">📂</div>
                <div style="color:var(--text-muted);font-size:0.9rem">
                    No documents yet. Upload a file to get started.
                </div>
            </div>
            """, unsafe_allow_html=True)
            return

        # summary bar
        total_size = sum(d.get("size_bytes", 0) for d in docs) / (1024 * 1024)
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:24px;
                    padding:10px 16px;background:rgba(255,255,255,0.02);
                    border:1px solid var(--border-glass);
                    border-radius:10px;margin-bottom:1rem">
            <div>
                <span style="font-size:0.75rem;color:var(--text-muted);
                             text-transform:uppercase;letter-spacing:0.06em;
                             font-weight:600">Documents</span>
                <span style="font-weight:700;color:var(--text-primary);
                             margin-left:8px">{len(docs)}</span>
            </div>
            <div>
                <span style="font-size:0.75rem;color:var(--text-muted);
                             text-transform:uppercase;letter-spacing:0.06em;
                             font-weight:600">Total size</span>
                <span style="font-weight:700;color:var(--text-primary);
                             margin-left:8px">{total_size:.1f} MB</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for doc in docs:
            doc_id   = doc.get("id", "")
            filename = doc.get("filename", "Untitled")
            ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            icon     = _EXT_ICON.get(ext, "📄")
            size_mb  = doc.get("size_bytes", 0) / (1024 * 1024)
            status   = doc.get("status", "ready")
            created  = (doc.get("created_at") or "")[:10]
            chunks   = doc.get("chunk_count", 0)

            col_info, col_act = st.columns([6, 1])
            with col_info:
                st.markdown(f"""
                <div class="glass-card" style="padding:14px 18px;margin:4px 0">
                    <div style="display:flex;align-items:center;gap:14px">
                        <span style="font-size:1.625rem">{icon}</span>
                        <div style="flex:1;min-width:0">
                            <div style="font-weight:600;color:var(--text-primary);
                                        font-size:0.9rem;white-space:nowrap;
                                        overflow:hidden;text-overflow:ellipsis">
                                {filename}
                            </div>
                            <div style="font-size:0.75rem;color:var(--text-muted);
                                        margin-top:3px;display:flex;gap:12px">
                                <span>{size_mb:.2f} MB</span>
                                <span>{chunks} chunks</span>
                                <span>{created}</span>
                            </div>
                        </div>
                        {_status_badge(status)}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_act:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                if st.button("🗑", key=f"del_{doc_id}", help="Delete document"):
                    try:
                        r = requests.delete(
                            f"{settings.BACKEND_URL}/api/v1/documents/{doc_id}",
                            headers=get_auth_headers(),
                            timeout=10,
                        )
                        if r.status_code == 200:
                            st.success("Deleted")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                    except Exception as exc:
                        st.error(str(exc))
