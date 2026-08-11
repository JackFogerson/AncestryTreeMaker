"""Pure ethnicity inheritance calculations."""

from __future__ import annotations

from collections.abc import Mapping

from models import AncestorNode


UNKNOWN_ETHNICITY = "Unknown"
FULL_PERCENTAGE = 100.0


def calculate_inheritance(tree: Mapping[str, AncestorNode]) -> None:
    """Populate each node's computed ethnicities without drawing UI."""
    for node in tree.values():
        node.computed_ethnicities = {}

    roots = [name for name, node in tree.items() if not node.father and not node.mother]
    if not roots and tree:
        roots = [next(iter(tree))]

    for root_name in roots:
        _compute_node_heritage(tree, root_name, visited=set())


def _compute_node_heritage(tree: Mapping[str, AncestorNode], name: str, visited: set[str]) -> None:
    if name in visited or name not in tree:
        return
    visited.add(name)
    node = tree[name]

    if node.father or node.mother:
        if node.father:
            _compute_node_heritage(tree, node.father, visited)
        if node.mother:
            _compute_node_heritage(tree, node.mother, visited)

        has_father = bool(node.father and node.father in tree)
        has_mother = bool(node.mother and node.mother in tree)
        father_dna = tree[node.father].computed_ethnicities if has_father else {UNKNOWN_ETHNICITY: FULL_PERCENTAGE}
        mother_dna = tree[node.mother].computed_ethnicities if has_mother else {UNKNOWN_ETHNICITY: FULL_PERCENTAGE}

        is_single_parent = (node.father and not node.mother) or (node.mother and not node.father)
        if is_single_parent:
            parent_dna = father_dna if has_father else mother_dna
            if any(abs(percentage - FULL_PERCENTAGE) < 1e-5 for percentage in parent_dna.values()):
                ethnicity = next(ethnicity for ethnicity, percentage in parent_dna.items() if abs(percentage - FULL_PERCENTAGE) < 1e-5)
                node.computed_ethnicities = {ethnicity: FULL_PERCENTAGE}
            else:
                node.computed_ethnicities = _combine_parents(father_dna, mother_dna)
        else:
            node.computed_ethnicities = _combine_parents(father_dna, mother_dna)
    elif node.base_ethnicities:
        percentage = FULL_PERCENTAGE / len(node.base_ethnicities)
        node.computed_ethnicities = {ethnicity: percentage for ethnicity in node.base_ethnicities}
    else:
        node.computed_ethnicities = {UNKNOWN_ETHNICITY: FULL_PERCENTAGE}

    for child_name, child_node in tree.items():
        if child_node.father == name or child_node.mother == name:
            _compute_node_heritage(tree, child_name, visited.copy())


def _combine_parents(father_dna: Mapping[str, float], mother_dna: Mapping[str, float]) -> dict[str, float]:
    combined: dict[str, float] = {}
    for ethnicity, percentage in father_dna.items():
        combined[ethnicity] = combined.get(ethnicity, 0.0) + percentage * 0.5
    for ethnicity, percentage in mother_dna.items():
        combined[ethnicity] = combined.get(ethnicity, 0.0) + percentage * 0.5
    return combined
