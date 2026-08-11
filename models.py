"""Data-only domain models for the ancestry tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


LocationRecord = dict[str, Any]


@dataclass
class AncestorNode:
    """A person and the data required to render their ancestry."""

    name: str
    base_ethnicities: list[str] = field(default_factory=list)
    father: str | None = None
    mother: str | None = None
    display_name: str = ""
    birth_year: str = ""
    death_year: str = ""
    is_living: bool = False
    locations: list[LocationRecord] = field(default_factory=list)
    computed_ethnicities: dict[str, float] = field(default_factory=dict, init=False)
    signifiers: list[str] = field(default_factory=list)
    birth_location: str = ""
    death_location: str = ""

    def __post_init__(self) -> None:
        if not self.display_name:
            self.display_name = self.name
        if self.base_ethnicities is None:
            self.base_ethnicities = []
        if self.locations is None:
            self.locations = []
