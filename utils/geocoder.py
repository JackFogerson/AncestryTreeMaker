"""Optional geocoding dependency boundary."""

from __future__ import annotations

try:
    from geopy.geocoders import Nominatim
except ImportError:
    Nominatim = None


def create_geocoder() -> object | None:
    """Create the application's optional Nominatim client when available."""
    return Nominatim(user_agent="ancestor_timeline_mapper") if Nominatim else None


def is_available() -> bool:
    return Nominatim is not None
