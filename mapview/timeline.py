"""Pure construction of migration-map timeline steps."""

from __future__ import annotations

from collections.abc import Mapping

from models import AncestorNode


def build_timeline_steps(tree: Mapping[str, AncestorNode]) -> tuple[list[tuple[int, int]], int, int]:
    years: set[int] = set()
    for node in tree.values():
        years.update(location["year"] for location in node.locations)
        if node.birth_year.isdigit():
            years.add(int(node.birth_year))
        if node.death_year.isdigit():
            years.add(int(node.death_year))
    if not years:
        return [], 0, 0
    minimum, maximum = min(years), max(years)
    steps: list[tuple[int, int]] = []
    for year in range(minimum, maximum + 1):
        max_locations = max(
            (sum(1 for location in node.locations if location["year"] == year and location.get("lat") is not None and location.get("lon") is not None) for node in tree.values()),
            default=0,
        )
        steps.extend((year, index) for index in range(1, max(1, max_locations) + 1))
    return steps, minimum, maximum
