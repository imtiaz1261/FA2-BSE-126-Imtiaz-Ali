"""
Pure-Python in-memory knowledge graph.
Drop-in replacement for GraphBuilder when Neo4j is unavailable.
Stores nodes and edges as plain dicts; supports a subset of Cypher-like
queries via Python methods.
"""

from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List, Optional


class InMemoryGraph:
    """Adjacency-list knowledge graph with named relationship types."""

    def __init__(self):
        # node_id → {"id", "label", "properties": {...}}
        self._nodes: Dict[str, Dict] = {}
        # list of {"src", "tgt", "type", "properties"}
        self._edges: List[Dict] = []

    # ─────────────────────────────────── write
    def merge_node(self, node_id: str, label: str, props: Dict):
        if node_id not in self._nodes:
            self._nodes[node_id] = {"id": node_id, "label": label,
                                    "properties": dict(props)}
        else:
            self._nodes[node_id]["properties"].update(props)

    def merge_edge(self, src_id: str, tgt_id: str, rel_type: str,
                   props: Optional[Dict] = None):
        # idempotent
        for e in self._edges:
            if e["src"] == src_id and e["tgt"] == tgt_id \
                    and e["type"] == rel_type:
                if props:
                    e["properties"].update(props)
                return
        self._edges.append({
            "src": src_id, "tgt": tgt_id,
            "type": rel_type,
            "properties": dict(props or {}),
        })

    def create_nodes(self, nodes: List[Dict]):
        for n in nodes:
            self.merge_node(n["id"], n["label"], n["properties"])

    def create_relationships(self, edges: List[Dict]):
        for e in edges:
            self.merge_edge(e["source"], e["target"], e["type"],
                            e.get("properties", {}))

    def add_document_to_graph(self, data: Dict):
        self.create_nodes(data.get("nodes", []))
        self.create_relationships(data.get("edges", []))
        print(f"  + {len(data.get('nodes',[]))} nodes, "
              f"{len(data.get('edges',[]))} edges ingested")

    def clear(self):
        self._nodes.clear()
        self._edges.clear()
        print("Graph cleared.")

    # ─────────────────────────────────── read helpers
    def _node_by_name(self, name: str) -> Optional[Dict]:
        for n in self._nodes.values():
            if n["properties"].get("name") == name:
                return n
        return None

    def _neighbours(self, node_id: str, rel_types=None,
                    direction="out") -> List[Dict]:
        """Return list of (edge, neighbour_node) pairs."""
        results = []
        for e in self._edges:
            if rel_types and e["type"] not in rel_types:
                continue
            if direction in ("out", "both") and e["src"] == node_id:
                nb = self._nodes.get(e["tgt"])
                if nb:
                    results.append((e, nb))
            if direction in ("in", "both") and e["tgt"] == node_id:
                nb = self._nodes.get(e["src"])
                if nb:
                    results.append((e, nb))
        return results

    def get_entity_neighbourhood(self, name: str, hops: int = 2) -> List[Dict]:
        start = self._node_by_name(name)
        if not start:
            return []

        rows = []
        # BFS up to `hops` levels, both directions
        frontier = [(start, [start], [])]  # (node, path_nodes, path_rels)
        visited_ids = {start["id"]}

        for _ in range(hops):
            next_frontier = []
            for node, path_nodes, path_rels in frontier:
                for edge, nb in self._neighbours(node["id"], direction="both"):
                    if nb["id"] in visited_ids:
                        continue
                    visited_ids.add(nb["id"])
                    new_path_nodes = path_nodes + [nb]
                    new_path_rels  = path_rels  + [edge]
                    next_frontier.append((nb, new_path_nodes, new_path_rels))
                    rows.append({
                        "start":       start["properties"].get("name"),
                        "path_nodes":  [n["properties"].get("name","?")
                                        for n in new_path_nodes],
                        "rel_types":   [r["type"] for r in new_path_rels],
                        "node_labels": [n["label"] for n in new_path_nodes],
                        "hops":        len(new_path_rels),
                    })
            frontier = next_frontier

        return rows

    def run_cypher(self, query: str, **params) -> List[Dict]:
        """
        Very limited Cypher-like interpreter for the patterns used in graph_rag.py.
        Handles the specific queries issued by _targeted_cypher().
        """
        q = query.strip()

        # ── MANAGED_BY ────────────────────────────────────────────────────
        if "MANAGED_BY" in q and "person, mgr.name" in q:
            name = params.get("n", "")
            node = self._node_by_name(name)
            if not node:
                return []
            results = []
            for e, nb in self._neighbours(node["id"], rel_types={"MANAGED_BY"},
                                          direction="out"):
                results.append({"person": name,
                                 "manager": nb["properties"].get("name")})
            return results

        # ── LEADS (person → project) ──────────────────────────────────────
        if "LEADS" in q and "person, pr.name AS project" in q:
            name = params.get("n", "")
            node = self._node_by_name(name)
            if not node:
                return []
            results = []
            for e, nb in self._neighbours(node["id"], rel_types={"LEADS"},
                                          direction="out"):
                results.append({"person": name,
                                 "project": nb["properties"].get("name")})
            return results

        # ── who leads a project ───────────────────────────────────────────
        if "LEADS" in q and "p.name AS person, pr.name AS project" in q:
            name = params.get("n", "")
            node = self._node_by_name(name)
            if not node:
                return []
            results = []
            for e, nb in self._neighbours(node["id"], rel_types={"LEADS"},
                                          direction="in"):
                results.append({"person": nb["properties"].get("name"),
                                 "project": name})
            return results

        # ── top of org (no manager) ───────────────────────────────────────
        if "WORKS_FOR" in q and "p.name AS person" in q:
            org_name = params.get("n", "")
            results = []
            for node in self._nodes.values():
                if node["label"] != "Person":
                    continue
                works_for_org = any(
                    e["tgt"] == self._node_by_name(org_name, ).get("id","__")
                    and e["type"] == "WORKS_FOR"
                    for e in self._edges if e["src"] == node["id"]
                )
                has_manager = any(
                    e["src"] == node["id"] and e["type"] == "MANAGED_BY"
                    for e in self._edges
                )
                if works_for_org and not has_manager:
                    results.append(
                        {"person": node["properties"].get("name")})
            return results

        # ── HAS_SKILL ─────────────────────────────────────────────────────
        if "HAS_SKILL" in q and "s.name AS skill" in q:
            name = params.get("n", "")
            node = self._node_by_name(name)
            if not node:
                return []
            results = []
            for e, nb in self._neighbours(node["id"], rel_types={"HAS_SKILL"},
                                          direction="out"):
                results.append({"skill": nb["properties"].get("name")})
            return results

        return []

    # fix for None check in run_cypher WORKS_FOR branch
    def _node_by_name(self, name: str) -> Dict:          # type: ignore[override]
        for n in self._nodes.values():
            if n["properties"].get("name") == name:
                return n
        return {}

    def get_stats(self) -> Dict[str, Any]:
        label_count: Dict[str, int] = defaultdict(int)
        for n in self._nodes.values():
            label_count[n["label"]] += 1
        rel_count: Dict[str, int] = defaultdict(int)
        for e in self._edges:
            rel_count[e["type"]] += 1
        return {
            "nodes":         [{"lbl": k, "c": v}
                              for k, v in sorted(label_count.items())],
            "relationships": [{"rel_type": k, "c": v}
                              for k, v in sorted(rel_count.items())],
        }

    # ── stubs so the rest of the code doesn't need to branch ──────────────
    def close(self):
        pass

    @property
    def driver(self):
        return _FakeDriver(self)


class _FakeSession:
    """Mimics neo4j Session.run() using the in-memory graph."""
    def __init__(self, graph: InMemoryGraph):
        self._g = graph

    def run(self, query: str, **params):
        # Used only for explicit relationship inserts in main.py
        import re
        # MERGE (a {name: $src}) MERGE (b {name: $tgt}) MERGE (a)-[:REL]->(b)
        m = re.search(r'MERGE \(a\)-\[:(\w+)\]->\(b\)', query)
        if m:
            rel_type = m.group(1)
            src_name = params.get("src", "")
            tgt_name = params.get("tgt", "")
            src_id = f"auto:{src_name}"
            tgt_id = f"auto:{tgt_name}"
            # ensure nodes exist
            if not self._g._node_by_name(src_name):
                self._g.merge_node(src_id, "Entity", {"name": src_name})
            else:
                src_id = next(
                    n["id"] for n in self._g._nodes.values()
                    if n["properties"].get("name") == src_name
                )
            if not self._g._node_by_name(tgt_name):
                self._g.merge_node(tgt_id, "Entity", {"name": tgt_name})
            else:
                tgt_id = next(
                    n["id"] for n in self._g._nodes.values()
                    if n["properties"].get("name") == tgt_name
                )
            self._g.merge_edge(src_id, tgt_id, rel_type)

    def __enter__(self):  return self
    def __exit__(self, *_): pass


class _FakeDriver:
    def __init__(self, graph: InMemoryGraph):
        self._g = graph

    def session(self):
        return _FakeSession(self._g)
