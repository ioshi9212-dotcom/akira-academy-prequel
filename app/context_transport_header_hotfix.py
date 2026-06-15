"""Runtime header/footer hotfix v18. Energy lives inside character cards; no separate per-type files."""
from __future__ import annotations
try:
    import app.calendar_context_runtime_patch as calendar_patch  # noqa: F401
except Exception: calendar_patch=None
try:
    import app.lore_context_runtime_patch as lore_patch  # noqa: F401
except Exception: lore_patch=None
try:
    import app.context_cleanup_runtime_patch as cleanup_patch  # noqa: F401
except Exception: cleanup_patch=None
import app.runtime_speed_patch as speed_patch  # noqa: F401
import app.context_transport_runtime_patch as rt
from app.runtime_speed_patch import app
rt.MINIMAL_LOCK_FILES=["gpt/locks/runtime_scene_rules_digest.md"]
try:
    import app.scene_output_format_runtime_patch as scene_format_patch  # noqa: F401
except Exception: scene_format_patch=None
app.version="0.3.41-character-card-energy-header-v18"
rt.MEDIUM_STYLE_FORMAT_DIGEST="""
## Medium scene style digest — strict Academy scene format
Use old Academy header/footer. Energy should be visually/physically felt when relevant: cold, heat, sound, vibration, pressure, metal tremor, trajectory shift. Personal energy is in character cards, not in separate per-type files.
"""
