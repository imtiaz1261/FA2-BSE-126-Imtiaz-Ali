"""
api.py
------
FastAPI backend exposing the research workflow over HTTP, so the
Streamlit frontend (or any other client) can trigger a research run
and fetch/export the resulting report.

Run with:
    uvicorn api:app --host 127.0.0.1 --port 8000 --reload
"""

import uuid
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import OUTPUTS_DIR, API_HOST, API_PORT
from graph.build import build_graph, get_mermaid_diagram
from llm import LLMInitError
from report.report_builder import export_pdf, export_docx
from state import new_initial_state
from utils import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Multi-Step Research Assistant API",
    description="LangGraph-powered research workflow: plan, search, validate, summarize, report.",
    version="1.0.0",
)

# In-memory store of completed run states, keyed by run_id, so the report
# can be fetched/exported in a follow-up request without re-running research.
_RUNS: dict = {}


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    run_id: str
    query: str
    objective: str
    tasks: List[str]
    node_log: List[str]
    errors: List[str]
    report_title: str
    report_markdown: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/graph/mermaid")
def graph_mermaid():
    """Return the LangGraph workflow structure as Mermaid diagram syntax."""
    try:
        return {"mermaid": get_mermaid_diagram()}
    except LLMInitError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    """Run the full research workflow for a query and return the report."""
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        graph = build_graph()
        run_id = str(uuid.uuid4())[:8]
        config = {"configurable": {"thread_id": run_id}}
        final_state = graph.invoke(new_initial_state(query), config=config)
    except LLMInitError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        logger.error("Research run failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Research run failed: {exc}")

    _RUNS[run_id] = final_state

    return ResearchResponse(
        run_id=run_id,
        query=query,
        objective=final_state.get("objective", ""),
        tasks=final_state.get("tasks", []),
        node_log=final_state.get("node_log", []),
        errors=final_state.get("errors", []),
        report_title=final_state.get("report_title", ""),
        report_markdown=final_state.get("report_markdown", ""),
    )


@app.get("/report/{run_id}/export")
def export_report(run_id: str, fmt: str = "pdf"):
    """Export a previously completed run's report as pdf or docx."""
    state = _RUNS.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No run found with id '{run_id}'.")

    safe_name = f"report_{run_id}"
    if fmt == "pdf":
        path = export_pdf(state["report_title"], state["report_markdown"], OUTPUTS_DIR / f"{safe_name}.pdf")
        media_type = "application/pdf"
    elif fmt == "docx":
        path = export_docx(state["report_title"], state["report_markdown"], OUTPUTS_DIR / f"{safe_name}.docx")
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="fmt must be 'pdf' or 'docx'.")

    return FileResponse(path=str(path), media_type=media_type, filename=path.name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=API_HOST, port=API_PORT, reload=True)
