"""
GraphRAG Engine — uses Groq (free) or OpenAI, no LangChain / numpy.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from graph_builder   import GraphBuilder
from in_memory_graph import InMemoryGraph
from config import GROQ_API_KEY, OPENAI_API_KEY, LLM_MODEL, MAX_HOPS, USE_GROQ


def _make_graph():
    """Return a live Neo4j GraphBuilder, or an InMemoryGraph fallback."""
    try:
        g = GraphBuilder()
        # quick connectivity check
        with g.driver.session() as s:
            s.run("RETURN 1")
        print("  [graph] Connected to Neo4j.")
        return g
    except Exception:
        print("  [graph] Neo4j unavailable — using in-memory graph.")
        return InMemoryGraph()


def _get_llm_client():
    """Get Groq or OpenAI client and return (client, provider_name)."""
    if USE_GROQ and GROQ_API_KEY:
        try:
            from groq import Groq
            print("  [LLM] Using Groq API (free tier) — no rate limiting!")
            return Groq(api_key=GROQ_API_KEY), "groq"
        except ImportError:
            print("  [LLM] Groq SDK not installed. Installing...")
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "groq", "-q"])
            from groq import Groq
            return Groq(api_key=GROQ_API_KEY), "groq"
    elif OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-openai-key-here":
        try:
            from openai import OpenAI
            print("  [LLM] Using OpenAI API")
            return OpenAI(api_key=OPENAI_API_KEY), "openai"
        except ImportError:
            return None, None
    return None, None


class GraphRAG:
    def __init__(self, graph=None):
        self.graph = graph if graph is not None else _make_graph()
        self.client, self.provider = _get_llm_client()

    # ---------------------------------------------------- query helpers
    def _extract_names(self, query: str) -> List[str]:
        """Pull capitalized-word sequences that look like entity names."""
        candidates = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', query)
        # filter very short / common words
        stopwords = {"Who", "What", "Which", "Where", "When", "The",
                     "Does", "Has", "Are", "Is", "Project"}
        return [c for c in candidates if c not in stopwords]

    def _build_graph_context(self, query: str) -> str:
        """Retrieve relevant subgraph and serialise it as readable text."""
        names = self._extract_names(query)
        parts: List[str] = []

        for name in names:
            rows = self.graph.get_entity_neighbourhood(name, hops=MAX_HOPS)
            if not rows:
                continue
            parts.append(f"[Entity: {name}]")
            for row in rows:
                path_str = " → ".join(
                    f"{n}({t})"
                    for n, t in zip(row["path_nodes"], row["node_labels"])
                )
                rels_str = ", ".join(row["rel_types"])
                parts.append(f"  path ({row['hops']} hop{'s' if row['hops']>1 else ''}): "
                              f"{path_str}  [{rels_str}]")
            parts.append("")

        # also run a direct Cypher for common multi-hop patterns
        extra = self._targeted_cypher(query)
        if extra:
            parts.append("[Targeted graph query result]")
            parts.extend(extra)

        return "\n".join(parts) if parts else "No relevant subgraph found."

    def _targeted_cypher(self, query: str) -> List[str]:
        """Run hand-crafted Cypher for recognisable question patterns."""
        q = query.lower()
        lines: List[str] = []

        # "who is X's manager / who manages X"
        m = re.search(r"manager\s+of\s+([a-z ]+)", q) or \
            re.search(r"([a-z ]+?)(?:'s)?\s+manager", q) or \
            re.search(r"who\s+manages\s+([a-z ]+)", q)
        if m:
            name = m.group(1).strip().title()
            rows = self.graph.run_cypher(
                "MATCH (p {name:$n})-[:MANAGED_BY]->(mgr) "
                "RETURN p.name AS person, mgr.name AS manager",
                n=name)
            for r in rows:
                lines.append(f"  {r['person']} is managed by {r['manager']}")

        # "what project does X lead / leads"
        m = re.search(r"project.*?(?:does|did)\s+([a-z ]+?)\s+lead", q) or \
            re.search(r"([a-z ]+?)\s+leads?\s+(?:which\s+)?project", q)
        if m:
            name = m.group(1).strip().title()
            rows = self.graph.run_cypher(
                "MATCH (p {name:$n})-[:LEADS]->(pr) "
                "RETURN p.name AS person, pr.name AS project",
                n=name)
            for r in rows:
                lines.append(f"  {r['person']} leads {r['project']}")

        # "who leads / project lead of X"
        m = re.search(r"(?:who\s+leads?|lead\s+of)\s+([a-z ]+)", q)
        if m:
            proj = m.group(1).strip().title()
            rows = self.graph.run_cypher(
                "MATCH (p)-[:LEADS]->(pr {name:$n}) "
                "RETURN p.name AS person, pr.name AS project",
                n=proj)
            for r in rows:
                lines.append(f"  {r['person']} leads {r['project']}")

        # "CEO / founder of X"
        m = re.search(r"(?:ceo|founder)\s+of\s+([a-z ]+)", q)
        if m:
            org = m.group(1).strip().title()
            rows = self.graph.run_cypher(
                "MATCH (p)-[:WORKS_FOR]->(o {name:$n}) "
                "WHERE NOT (p)-[:MANAGED_BY]->() "
                "   OR (p)-[:MANAGED_BY]->()-[:MANAGED_BY*0..]->() "
                "RETURN p.name AS person",
                n=org)
            # fallback: find who has no manager inside the org
            if not rows:
                rows = self.graph.run_cypher(
                    "MATCH (p:Person)-[:WORKS_FOR]->(o {name:$n}) "
                    "WHERE NOT EXISTS { MATCH (p)-[:MANAGED_BY]->() } "
                    "RETURN p.name AS person",
                    n=org)
            for r in rows:
                lines.append(f"  {r['person']} is at the top of {org}")

        # skills of a person
        m = re.search(r"skills?\s+(?:does\s+)?([a-z ]+?)\s+(?:have|has)", q) or \
            re.search(r"([a-z ]+?)(?:'s)?\s+skills?", q)
        if m:
            name = m.group(1).strip().title()
            rows = self.graph.run_cypher(
                "MATCH (p {name:$n})-[:HAS_SKILL]->(s) RETURN s.name AS skill",
                n=name)
            if rows:
                skills = ", ".join(r["skill"] for r in rows)
                lines.append(f"  {name}'s skills: {skills}")

        return lines

    # --------------------------------------------------- LLM answer
    def _generate_answer(self, query: str, context: str) -> str:
        if not self.client:
            return f"[LLM unavailable]\n\nRaw context:\n{context}"

        system = (
            "You are a GraphRAG assistant. Answer questions strictly using "
            "the knowledge-graph context below. Mention the entity names and "
            "relationships you used. Keep answers concise (2-3 sentences)."
        )
        user = f"Question: {query}\n\nKnowledge Graph Context:\n{context}"

        try:
            if self.provider == "groq":
                resp = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )
            elif self.provider == "openai":
                resp = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    temperature=0.1,
                )
            else:
                return f"[Unknown LLM provider]\n\nRaw context:\n{context}"

            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"[LLM error: {str(e)[:100]}]\n\nRaw context:\n{context}"

    # --------------------------------------------------- public API
    def answer(self, query: str) -> Dict[str, Any]:
        context = self._build_graph_context(query)
        answer  = self._generate_answer(query, context)
        return {
            "query":   query,
            "context": context,
            "answer":  answer,
        }

    def close(self):
        self.graph.close()
