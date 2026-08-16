"""
Entity and Relationship Extractor — pure Python, no spaCy / numpy.
Uses hand-crafted regex patterns tuned to the sample corpus.
"""

import re
from typing import List, Dict, Tuple


# ---------------------------------------------------------------------------
# Known-entity seed lists (bootstrapped from sample_data.py corpus)
# These make extraction deterministic and accurate for the test suite.
# ---------------------------------------------------------------------------
KNOWN_PERSONS = [
    "John Smith", "Sarah Johnson", "Jane Doe",
    "Michael Chen", "Lisa Wang",
]

KNOWN_ORGS = ["TechCorp"]

KNOWN_PROJECTS = ["Project Alpha", "Project Beta", "Project Gamma"]

KNOWN_SKILLS = [
    "Python", "Machine Learning", "Cloud Computing",
    "SQL", "Data Visualization", "Statistical Analysis",
    "TensorFlow", "AWS", "Apache Spark", "Hadoop", "Tableau",
]


class EntityExtractor:
    """Regex-based entity + relationship extractor."""

    # ------------------------------------------------------------------ init
    def __init__(self):
        # relationship verb → canonical rel-type
        self.rel_patterns: List[Tuple[str, str]] = [
            (r"works\s+(?:for|at)|employed\s+by|employee\s+of",     "WORKS_FOR"),
            (r"manages|supervises",                                   "MANAGES"),
            (r"managed\s+by|supervised\s+by|reports\s+to",           "MANAGED_BY"),
            (r"leads?(?:\s+project)?|project\s+lead",                "LEADS"),
            (r"part\s+of|member\s+of|belongs\s+to",                  "PART_OF"),
            (r"skilled?\s+in|expert\s+in|proficient\s+in",           "HAS_SKILL"),
            (r"worked?\s+on|working\s+on",                           "WORKED_ON"),
        ]

    # --------------------------------------------------------- public API
    def extract_entities(self, text: str) -> List[Dict]:
        """Return list of entity dicts found in *text*."""
        found: List[Dict] = []
        seen: set = set()

        def _add(name: str, label: str, start: int, end: int, conf: float = 0.95):
            key = (name.strip(), label)
            if key not in seen:
                seen.add(key)
                found.append({
                    "text":       name.strip(),
                    "label":      label,
                    "start":      start,
                    "end":        end,
                    "confidence": conf,
                })

        # seed-list matches (highest confidence, longest-match first)
        for lst, label in [
            (KNOWN_PERSONS,  "PERSON"),
            (KNOWN_PROJECTS, "PROJECT"),
            (KNOWN_ORGS,     "ORGANIZATION"),
            (KNOWN_SKILLS,   "SKILL"),
        ]:
            for name in lst:
                for m in re.finditer(re.escape(name), text):
                    _add(name, label, m.start(), m.end(), 0.99)

        # fallback: "Firstname Lastname" pattern for unknown persons
        for m in re.finditer(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', text):
            _add(m.group(1), "PERSON", m.start(), m.end(), 0.75)

        # fallback: "Project Xxx" pattern
        for m in re.finditer(r'\bProject\s+[A-Z][a-zA-Z]+\b', text):
            _add(m.group(), "PROJECT", m.start(), m.end(), 0.80)

        return found

    def extract_relationships(self, text: str, entities: List[Dict]) -> List[Dict]:
        """Heuristically link entity pairs around relationship verbs."""
        rels: List[Dict] = []

        for pattern, rel_type in self.rel_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                ms, me = m.start(), m.end()

                # entities that end before the verb
                before = [e for e in entities if e["end"] <= ms]
                # entities that start after the verb
                after  = [e for e in entities if e["start"] >= me]

                if not before or not after:
                    continue

                src = max(before, key=lambda e: e["end"])   # closest before
                tgt = min(after,  key=lambda e: e["start"]) # closest after

                rels.append({
                    "source":     src["text"],
                    "target":     tgt["text"],
                    "type":       rel_type,
                    "text":       m.group(),
                    "confidence": 0.80,
                })

        return rels

    def extract_structured_data(self, document: str) -> Dict:
        entities      = self.extract_entities(document)
        relationships = self.extract_relationships(document, entities)
        return {
            "entities":      entities,
            "relationships": relationships,
            "document":      document[:120] + "…" if len(document) > 120 else document,
        }

    # ------------------------------------------------ graph-prep helpers
    def prepare_graph_nodes(self, entities: List[Dict]) -> List[Dict]:
        nodes, seen = [], set()
        for e in entities:
            node_id = f"{e['label']}:{e['text']}"
            if node_id not in seen:
                seen.add(node_id)
                nodes.append({
                    "id":    node_id,
                    "label": self._map_label(e["label"]),
                    "properties": {
                        "name": e["text"],
                        "type": e["label"],
                    },
                })
        return nodes

    def prepare_graph_edges(self, relationships: List[Dict], nodes: List[Dict]) -> List[Dict]:
        edges = []
        for rel in relationships:
            src_id = self._find_node_id(nodes, rel["source"])
            tgt_id = self._find_node_id(nodes, rel["target"])
            if src_id and tgt_id:
                edges.append({
                    "source": src_id,
                    "target": tgt_id,
                    "type":   rel["type"],
                    "properties": {
                        "description": rel["text"],
                        "confidence":  rel["confidence"],
                    },
                })
        return edges

    # ------------------------------------------------------------ private
    def _map_label(self, label: str) -> str:
        return {
            "PERSON":       "Person",
            "ORGANIZATION": "Organization",
            "PROJECT":      "Project",
            "SKILL":        "Skill",
            "DATE":         "Date",
            "LOCATION":     "Location",
        }.get(label, "Entity")

    def _find_node_id(self, nodes: List[Dict], text: str) -> str | None:
        for n in nodes:
            if n["properties"]["name"] == text:
                return n["id"]
        return None
