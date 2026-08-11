"""Shared utilities with no feature-specific dependencies."""

from .geocoder import create_geocoder, is_available

__all__ = ["create_geocoder", "is_available"]
