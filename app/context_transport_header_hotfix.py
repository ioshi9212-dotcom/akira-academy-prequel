"""Runtime header/footer hotfix v20.

Connects runtime layers:
- calendar/lore/cleanup/speed
- scene format
- state persistence
- POV switch
- compact turn-contract with rich-scene rules
- world integrity diagnostics
"""
from __future__ import annotations

try:
    import app.calendar_context_runtime_patch as calendar_patch  # noqa: F401
except Exception:
    calendar_patch = None
try:
    import app.lore_context_runtime_patch as lore_patch  # noqa: F401
except Exception:
    lore_patch = None
try:
    import app.context_cleanup_runtime_patch as cleanup_patch  # noqa: F401
except Exception:
    cleanup_patch = None

import app.runtime_speed_patch as speed_patch  # noqa: F401
import app.context_transport_runtime_patch as rt
from app.runtime_speed_patch import app

rt.MINIMAL_LOCK_FILES = ["gpt/locks/runtime_scene_rules_digest.md"]

try:
    import app.scene_output_format_runtime_patch as scene_format_patch  # noqa: F401
except Exception:
    scene_format_patch = None
try:
    import app.state_persistence_runtime_patch as state_persistence_patch  # noqa: F401
except Exception:
    state_persistence_patch = None
try:
    import app.pov_switch_runtime_patch as pov_switch_patch  # noqa: F401
except Exception:
    pov_switch_patch = None
try:
    import app.turn_contract_compact_runtime_patch as turn_contract_compact_patch  # noqa: F401
except Exception:
    turn_contract_compact_patch = None
try:
    import app.world_integrity_pov_runtime_patch as world_integrity_patch  # noqa: F401
except Exception:
    world_integrity_patch = None

app.version = "0.3.51-balanced-scene-living-npc-v3"

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — strict Academy rich scene format
Use old Academy header/footer.
Add 🎥 POV line only if explicit POV mode is active.
Compact turn-contract is NOT permission to shorten visible scenes.
Keep Academy VN richness: sensory detail, micro-movements, pauses, banter, social pressure, consequence.
Never print raw player parenthetical action blocks; translate them into prose or short stage notes.
Energy is visually/physically felt when relevant.
Personal energy is in character cards, not separate per-type files.
"""
