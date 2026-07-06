from __future__ import annotations

import json
from typing import Any

MAX_PROMPT_PREVIEW_CHARS = 8000


def _cut(text: Any, limit: int = 2000) -> str:
    value = "" if text is None else str(text).strip()
    return value if len(value) <= limit else value[:limit].rstrip() + "..."


def _dump(value: Any, limit: int = 2500) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except Exception:
        text = str(value)
    return _cut(text, limit)


def build_prompt_preview(scene_packet: dict[str, Any]) -> str:
    """Build a compact GPT rendering brief.

    Borrowed from the old working Academy idea: preserve POV anchors, NPC/world rhythm,
    fidelity checks, and output gate. Removed old global locks and legacy knowledge/relationship files.
    """
    current = scene_packet.get("current_frame", {})
    player = scene_packet.get("player_input", {})
    loaded = scene_packet.get("loaded_files", {})
    required = scene_packet.get("required_files", [])

    scene_core = loaded.get("rules/scene_core.md", "")

    character_files = {
        path: content
        for path, content in loaded.items()
        if path.startswith("characters/") and path.endswith("/main.yaml")
    }
    memory_files = {
        path: content
        for path, content in loaded.items()
        if path.startswith("state/character_memory/")
    }
    relationship_files = {
        path: content
        for path, content in loaded.items()
        if path.startswith("state/relationship_pairs/")
    }
    location_files = {
        path: content
        for path, content in loaded.items()
        if path.startswith("locations/") and path.endswith(".yaml")
    }
    calendar_files = {
        path: content
        for path, content in loaded.items()
        if path.startswith("calendar/days/")
    }
    state_files = {
        path: content
        for path, content in loaded.items()
        if path.startswith("state/") and path not in memory_files and path not in relationship_files
    }

    brief = f"""
ACADEMY 1198 SCENE RENDER BRIEF

ROLE SPLIT:
- Railway/API has already assembled the scene packet and loaded files internally.
- GPT renders the scene from this packet only.
- Do not search for extra gameplay files during normal play.
- Do not invent exact room, floor, route, group, schedule, procedure result, or staff decision.

PACKET STATUS:
{scene_packet.get("packet_status")}

RENDERED HEADER:
{scene_packet.get("rendered_header")}

PLAYER INPUT SEGMENTS, ORIGINAL ORDER:
{_dump(player, 1200)}

CURRENT FRAME:
{_dump(current, 1400)}

SCENE CORE RULES:
{_cut(scene_core, 1800)}

LOADED CALENDAR:
{_dump(calendar_files, 1200)}

LOADED LOCATION:
{_dump(location_files, 1400)}

LOADED CHARACTER CARDS:
{_dump(character_files, 3000)}

LOADED CHARACTER MEMORY:
{_dump(memory_files, 1200)}

LOADED RELATIONSHIP PAIRS:
{_dump(relationship_files, 1600)}

LOADED CONDITIONAL STATE:
{_dump(state_files, 1200)}

REQUIRED FILES:
{_dump(required, 1000)}

RHYTHM RULES FROM OLD WORKING ACADEMY, KEPT COMPACT:
- Player outside-parentheses text is exact POV speech.
- Player parenthetical text is POV action/body state/intention/thought/pause.
- Keep input segment order. Do not merge speech across parentheticals.
- If the player gives movement, waiting, following, routine transition, or a chain of actions, resolve to the nearest meaningful point: line, interruption, procedure result, social pressure, visible consequence, or choice.
- Do not split harmless movement into empty micro-turns.
- Do not choose a new major goal, answer, consent, attack, trust shift, time skip, or unrelated location for the player-controlled character.
- The world does not freeze when the POV is silent; NPCs act from their loaded character, knowledge, relationship, role, status, and visible pressure.
- Good rhythm: POV anchor -> 1-4 meaningful NPC/world reactions -> nearest meaningful beat or choice point.
- If many NPC lines pass without a new player anchor or player choice, stop earlier.
- If the player-controlled character is leaving and someone throws a meaningful hook at their back, stop on that hook unless the player explicitly wrote that they ignore it.

CHARACTER FIDELITY:
- Characters must act according to loaded character files, loaded memories, relationship files, visible state, goals, limits and scene pressure.
- If a planned line/reaction contradicts a loaded card, relationship, knowledge boundary, location, or current state, rewrite before sending.
- If a character is reference-only and not full-loaded, do not give them meaningful new dialogue/action.

BOTTOM UI FORMAT:
- Use max 3 bottom blocks total, and max 3 bullet/lines inside each block.
- Allowed bottom blocks only: `✦ Что можно сделать`, `✦ Уровни`, `✦ Отношения`.
- Do not output `✦ Что Акира могла бы сказать` unless explicitly requested.
- `✦ Что можно сделать`: max 3 action options, no exact dialogue suggestions.
- `✦ Уровни`: max 3 compact lines; use only active values/states supported by loaded/current state. Allowed subjects: Сумка, Внимание, Энергия, Усталость, Риск, Позиция.
- `✦ Отношения`: only if relationship pair file is loaded. Use numeric `surface_dynamic` values only. Preferred line: `Акира ↔ Ливия: привязанность 18 · доверие 14 · напряжение 0`.
- Never write `Акира ↔ Ливия: без изменений` or `Без изменений` in relationships when a pair file is loaded.

OUTPUT GATE:
1. The rendered header exactly.
2. Scene body.
3. Player-input anchors inserted as POV speech/action in original order.
4. Character fidelity.
5. Visible-source fidelity.
6. Witness/knowledge fidelity.
7. Bottom UI follows the max-three numeric format above.

FORBIDDEN FINAL OUTPUT IN PLAY MODE:
- API/debug/contract commentary.
- Renaming a described invented NPC into a fixed canon character.
- Letting absent/delayed/reference characters know or act on scenes they missed.
- Letting NPCs/staff/procedure react as if the POV's unspoken thoughts were spoken or visible.
"""
    return brief[:MAX_PROMPT_PREVIEW_CHARS]
