"""Pure position calculation for ancestor trees."""

from __future__ import annotations

from collections.abc import Mapping

from models import AncestorNode


def calculate_positions(tree: Mapping[str, AncestorNode], isolated_root: str | None) -> dict[str, tuple[float, float]]:
    if not tree:
        return {}
    roots = [isolated_root] if isolated_root in tree else _display_roots(tree)
    positions: dict[str, tuple[float, float]] = {}
    leaf_memo: dict[str, int] = {}

    def assign(name: str, x: float, y: float, width: float) -> None:
        if name not in tree or name in positions:
            return
        positions[name] = (x, y)
        node = tree[name]
        if node.father and node.mother:
            father_leaves, mother_leaves = _count_leaves(tree, node.father, leaf_memo), _count_leaves(tree, node.mother, leaf_memo)
            total = father_leaves + mother_leaves
            father_width = father_leaves / total * width
            mother_width = mother_leaves / total * width
            assign(node.father, x - width / 2 + father_width / 2, y - 500.0, father_width)
            assign(node.mother, x + width / 2 - mother_width / 2, y - 500.0, mother_width)
        elif node.father:
            assign(node.father, x, y - 500.0, width)
        elif node.mother:
            assign(node.mother, x, y - 500.0, width)

    max_depth = max((_max_depth(tree, root, set()) for root in roots), default=1)
    current_x = 200.0
    base_y = max(600.0, max_depth * 500.0 + 100.0)
    for root in roots:
        width = _count_leaves(tree, root, leaf_memo) * 140.0
        assign(root, current_x + width / 2, base_y, width)
        current_x += width + 150.0
    return positions


def display_roots(tree: Mapping[str, AncestorNode]) -> list[str]:
    return _display_roots(tree)


def _display_roots(tree: Mapping[str, AncestorNode]) -> list[str]:
    parents = {parent for node in tree.values() for parent in (node.father, node.mother) if parent}
    return [name for name in tree if name not in parents] or [next(iter(tree))]


def _count_leaves(tree: Mapping[str, AncestorNode], name: str, memo: dict[str, int]) -> int:
    if name not in tree:
        return 1
    if name in memo:
        return memo[name]
    node = tree[name]
    if not node.father and not node.mother:
        return 1
    memo[name] = max(1, ( _count_leaves(tree, node.father, memo) if node.father else 0) + (_count_leaves(tree, node.mother, memo) if node.mother else 0))
    return memo[name]


def _max_depth(tree: Mapping[str, AncestorNode], name: str, visited: set[str]) -> int:
    if name in visited or name not in tree:
        return 0
    visited.add(name)
    node = tree[name]
    return 1 + max(_max_depth(tree, node.father, visited) if node.father else 0, _max_depth(tree, node.mother, visited) if node.mother else 0)
