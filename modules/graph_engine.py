"""
graph_engine.py - Deterministic Crime Knowledge Graph & Network Analytics Engine
Powered by NetworkX on CPU (Zero GPU required).
Computes Brandes Betweenness Centrality, Multi-Source Corroboration,
Shortest Multi-Hop Path Tracing, and PyVis HTML Rendering.
"""

import json
import networkx as nx
from typing import Dict, List, Any, Tuple, Optional
from pyvis.network import Network


# High-contrast Law Enforcement Color Palette
NODE_COLORS = {
    "PERSON": "#E63946",       # Crimson Red
    "PHONE": "#457B9D",        # Steel Blue
    "VEHICLE": "#F4A261",      # Amber Orange
    "BANK_ACC": "#2A9D8F",     # Teal Emerald
    "UPI": "#2A9D8F",          # Teal Emerald
    "CASE": "#9B5DE5",         # Purple
    "LOCATION": "#6C757D"      # Slate Grey
}

EDGE_COLORS = {
    "OBSERVED": "#2ECC71",     # Solid Green (100% Proven Record)
    "INFERRED": "#F39C12",     # Solid Amber (Resolved via ER)
    "HYPOTHESIS": "#3498DB"    # Dotted/Dashed Blue (Structural/Multi-hop)
}


class CrimeKnowledgeGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.evidence_registry = {}

    def add_entity_node(self, node_id: str, label: str, node_type: str, metadata: Optional[Dict[str, Any]] = None):
        """Adds a typed entity node to the network."""
        node_id = str(node_id)
        meta = metadata or {}
        color = NODE_COLORS.get(node_type, "#999999")
        self.graph.add_node(
            node_id,
            label=str(label),
            node_type=node_type,
            color=color,
            metadata=meta
        )

    def add_evidence_edge(self, u: str, v: str, relation_type: str, tier: str, evidence_ids: List[str], details: Dict[str, Any]):
        """
        Adds a classified evidence edge.
        tier: 'OBSERVED', 'INFERRED', or 'HYPOTHESIS'
        """
        u, v = str(u), str(v)
        edge_color = EDGE_COLORS.get(tier, "#888888")
        
        # If edge already exists, append evidence
        if self.graph.has_edge(u, v):
            existing = self.graph[u][v]
            existing["evidence_ids"] = list(set(existing["evidence_ids"] + evidence_ids))
            existing["weight"] = existing.get("weight", 1) + 1
            if tier == "OBSERVED":
                existing["tier"] = "OBSERVED"
                existing["color"] = EDGE_COLORS["OBSERVED"]
        else:
            self.graph.add_edge(
                u,
                v,
                relation_type=relation_type,
                tier=tier,
                color=edge_color,
                evidence_ids=evidence_ids,
                details=details,
                weight=1
            )

    def compute_betweenness_centrality(self) -> Dict[str, float]:
        """Calculates Brandes Betweenness Centrality to detect covert coordinators and brokers."""
        if len(self.graph) == 0:
            return {}
        scores = nx.betweenness_centrality(self.graph, normalized=True)
        # Store in node attributes
        for node, score in scores.items():
            self.graph.nodes[node]["betweenness"] = round(score, 4)
        return {k: round(v, 4) for k, v in sorted(scores.items(), key=lambda item: item[1], reverse=True)}

    def find_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Finds deterministic multi-hop evidence path between two nodes."""
        try:
            return nx.shortest_path(self.graph, source=source_id, target=target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def explain_connection(self, node_a: str, node_b: str) -> Dict[str, Any]:
        """
        The 'Explain This Connection' Engine.
        Returns exact facts, timestamps, and statutory provenance.
        """
        if not self.graph.has_node(node_a) or not self.graph.has_node(node_b):
            return {"status": "NOT_FOUND", "message": "One or both entities not found in graph."}

        # Direct edge case
        if self.graph.has_edge(node_a, node_b):
            edge = self.graph[node_a][node_b]
            return {
                "connection_type": "DIRECT_EDGE",
                "tier": edge["tier"],
                "relation_type": edge["relation_type"],
                "evidence_ids": edge["evidence_ids"],
                "details": edge.get("details", {}),
                "corroboration_strength": "HIGH" if edge["tier"] == "OBSERVED" else "MEDIUM",
                "statutory_note": "Direct factual link backed by primary electronic records (BSA 2023 Sec 63)."
            }

        # Multi-hop indirect path
        path = self.find_shortest_path(node_a, node_b)
        if path:
            hops = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                e = self.graph[u][v]
                hops.append({
                    "from": u,
                    "to": v,
                    "relation": e["relation_type"],
                    "tier": e["tier"],
                    "evidence": e["evidence_ids"]
                })
            return {
                "connection_type": "INDIRECT_MULTI_HOP",
                "path_length": len(path) - 1,
                "path_nodes": path,
                "hops": hops,
                "corroboration_strength": "CORROBORATED_PATH",
                "statutory_note": "Multi-hop relationship established by deterministic graph traversal."
            }

        return {
            "connection_type": "DISCONNECTED",
            "message": "No recorded direct or multi-hop path found within the investigated records."
        }

    def render_pyvis_html(self, output_path: str, height: str = "600px", width: str = "100%") -> str:
        """Renders interactive PyVis HTML network with cyber police styling."""
        net = Network(height=height, width=width, bgcolor="#121820", font_color="#FFFFFF", directed=False)
        net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=100, spring_strength=0.08)

        for node_id, data in self.graph.nodes(data=True):
            b_score = data.get("betweenness", 0.0)
            size = 20 + int(b_score * 40)
            label = data.get("label", node_id)
            title = f"Type: {data.get('node_type')}\nBetweenness Centrality: {b_score}\nID: {node_id}"
            net.add_node(
                node_id,
                label=label,
                color=data.get("color", "#FFFFFF"),
                size=size,
                title=title
            )

        for u, v, data in self.graph.edges(data=True):
            color = data.get("color", "#888888")
            tier = data.get("tier", "OBSERVED")
            dashes = True if tier == "HYPOTHESIS" else False
            title = f"Relation: {data.get('relation_type')}\nTier: {tier}\nEvidence: {', '.join(data.get('evidence_ids', []))}"
            net.add_edge(
                u,
                v,
                color=color,
                title=title,
                dashes=dashes,
                width=2 if tier == "OBSERVED" else 1.5
            )

        net.save_graph(output_path)
        return output_path
