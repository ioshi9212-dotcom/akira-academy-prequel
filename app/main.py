"""Compatibility entrypoint.

The active Railway/API app is assembled through app.server -> runtime patches.
Older app.main depended on removed app.core modules and could crash accidental imports.
"""

from app.server import app  # noqa: F401

__all__ = ["app"]
