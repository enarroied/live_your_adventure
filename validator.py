"""
validator.py — Compatibility checks between a graph template and a story package.

All rules from the spec are enforced here.
The engine calls validate() before gameplay begins.
Errors are collected (not raised immediately) so all problems are reported at once.
"""

from __future__ import annotations

from collections import deque


def validate(graph: dict, story: dict) -> list[str]:
    """
    Run all compatibility checks.

    Returns a list of error strings.
    An empty list means the pair is valid and gameplay can start.
    """
    errors: list[str] = []

    # ── 1. Graph identifier match ──────────────────────────────────────────
    if graph.get("graph_id") != story.get("graph_id"):
        errors.append(
            f"graph_id mismatch: graph='{graph.get('graph_id')}' "
            f"story='{story.get('graph_id')}'"
        )

    # ── 2. Start node exists ───────────────────────────────────────────────
    if "A" not in graph.get("nodes", {}):
        errors.append("Start node 'A' is missing from the graph.")

    # ── 3. Ending nodes have no outgoing edges ─────────────────────────────
    for node_id, node in graph.get("nodes", {}).items():
        if node.get("type") == "ending":
            if node_id in graph.get("edges", {}):
                errors.append(
                    f"Ending node '{node_id}' must not have outgoing edges."
                )

    # ── 4. Scene nodes must have outgoing edges ────────────────────────────
    for node_id, node in graph.get("nodes", {}).items():
        if node.get("type") == "scene":
            if node_id not in graph.get("edges", {}) or not graph["edges"][node_id]:
                errors.append(
                    f"Scene node '{node_id}' has no outgoing edges."
                )

    # ── 5. All edge targets exist as nodes ────────────────────────────────
    all_node_ids = set(graph.get("nodes", {}).keys())
    for src, targets in graph.get("edges", {}).items():
        for tgt in targets:
            if tgt not in all_node_ids:
                errors.append(
                    f"Edge '{src}' → '{tgt}': target node '{tgt}' does not exist."
                )

    # ── 6. Reachability from start node ───────────────────────────────────
    reachable = _reachable_nodes(graph)
    for node_id in all_node_ids:
        if node_id not in reachable:
            errors.append(f"Node '{node_id}' is not reachable from start node 'A'.")

    # ── 7. Every path terminates in an ending node ────────────────────────
    unreachable_endings = _paths_without_ending(graph)
    for node_id in unreachable_endings:
        errors.append(
            f"Node '{node_id}' has a path that never reaches an ending node."
        )

    # ── 8. Node coverage: every graph node must exist in story ────────────
    story_nodes = set(story.get("nodes", {}).keys())
    for node_id in all_node_ids:
        if node_id not in story_nodes:
            errors.append(f"Graph node '{node_id}' is missing from the story package.")

    # ── 9. No extra story nodes ────────────────────────────────────────────
    for node_id in story_nodes:
        if node_id not in all_node_ids:
            errors.append(f"Story node '{node_id}' does not exist in the graph.")

    # ── 10. Edge coverage: every graph edge must have a choice label ───────
    story_choices = story.get("choices", {})

    # Normalise choice keys: accept both "A,AA" strings and ("A","AA") tuples
    normalised_choices: set[tuple[str, str]] = set()
    for key in story_choices:
        if isinstance(key, str):
            parts = key.split(",", 1)
            if len(parts) == 2:
                normalised_choices.add((parts[0].strip(), parts[1].strip()))
        elif isinstance(key, (list, tuple)) and len(key) == 2:
            normalised_choices.add((str(key[0]), str(key[1])))

    for src, targets in graph.get("edges", {}).items():
        for tgt in targets:
            if (src, tgt) not in normalised_choices:
                errors.append(
                    f"Edge '{src}' → '{tgt}' has no choice label in the story package."
                )

    return errors


# ── Helpers ────────────────────────────────────────────────────────────────────

def _reachable_nodes(graph: dict) -> set[str]:
    """BFS from start node 'A'."""
    visited: set[str] = set()
    queue: deque[str] = deque(["A"])
    edges = graph.get("edges", {})

    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for neighbour in edges.get(node, []):
            if neighbour not in visited:
                queue.append(neighbour)

    return visited


def _paths_without_ending(graph: dict) -> set[str]:
    """
    Return the set of nodes from which no path reaches an ending node.
    Uses a backward reachability pass: mark all nodes that *can* reach
    an ending, then report those that cannot.
    """
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", {})

    # Reverse edge map
    reverse: dict[str, list[str]] = {n: [] for n in nodes}
    for src, targets in edges.items():
        for tgt in targets:
            if tgt in reverse:
                reverse[tgt].append(src)

    # Seed with all ending nodes
    can_reach_ending: set[str] = set()
    queue: deque[str] = deque()

    for node_id, node in nodes.items():
        if node.get("type") == "ending":
            can_reach_ending.add(node_id)
            queue.append(node_id)

    while queue:
        node = queue.popleft()
        for predecessor in reverse.get(node, []):
            if predecessor not in can_reach_ending:
                can_reach_ending.add(predecessor)
                queue.append(predecessor)

    return set(nodes.keys()) - can_reach_ending
