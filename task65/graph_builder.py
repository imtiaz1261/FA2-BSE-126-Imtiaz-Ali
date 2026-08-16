"""
Neo4j Graph Builder — no numpy dependency.
All data is plain Python dicts / lists.
"""

from __future__ import annotations
from typing import Any, Dict, List

from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


class GraphBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        self._create_constraints()

    # ---------------------------------------------------------------- setup
    def _create_constraints(self):
        stmts = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Person)       REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Organization)  REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Project)       REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Skill)         REQUIRE n.id IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (n:Person)       ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Organization)  ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Project)       ON (n.name)",
        ]
        with self.driver.session() as s:
            for stmt in stmts:
                s.run(stmt)

    # ----------------------------------------------------------------- CRUD
    def create_nodes(self, nodes: List[Dict]):
        with self.driver.session() as s:
            for node in nodes:
                q = f"MERGE (n:{node['label']} {{id: $id}}) SET n += $props"
                s.run(q, id=node["id"], props=node["properties"])

    def create_relationships(self, edges: List[Dict]):
        with self.driver.session() as s:
            for edge in edges:
                q = f"""
                MATCH (src {{id: $src_id}})
                MATCH (tgt {{id: $tgt_id}})
                MERGE (src)-[r:{edge['type']}]->(tgt)
                SET r += $props
                """
                s.run(q, src_id=edge["source"], tgt_id=edge["target"],
                      props=edge["properties"])

    def add_document_to_graph(self, data: Dict):
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        self.create_nodes(nodes)
        self.create_relationships(edges)
        print(f"  + {len(nodes)} nodes, {len(edges)} edges ingested")

    def run_cypher(self, query: str, **params) -> List[Dict]:
        """Execute an arbitrary Cypher query and return rows as plain dicts."""
        with self.driver.session() as s:
            result = s.run(query, **params)
            return [record.data() for record in result]

    # -------------------------------------------------------- helpers
    def get_entity_neighbourhood(self, name: str, hops: int = 2) -> List[Dict]:
        """Return all nodes reachable from *name* within *hops* relationships."""
        q = f"""
        MATCH path = (start {{name: $name}})-[*1..{hops}]-(other)
        RETURN
            start.name                                        AS start,
            [n IN nodes(path)    | n.name]                   AS path_nodes,
            [r IN relationships(path) | type(r)]             AS rel_types,
            [n IN nodes(path)    | labels(n)[0]]             AS node_labels,
            length(path)                                     AS hops
        ORDER BY hops
        LIMIT 20
        """
        return self.run_cypher(q, name=name)

    def get_stats(self) -> Dict[str, Any]:
        with self.driver.session() as s:
            nodes = s.run(
                "MATCH (n) WITH labels(n)[0] AS lbl, count(*) AS c "
                "RETURN lbl, c ORDER BY c DESC"
            )
            rels = s.run(
                "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(*) AS c "
                "ORDER BY c DESC"
            )
            return {
                "nodes":         [r.data() for r in nodes],
                "relationships": [r.data() for r in rels],
            }

    def clear(self):
        with self.driver.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
        print("Graph cleared.")

    def close(self):
        self.driver.close()
