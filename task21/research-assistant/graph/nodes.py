"""
graph/nodes.py
---------------
Every LangGraph node function for the research workflow. Each node
takes the current ResearchState and returns a partial dict of updates,
which LangGraph merges into the state.

Nodes:
  - planner            : decompose the query into an objective + task list
  - web_search          : search the web for the current task, dedupe results
  - validator            : judge whether results are sufficient; decide
                           retry / continue / done (drives the conditional edge)
  - summarizer           : summarize each task's sources, then combine
  - report_generator      : produce the final structured Markdown report

route_after_validation() is the conditional-edge router function used
by graph/build.py.
"""

import json
import re
from datetime import datetime
from typing import Dict, List

from config import MAX_TASKS, MAX_RETRIES_PER_TASK, MIN_RESULTS_FOR_SUFFICIENCY
from llm import get_llm
from state import ResearchState, SourceResult
from tools.search_tool import search_web, dedupe_by_url, SearchError
from utils import get_logger

logger = get_logger(__name__)


def _log(state: ResearchState, message: str) -> str:
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {message}"
    logger.info(message)
    return entry


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from an LLM response that
    may include stray prose or markdown code fences around it."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(match.group(0))


# --------------------------------------------------------------------------
# Phase 1: Planner
# --------------------------------------------------------------------------
def planner_node(state: ResearchState) -> dict:
    query = state["query"]
    log_entries = []

    prompt = (
        "You are a research planning assistant. Given a user's research "
        "query, identify the core research objective and break it into "
        f"at most {MAX_TASKS} specific, individually-searchable sub-questions.\n\n"
        "Respond with ONLY a JSON object in this exact shape, no other text:\n"
        '{"objective": "...", "tasks": ["...", "..."]}\n\n'
        f"Query: {query}"
    )

    try:
        response = get_llm().invoke(prompt)
        parsed = _extract_json(response.content)
        objective = parsed.get("objective", "").strip() or query
        tasks = [t.strip() for t in parsed.get("tasks", []) if t.strip()][:MAX_TASKS]
        if not tasks:
            raise ValueError("Planner returned no tasks.")
    except Exception as exc:
        logger.warning("Planner LLM step failed (%s); falling back to single-task plan.", exc)
        objective = query
        tasks = [query]

    log_entries.append(_log(state, f"Planner: objective='{objective}', {len(tasks)} task(s) generated."))

    return {
        "objective": objective,
        "tasks": tasks,
        "current_task_index": 0,
        "search_results": {t: [] for t in tasks},
        "validated": {t: False for t in tasks},
        "retry_counts": {t: 0 for t in tasks},
        "node_log": state.get("node_log", []) + log_entries,
    }


# --------------------------------------------------------------------------
# Phase 2: Web Search
# --------------------------------------------------------------------------
def web_search_node(state: ResearchState) -> dict:
    tasks = state["tasks"]
    idx = state["current_task_index"]
    task = tasks[idx]
    log_entries = []
    errors = list(state.get("errors", []))

    try:
        new_results = search_web(task)
    except SearchError as exc:
        logger.error("Web search failed for task '%s': %s", task, exc)
        errors.append(f"Search error on task '{task}': {exc}")
        new_results: List[SourceResult] = []

    existing = state["search_results"].get(task, [])
    merged = dedupe_by_url(existing, new_results)

    search_results = dict(state["search_results"])
    search_results[task] = merged

    log_entries.append(_log(
        state,
        f"WebSearch: task='{task}' (+{len(new_results)} new, {len(merged)} total unique sources)",
    ))

    return {
        "search_results": search_results,
        "node_log": state.get("node_log", []) + log_entries,
        "errors": errors,
    }


# --------------------------------------------------------------------------
# Phase 3: Validator (+ retry/continue/done decision)
# --------------------------------------------------------------------------
def _llm_judge_sufficiency(task: str, sources: List[SourceResult]) -> bool:
    """Ask the LLM whether the collected sources sufficiently cover the task."""
    snippets = "\n".join(f"- {s['title']}: {s['snippet'][:200]}" for s in sources)
    prompt = (
        "You are validating research results. Given a research task and the "
        "snippets collected so far, judge whether they contain enough "
        "relevant, concrete information to answer the task.\n\n"
        'Respond with ONLY JSON: {"sufficient": true or false}\n\n'
        f"Task: {task}\n\nSnippets:\n{snippets}"
    )
    try:
        response = get_llm().invoke(prompt)
        parsed = _extract_json(response.content)
        return bool(parsed.get("sufficient", False))
    except Exception as exc:
        logger.warning("Validator LLM judgment failed (%s); using heuristic fallback.", exc)
        return len(sources) >= MIN_RESULTS_FOR_SUFFICIENCY


def validator_node(state: ResearchState) -> dict:
    tasks = state["tasks"]
    idx = state["current_task_index"]
    task = tasks[idx]
    sources = state["search_results"].get(task, [])
    log_entries = []

    # Cheap heuristic first: zero/near-zero results never need an LLM call.
    if len(sources) < MIN_RESULTS_FOR_SUFFICIENCY:
        is_sufficient = False
    else:
        is_sufficient = _llm_judge_sufficiency(task, sources)

    validated = dict(state["validated"])
    validated[task] = is_sufficient

    retry_counts = dict(state["retry_counts"])
    retries_used = retry_counts.get(task, 0)
    can_retry = retries_used < MAX_RETRIES_PER_TASK

    if not is_sufficient and can_retry:
        retry_counts[task] = retries_used + 1
        route_decision = "retry"
        log_entries.append(_log(
            state, f"Validator: task='{task}' INSUFFICIENT -> retry {retries_used + 1}/{MAX_RETRIES_PER_TASK}",
        ))
        new_index = idx  # stay on the same task
    else:
        status = "sufficient" if is_sufficient else "insufficient (retries exhausted)"
        log_entries.append(_log(state, f"Validator: task='{task}' {status} -> advancing"))
        new_index = idx + 1
        route_decision = "continue" if new_index < len(tasks) else "done"

    return {
        "validated": validated,
        "retry_counts": retry_counts,
        "current_task_index": new_index,
        "route_decision": route_decision,
        "node_log": state.get("node_log", []) + log_entries,
    }


def route_after_validation(state: ResearchState) -> str:
    """Conditional-edge router: reads route_decision set by validator_node."""
    decision = state.get("route_decision", "done")
    if decision == "retry":
        return "web_search"
    if decision == "continue":
        return "web_search"
    return "summarizer"


# --------------------------------------------------------------------------
# Phase 4: Summarizer
# --------------------------------------------------------------------------
def summarizer_node(state: ResearchState) -> dict:
    tasks = state["tasks"]
    log_entries = []
    task_summaries: Dict[str, str] = {}

    for task in tasks:
        sources = state["search_results"].get(task, [])
        if not sources:
            task_summaries[task] = "No reliable information was found for this sub-question."
            continue

        snippets = "\n".join(f"- {s['title']}: {s['snippet']}" for s in sources if s["snippet"])
        prompt = (
            "Summarize the following research snippets into a concise, factual "
            "paragraph (3-5 sentences) that answers the sub-question below. "
            "Only use information present in the snippets; do not add outside "
            "knowledge or invent facts.\n\n"
            f"Sub-question: {task}\n\nSnippets:\n{snippets}\n\nSummary:"
        )
        try:
            response = get_llm().invoke(prompt)
            task_summaries[task] = response.content.strip()
        except Exception as exc:
            logger.warning("Summarization failed for task '%s': %s", task, exc)
            task_summaries[task] = "Summary unavailable due to an internal error."

    log_entries.append(_log(state, f"Summarizer: produced {len(task_summaries)} task summarie(s)."))

    combined = "\n\n".join(f"**{task}**\n{summary}" for task, summary in task_summaries.items())

    return {
        "task_summaries": task_summaries,
        "combined_summary": combined,
        "node_log": state.get("node_log", []) + log_entries,
    }


# --------------------------------------------------------------------------
# Phase 5: Report Generator
# --------------------------------------------------------------------------
def report_generator_node(state: ResearchState) -> dict:
    from report.report_builder import build_markdown_report

    log_entries = []
    try:
        title, markdown = build_markdown_report(state)
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        title = f"Research Report: {state['query']}"
        markdown = (
            f"# {title}\n\nAn error occurred while generating the full report: {exc}\n\n"
            f"## Raw Summary\n\n{state.get('combined_summary', '')}"
        )

    log_entries.append(_log(state, "ReportGenerator: final report assembled."))

    return {
        "report_title": title,
        "report_markdown": markdown,
        "node_log": state.get("node_log", []) + log_entries,
    }
