"""Document manager UI: upload, list, delete (Phase 8)."""

import streamlit as st

from api_client.client import api_client

ACCEPTED_EXTENSIONS = ["pdf", "docx", "txt", "md"]


def _load_documents(token: str) -> None:
    result = api_client.list_documents(token)
    if result.ok:
        st.session_state["documents"] = result.data
    else:
        st.session_state["documents"] = []
        st.error(result.error)


def render_document_manager() -> None:
    token = st.session_state["access_token"]

    uploaded = st.file_uploader(
        "Upload a document",
        type=ACCEPTED_EXTENSIONS,
        accept_multiple_files=False,
        key="doc_uploader",
        help="PDF, DOCX, TXT, or MD.",
    )
    if uploaded is not None and st.button("Upload", key="confirm_upload", use_container_width=True):
        result = api_client.upload_document(token, uploaded.name, uploaded.type, uploaded.getvalue())
        if result.ok:
            st.success(f"Uploaded {uploaded.name}")
            _load_documents(token)
            st.rerun()
        else:
            st.error(result.error)

    if "documents" not in st.session_state:
        _load_documents(token)

    documents = st.session_state.get("documents", [])
    if not documents:
        st.caption("No documents uploaded yet.")
        return

    for doc in documents:
        cols = st.columns([5, 1])
        with cols[0]:
            size_kb = doc["size_bytes"] / 1024
            st.write(f"**{doc['filename']}**")
            st.caption(f"{size_kb:.0f} KB · {doc['status']}")
        with cols[1]:
            if st.button("🗑", key=f"delete_doc_{doc['id']}", help="Delete"):
                result = api_client.delete_document(token, doc["id"])
                if result.ok:
                    _load_documents(token)
                    st.rerun()
                else:
                    st.error(result.error)
