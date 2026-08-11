"""Compatibility helpers for persisted tree data."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def normalize_save_data(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Supply defaults required by legacy saves without altering stored meaning."""
    return {
        "master_ethnicities": list(raw.get("master_ethnicities", [])),
        "ethnicity_colors": dict(raw.get("ethnicity_colors", {})),
        "nodes": dict(raw.get("nodes", {})),
    }
