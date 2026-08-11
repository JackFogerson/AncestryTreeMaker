"""JSON persistence for ancestry trees."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from models import AncestorNode
from .compatibility import normalize_save_data


def save_tree_file(path: str | Path, tree: Mapping[str, AncestorNode], ethnicity_options: list[str], ethnicity_colors: Mapping[str, str]) -> None:
    """Write the current, backward-compatible tree JSON format."""
    payload = json.dumps(tree_to_data(tree, ethnicity_options, ethnicity_colors), indent=4)
    Path(path).write_text(payload, encoding="utf-8")


def load_tree_file(path: str | Path) -> tuple[dict[str, AncestorNode], list[str], dict[str, str]]:
    """Load both current and legacy JSON files."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return data_to_tree(raw)


def tree_to_data(tree: Mapping[str, AncestorNode], ethnicity_options: list[str], ethnicity_colors: Mapping[str, str]) -> dict[str, Any]:
    """Return the existing JSON-compatible dictionary representation."""
    return {
        "master_ethnicities": ethnicity_options,
        "ethnicity_colors": dict(ethnicity_colors),
        "nodes": {
            name: {
                "name": node.name,
                "display_name": node.display_name,
                "birth_year": node.birth_year,
                "death_year": node.death_year,
                "is_living": node.is_living,
                "base_ethnicities": node.base_ethnicities,
                "father": node.father,
                "mother": node.mother,
                "locations": node.locations,
                "signifiers": node.signifiers,
                "birth_location": node.birth_location,
                "death_location": node.death_location,
            }
            for name, node in tree.items()
        },
    }


def data_to_tree(raw: Mapping[str, Any]) -> tuple[dict[str, AncestorNode], list[str], dict[str, str]]:
    """Deserialize legacy and current save data without changing its meaning."""
    normalized = normalize_save_data(raw)
    tree: dict[str, AncestorNode] = {}
    for name, data in normalized["nodes"].items():
        node = AncestorNode(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            birth_year=data.get("birth_year", ""),
            death_year=data.get("death_year", ""),
            is_living=data.get("is_living", False),
            base_ethnicities=data.get("base_ethnicities", []),
            father=data.get("father"),
            mother=data.get("mother"),
            locations=data.get("locations", []),
            signifiers=data.get("signifiers", []),
            birth_location=data.get("birth_location", ""),
            death_location=data.get("death_location", ""),
        )
        tree[name] = node
    return tree, normalized["master_ethnicities"], normalized["ethnicity_colors"]
