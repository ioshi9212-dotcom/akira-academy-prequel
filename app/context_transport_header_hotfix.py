"""Runtime header/footer hotfix v22.

Connects runtime layers:
- calendar/lore/cleanup/speed
- scene format
- state persistence
- POV switch
- compact turn-contract with balanced scene rules
- world integrity diagnostics
- one-call scene startup action
- stable Custom GPT Actions OpenAPI schema
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
try:
    import app.gpt_scene_startup_runtime_patch as gpt_scene_startup_patch  # noqa: F401,E402
except Exception:
    gpt_scene_startup_patch = None

app.version = "0.3.55-one-call-scene-startup"

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — strict Academy balanced scene format

Startup/tool loading rule:
In gameplay mode, never ask the user to provide starting conditions if tools/session data can be used.
Do not answer with "I cannot start blind" or "send location/time/state".
First use the current session and call the available session/context tools.
Required startup flow:
0. If beginSceneSetup is available, use it first for any start/continue command.
1. getSessionContext if available.
2. getSessionTurnContract.
3. getRequiredFilesManifest.
4. getRequiredFilesChunk from chunk_index=0 until has_more=false.
If getSessionContext is too large, continue with getSessionTurnContract + manifest + chunks instead of asking the user.
Only ask the user for session_id if no current session can be identified by available tools.
After data is loaded, output gameplay scene only.

Use the old Academy header fully. Do not shorten it into a tiny card.

Required visible header shape:
🏛️ Академия Астрейн · 1198 г., date/day
🕒 time · 📍 location
🎥 POV line only if explicit POV mode is active
🌦️ Weather/atmosphere line
⚙️ Active scene state
blank line
✦ visible POV/controlled-character state
🧥 outfit line if relevant/current_state supports it
◈ visible items/nearby items if relevant/current_state supports it
blank line
━━━━━━━━━━━━━━━━━━━━

Dialogue format is strict:
**Name or visible descriptor** — Speech. (*short remark*)

Never write dialogue as:
Name — Speech
without bold speaker name.

Descriptions are normal prose paragraphs.
Do not split prose into dramatic one-word or one-line fragments.
Do not stack empty micro-paragraphs for rhythm.
Use compact paragraphs of 1-4 sentences when possible.

Balanced scene rule:
Compact turn-contract DOES allow visible scenes to stay balanced and stop early.
Do not force rich/chapter-length scenes.
Do not keep expanding after Akira reaches a choice point.
Use 1-4 meaningful NPC/world reactions per Akira anchor, then stop or offer player choice.
If an NPC directly questions, challenges, provokes, blocks, names, or hooks Akira, stop after that hook and let the player answer.
If Akira is leaving/moving away, render only the immediate consequence and stop at the first meaningful threshold or interruption.

Living-space rule:
In public Academy spaces, 1-3 short ambient student/minor NPC reactions are allowed when useful.
They must stay brief and local; they must not steal agency or become long dialogue.

Player input rule:
Never print raw player parenthetical action blocks.
Parenthetical thoughts/motives/judgments are POV-only guidance.
NPCs must not read, answer, mirror, confirm or deny inner thoughts unless spoken aloud or visibly observable.

Energy is visually/physically felt only when relevant.
Personal energy is in character cards, not separate per-type files.
"""

# Keep this import last: it overrides app.openapi after all runtime routes are registered,
# so Custom GPT sees stable operationIds instead of FastAPI-generated names.
try:
    import app.gpt_actions_openapi_runtime_patch as gpt_actions_openapi_patch  # noqa: F401,E402
except Exception:
    gpt_actions_openapi_patch = None
