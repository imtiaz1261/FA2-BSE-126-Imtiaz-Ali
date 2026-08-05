"""
Deep Web Research Service — Phase 13.

Implements a Perplexity/ChatGPT Deep Research-style pipeline:

  User Query
      │
      ▼
  Intent Analysis          ← LLM extracts topic, scope, objectives
      │
      ▼
  Research Planner         ← generates 3-5 optimised search queries
      │
      ▼
  Parallel Web Search      ← Tavily; all queries fire concurrently
      │
      ▼
  Source Processing        ← deduplicate, filter low-quality, normalise
      │
      ▼
  Source Ranking           ← semantic relevance + freshness + authority
      │
      ▼
  Summariser               ← per-source key-findings extraction
      │
      ▼
  Report Writer            ← structured Markdown report with all sections
      │
      ▼
  AI Editor                ← grammar, coherence, dedup, formatting pass
      │
      ▼
  Final Report + Sources

The service streams ResearchEvent dicts to callers so the frontend can
show real-time progress steps identical to ChatGPT/Perplexity.

Wire events  (type field):
  "step"     — progress update: {"step": str, "detail": str}
  "sources"  — sources found:   {"sources": List[SourceDoc]}
  "report"   — final report:    {"report": str, "sources": List[SourceDoc]}
  "error"    — failure:         {"message": str}
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.services.llm_service import get_client

logger = logging.getLogger(__name__)


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class SourceDoc:
    title:       str
    url:         str
    domain:      str
    snippet:     str
    content:     str
    score:       float = 0.0
    published:   str   = ""
    author:      str   = ""
    key_findings: str  = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title":        self.title,
            "url":          self.url,
            "domain":       self.domain,
            "snippet":      self.snippet,
            "content":      self.content[:600],
            "score":        round(self.score, 3),
            "published":    self.published,
            "author":       self.author,
            "key_findings": self.key_findings,
        }


@dataclass
class ResearchPlan:
    intent:      str
    objectives:  List[str]
    queries:     List[str]


# ── Authority scoring ─────────────────────────────────────────────────────────

_HIGH_AUTH = {
    "arxiv.org", "nature.com", "science.org", "pubmed.ncbi.nlm.nih.gov",
    "github.com", "docs.python.org", "openai.com", "anthropic.com",
    "huggingface.co", "deepmind.com", "research.google", "microsoft.com",
    "mit.edu", "stanford.edu", "ieee.org", "acm.org",
}
_GOV_SUFFIXES = (".gov", ".edu", ".ac.uk", ".ac.jp")


def _authority_score(url: str) -> float:
    domain = urlparse(url).netloc.lower().lstrip("www.")
    if domain in _HIGH_AUTH:
        return 1.0
    if any(domain.endswith(s) for s in _GOV_SUFFIXES):
        return 0.9
    # prefer .org over commercial TLDs
    if domain.endswith(".org"):
        return 0.7
    return 0.5


# ── LLM helpers (all use the existing llm_service client) ────────────────────

async def _llm(system: str, user: str, temperature: float = 0.3, max_tokens: int = 1500) -> str:
    client = get_client()
    try:
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("Research LLM call failed: %s", exc)
        return ""


# ── Step 1: Intent Analysis + Research Plan ───────────────────────────────────

async def build_research_plan(query: str) -> ResearchPlan:
    """Analyse the query and generate optimised search sub-queries."""
    system = """You are a research planning AI.
Given a research query, output a JSON object with:
  "intent": one-sentence description of what the user wants to learn
  "objectives": list of 3-5 key research objectives (strings)
  "queries": list of 3-5 optimised web search queries that together
             cover the topic comprehensively. Avoid redundant queries.
Output ONLY valid JSON — no markdown fences, no extra text."""

    raw = await _llm(system, query, temperature=0.2, max_tokens=600)
    try:
        import json as _json
        data = _json.loads(raw)
        return ResearchPlan(
            intent=data.get("intent", query),
            objectives=data.get("objectives", [query]),
            queries=data.get("queries", [query])[: settings.RESEARCH_MAX_QUERIES],
        )
    except Exception:
        # Fallback: use the raw query as a single search
        return ResearchPlan(intent=query, objectives=[query], queries=[query])


# ── Step 2: Parallel Web Search ───────────────────────────────────────────────

async def _search_one(query: str, max_results: int = 5) -> List[Dict]:
    """Run a single Tavily search and return raw result dicts."""
    api_key = settings.TAVILY_API_KEY or settings.WEB_SEARCH_API_KEY
    if not api_key:
        return []
    try:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=api_key)
        resp = await client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_raw_content=True,
        )
        return resp.get("results", [])
    except ImportError:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=api_key)
            resp = client.search(query=query, max_results=max_results, search_depth="advanced")
            return resp.get("results", [])
        except Exception as exc:
            logger.warning("Tavily search failed for %r: %s", query, exc)
            return []
    except Exception as exc:
        logger.warning("Tavily async search failed for %r: %s", query, exc)
        return []


async def parallel_search(queries: List[str]) -> List[Dict]:
    """Fire all search queries concurrently and flatten results."""
    tasks = [_search_one(q, max_results=5) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    flat: List[Dict] = []
    for r in results:
        if isinstance(r, list):
            flat.extend(r)
    return flat


# ── Step 3: Source Processing ─────────────────────────────────────────────────

def process_sources(raw_results: List[Dict]) -> List[SourceDoc]:
    """Deduplicate, clean, and build SourceDoc objects."""
    seen_urls:  set[str] = set()
    seen_hashes: set[str] = set()
    docs: List[SourceDoc] = []

    for r in raw_results[: settings.RESEARCH_MAX_SOURCES * 3]:
        url     = r.get("url", "").strip()
        title   = (r.get("title") or "").strip()
        snippet = (r.get("content") or r.get("snippet") or "").strip()
        content = (r.get("raw_content") or snippet)[:3000]

        if not url or not snippet:
            continue

        # URL-level dedup
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Content-level dedup (hash first 200 chars)
        h = hashlib.md5(snippet[:200].encode()).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        # Filter junk
        if len(snippet) < 60:
            continue
        if any(kw in url.lower() for kw in ("login", "signup", "cart", "checkout")):
            continue

        domain    = urlparse(url).netloc.lower().lstrip("www.")
        published = r.get("published_date") or r.get("publishedDate") or ""

        docs.append(
            SourceDoc(
                title=title or domain,
                url=url,
                domain=domain,
                snippet=snippet[:300],
                content=content,
                published=published,
                score=r.get("score", 0.5),
            )
        )

    return docs[: settings.RESEARCH_MAX_SOURCES]


# ── Step 4: Source Ranking ────────────────────────────────────────────────────

def rank_sources(docs: List[SourceDoc], query: str) -> List[SourceDoc]:
    """
    Rank using: Tavily relevance score + authority bonus + freshness.
    Returns docs sorted best-first.
    """
    now_year = datetime.now(timezone.utc).year

    for doc in docs:
        auth   = _authority_score(doc.url)
        # freshness: prefer sources from the last 2 years
        fresh  = 0.0
        if doc.published:
            m = re.search(r"(20\d{2})", doc.published)
            if m:
                yr = int(m.group(1))
                fresh = max(0.0, 1.0 - (now_year - yr) / 5.0)

        # keyword overlap with original query
        q_tokens = set(query.lower().split())
        s_tokens = set(doc.content.lower().split())
        kw_score = len(q_tokens & s_tokens) / max(len(q_tokens), 1)

        doc.score = 0.40 * doc.score + 0.30 * auth + 0.20 * kw_score + 0.10 * fresh

    return sorted(docs, key=lambda d: d.score, reverse=True)


# ── Step 5: Per-source Summariser ─────────────────────────────────────────────

async def summarise_sources(
    docs: List[SourceDoc],
    query: str,
) -> List[SourceDoc]:
    """
    Extract key findings from each source concurrently.
    Mutates docs in place and returns them.
    """
    system = f"""You are a research assistant.
Given a web source excerpt and the research question "{query}",
extract 2-4 bullet-point key findings as a compact Markdown list.
Focus only on facts, statistics, and claims relevant to the question.
Be concise. Output ONLY the bullet list."""

    async def _summarise(doc: SourceDoc) -> None:
        text = doc.content[:1500]
        findings = await _llm(system, f"Source: {doc.title}\n\n{text}", max_tokens=250)
        doc.key_findings = findings.strip()

    await asyncio.gather(*[_summarise(d) for d in docs[:8]])
    return docs


# ── Step 6: Report Writer ─────────────────────────────────────────────────────

_REPORT_SYSTEM = """You are an expert technical report writer.
Write a comprehensive, well-structured Markdown research report.

Use this EXACT structure:
## Executive Summary
## Background
## Key Findings
## Technical Analysis
## Comparison / Landscape
## Advantages & Strengths
## Limitations & Challenges
## Future Trends
## Conclusion
## References

Rules:
- Cite sources inline as [Source N] where N matches the reference list.
- Use clear headings, bullet points, tables where appropriate.
- Be precise, factual, and professional.
- Do NOT include any personal opinions.
- References section: list every cited source as numbered Markdown links.
"""


async def write_report(
    query: str,
    plan: ResearchPlan,
    docs: List[SourceDoc],
) -> str:
    """Generate the full structured research report."""
    # Build context block
    context_lines = [f"# Research Question\n{query}\n"]
    context_lines.append(f"# Research Objectives\n" + "\n".join(f"- {o}" for o in plan.objectives))
    context_lines.append("\n# Source Findings\n")
    for i, doc in enumerate(docs[:10], 1):
        context_lines.append(
            f"[Source {i}] **{doc.title}** ({doc.domain})\n"
            f"URL: {doc.url}\n"
            f"{doc.key_findings or doc.snippet}\n"
        )

    context = "\n".join(context_lines)
    report  = await _llm(_REPORT_SYSTEM, context, temperature=0.2, max_tokens=3000)

    # Append clean reference list if LLM didn't include one
    if "## References" not in report:
        report += "\n\n## References\n"
        for i, doc in enumerate(docs[:10], 1):
            report += f"{i}. [{doc.title}]({doc.url})\n"

    return report


# ── Step 7: AI Editor ─────────────────────────────────────────────────────────

async def edit_report(report: str) -> str:
    """Polish the report: grammar, coherence, dedup, readability."""
    system = """You are a professional editor reviewing an AI-generated research report.
Your job:
1. Fix grammar, spelling, awkward phrasing.
2. Remove duplicate sentences or paragraphs.
3. Improve transitions between sections.
4. Ensure all headings are properly formatted.
5. Do NOT change facts, add new content, or remove section headers.
6. Return the complete, polished report in Markdown.
"""
    edited = await _llm(system, report, temperature=0.1, max_tokens=3500)
    return edited or report   # fall back to original if editor fails


# ── Main streaming pipeline ───────────────────────────────────────────────────

async def run_research(
    query: str,
    trace=None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Full research pipeline as an async generator of event dicts.
    Designed to be consumed by the research router's SSE endpoint.
    """
    from app.services.langfuse_service import finish_span, start_span

    def _step(step: str, detail: str = "") -> Dict[str, Any]:
        return {"type": "step", "step": step, "detail": detail}

    try:
        # 1. Understanding intent
        yield _step("Understanding request", query[:80])
        span = start_span(trace, "research-plan")
        plan = await build_research_plan(query)
        finish_span(span, output=f"{len(plan.queries)} queries planned")
        yield _step("Planning research", f"{len(plan.queries)} search queries")

        # 2. Parallel web search
        yield _step("Searching the web", f"Executing {len(plan.queries)} searches in parallel…")
        span2 = start_span(trace, "research-search")
        raw = await asyncio.wait_for(
            parallel_search(plan.queries),
            timeout=settings.RESEARCH_TIMEOUT_SECONDS - 20,
        )
        finish_span(span2, output=f"{len(raw)} raw results")
        yield _step("Reading sources", f"Found {len(raw)} results")

        # 3. Process + rank
        docs = process_sources(raw)
        docs = rank_sources(docs, query)
        yield _step("Ranking information", f"{len(docs)} quality sources selected")
        yield {"type": "sources", "sources": [d.to_dict() for d in docs[:10]]}

        # 4. Summarise per source
        yield _step("Summarizing sources", "Extracting key findings from each source…")
        await summarise_sources(docs, query)

        # 5. Write report
        yield _step("Writing report", "Composing structured research report…")
        span3 = start_span(trace, "research-report")
        report = await write_report(query, plan, docs)
        finish_span(span3, output=f"{len(report)} chars")

        # 6. Edit
        yield _step("Editing report", "AI editor reviewing for quality…")
        report = await edit_report(report)

        # 7. Done
        yield _step("Finalizing response", "Complete")
        yield {
            "type":    "report",
            "report":  report,
            "sources": [d.to_dict() for d in docs[:10]],
            "queries": plan.queries,
            "intent":  plan.intent,
        }

    except asyncio.TimeoutError:
        yield {"type": "error", "message": "Research timed out. Try a more focused query."}
    except Exception as exc:
        logger.exception("research pipeline failed")
        yield {"type": "error", "message": f"Research error: {exc}"}
