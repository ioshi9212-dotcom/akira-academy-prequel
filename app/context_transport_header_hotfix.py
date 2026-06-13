"""
Runtime header/footer hotfix v15.

Active import order:
1. calendar_context_runtime_patch
2. lore_context_runtime_patch
3. context_cleanup_runtime_patch
4. runtime_speed_patch

Server entry remains:
    app/server.py -> from app.context_transport_header_hotfix import app
"""

from __future__ import annotations

try:
    import app.calendar_context_runtime_patch as calendar_patch  # noqa: F401
except Exception:
    calendar_patch = None  # noqa: N816

try:
    import app.lore_context_runtime_patch as lore_patch  # noqa: F401
except Exception:
    lore_patch = None  # noqa: N816

try:
    import app.context_cleanup_runtime_patch as cleanup_patch  # noqa: F401
except Exception:
    cleanup_patch = None  # noqa: N816

import app.runtime_speed_patch as speed_patch  # noqa: F401

import app.context_transport_runtime_patch as rt
from app.runtime_speed_patch import app

app.version = "0.3.34-speed-header-v15"

# Old individual locks are intentionally not appended here.
# Required files should use only:
# - runtime/scene_context_digest.md
# - gpt/locks/runtime_scene_rules_digest.md
# - characters/character_id_index.md
# - active character YAML files

rt.MINIMAL_LOCK_FILES = ["gpt/locks/runtime_scene_rules_digest.md"]

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — selected header/footer format

Use compact visual header and visual-novel prose.

Scene header:
- Start with compact visual header.
- Do not show hidden lore, hidden NPCs, future calendar events or API/debug fields.
- Weather/location/items must reflect current_state.
- If uniform_worn=false, do not write Academy uniform as worn clothing.
- If phone is inside baggage, do not write phone as carried/visible.

Required feel:
- Continue with living visual-novel prose after the header.
- Do not write the scene as a technical card/table/form.
- Keep the world moving: every scene needs a concrete hook, reaction, social pressure, small conflict, consequence or transition.
- NPCs must act from loaded character files, relationship slice, calendar slice, lore slice and knowledge slice.
"""
