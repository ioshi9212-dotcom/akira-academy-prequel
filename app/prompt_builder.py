"""
Compact prompt preview builder for academy-prequel turn-contract.

This is not a user-visible scene.
It is an internal rendering brief that tells the GPT what to do after API/state/files
are loaded: output the scene, not the API/state/status.
"""

from __future__ import annotations

import json
import re
from typing import Any

MAX_PROMPT_PREVIEW_CHARS = 9000


def _cut(text: Any, limit: int = 700) -> str:
    if text is None:
        return ""
    value = str(text).strip()
    return value if len(value) <= limit else value[:limit].rstrip() + "..."


def _dump(value: Any, limit: int = 2200) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except Exception:
        text = str(value)
    return _cut(text, limit)


def _pov_target_from_text(text: Any) -> str | None:
    value = str(text or "").strip()
    low = value.lower().replace("ё", "е")
    if not re.search(r"\b(pov|пов)\s*[:：]", low):
        return None
    match = re.search(r"(?:pov|пов)\s*[:：]\s*([А-Яа-яA-Za-z_\-]+)", value, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).strip()
    key = raw.lower().replace("ё", "е")
    if key in {"акира", "akira"}:
        return None
    return raw or None


def _pov_override_text(current: dict[str, Any]) -> str:
    target = _pov_target_from_text(current.get("last_player_input")) or _pov_target_from_text(current.get("current_scene_goal"))
    if not target:
        return ""
    return f"""
NON-AKIRA POV OVERRIDE:
- Active POV target: {target}.
- For this response, player's outside-parentheses text is the POV character's exact speech, not Akira's.
- Player's parenthetical text is the POV character's action/body state/intention, not Akira's.
- Akira may still speak and act as an active NPC if she is present.
- If the POV character addresses Akira, Akira may answer/refuse/interrupt/move/leave according to her character and visible state.
- If Akira addresses/challenges/questions the POV character and waits for an answer, stop for player choice unless the player already wrote the POV character's answer/action.
- Do not write Akira's hidden thoughts in non-Akira POV; show only visible speech/action/reaction.
""".strip()


def _compact_current_state(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": current.get("current_date"),
        "time": current.get("current_time"),
        "location_id": current.get("current_location_id"),
        "location_text": current.get("current_location_text"),
        "scene_goal": current.get("current_scene_goal"),
        "akira_behavior_profile": current.get("akira_behavior_profile"),
        "akira_state": current.get("akira_state"),
        "current_outfit": current.get("current_outfit"),
        "uniform_worn": current.get("uniform_worn"),
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "active_characters": current.get("active_characters", []),
        "nearby_characters": current.get("nearby_characters", []),
        "scheduled_character_ids": current.get("scheduled_character_ids", []),
        "mentioned_character_ids": current.get("mentioned_character_ids", []),
        "delayed_character_ids": current.get("delayed_character_ids", []),
        "last_player_input": current.get("last_player_input"),
    }


def _compact_relationships(relationships: dict[str, Any], focus_ids: list[str]) -> dict[str, Any]:
    if not isinstance(relationships, dict):
        return {}
    pairs = relationships.get("pairs")
    if not isinstance(pairs, dict):
        return {}
    focus = set(focus_ids or [])
    result: dict[str, Any] = {}
    for pair_id, data in pairs.items():
        if not isinstance(pair_id, str) or "__" not in pair_id:
            continue
        left, right = pair_id.split("__", 1)
        if left not in focus or right not in focus:
            continue
        if isinstance(data, dict):
            result[pair_id] = {
                "status": data.get("status"),
                "affection": data.get("affection"),
                "trust": data.get("trust"),
                "tension": data.get("tension"),
                "jealousy": data.get("jealousy"),
                "respect": data.get("respect"),
                "curiosity": data.get("curiosity"),
                "resentment": data.get("resentment"),
                "notes": (data.get("notes") or [])[-3:] if isinstance(data.get("notes"), list) else data.get("notes"),
                "open_threads": (data.get("open_threads") or [])[-3:] if isinstance(data.get("open_threads"), list) else data.get("open_threads"),
                "behavior_next": (data.get("behavior_next") or [])[-3:] if isinstance(data.get("behavior_next"), list) else data.get("behavior_next"),
            }
    return result


def build_prompt_preview(
    *,
    session_id: str,
    current_state: dict[str, Any],
    turn_contract: dict[str, Any],
    required_files: list[str],
    knowledge_table: dict[str, Any] | None = None,
    relationships: dict[str, Any] | None = None,
    story_lines: dict[str, Any] | None = None,
    future_locks: dict[str, Any] | None = None,
) -> str:
    active_ids = list(turn_contract.get("active_character_ids", []) or [])
    nearby_ids = list(turn_contract.get("nearby_character_ids", []) or [])
    focus_ids: list[str] = []
    for item in ["akira"] + active_ids + nearby_ids:
        if item and item not in focus_ids:
            focus_ids.append(item)

    pov_override = _pov_override_text(current_state)

    brief = f"""
PLAY MODE RENDER BRIEF
session_id: {session_id}

TASK:
- Use this contract and required_files internally.
- Immediately after getSessionTurnContract and before any gameplay scene, load required files through the CHUNKED protocol.
- Do NOT replace chunked loading with getProjectFile or only main.yaml files.
- Output the gameplay scene only after required file chunks are loaded.
- Do NOT show API status, session status, current_state summary, file list, contract summary, setup explanation or prompt_preview.

{pov_override}

SOURCE SYSTEM:
- Default mode: player's latest visible speech/action anchors Akira. If NON-AKIRA POV OVERRIDE is present above, it overrides this line for the current response.
- Latest visible scene facts override stale object positions and old suggested options.
- Character behavior comes from characters/{{id}}/character.yaml, past.yaml and main.yaml if present.
- Calendar comes from calendar/calendar_index.yaml, calendar/days/{{current_date}}.yaml and state/calendar_runtime.json.
- Lore comes from canon_lore/ and lore slice.
- Hidden lore is author/engine knowledge, not automatic NPC knowledge.
- Akira unspoken text is only scene-director context for her own tension/intent; it is not world knowledge and does not trigger convenient scene events.

CANON IDENTITY BOUNDARY:
- Random/unnamed/session NPCs and fixed canon characters are different layers.
- Do not rename an invented or unnamed NPC into an existing fixed character after that NPC has already been described.
- Do not attach a fixed character name to an NPC if appearance, role, course/year, energy, relationships, location, timing or behavior contradicts that character's card.
- A fixed named character may enter only if current roster, calendar/current day, scheduled/delayed state, explicit player action, or already played setup allows it.
- If unsure whether a person is a fixed character, keep them unnamed/background and do not use a canon name.

WITNESS / KNOWLEDGE BOUNDARY:
- Characters know only what they saw, heard, were told, or can plausibly infer from visible signs.
- A delayed/absent/off-screen/not-yet-introduced character must not reference a previous scene as if they witnessed it.
- If a character arrives late, they know only what happened after arrival unless someone tells them on-screen or knowledge_state says they know.
- If they need to refer to someone from an unobserved scene, use uncertainty: "тот парень?", "тот рыжий?", "о ком вы?", "я что-то пропустил?".
- When the player brings in a delayed character, use their card from that point onward, but do not grant retroactive knowledge.

PLAYER INPUT ANCHOR PROTOCOL:
- Default Akira POV: everything the user writes outside parentheses is Akira's exact spoken line. Insert it as Akira's line.
- Default Akira POV: if the current player input contains no spoken text outside parentheses, do NOT create any new Akira dialogue lines in the scene body.
- Default Akira POV: everything inside parentheses is Akira's action, gesture, body state, intention, movement or inner pause. It is not speech and not an instruction for NPCs or scene systems to obey automatically.
- Non-Akira POV: if NON-AKIRA POV OVERRIDE is present, the same speech/action rules apply to the POV character instead of Akira.
- Non-Akira POV: Akira is an active NPC if present and may answer, refuse, interrupt, move, leave or follow her own plan according to her character/state.
- Non-Akira POV: do not stop only because the POV character addressed Akira; Akira can answer as NPC. Stop when Akira addresses/challenges/questions the POV character and the player must choose the POV character's response.
- Default Akira POV: if an NPC asks Akira a direct question, throws a social jab, challenges her, names her, blocks her, or changes the power balance, stop and give the player the choice instead of auto-answering.

VISIBLE-SOURCE RULE:
- NPCs, staff, crowd, procedures and scene events can react only to visible signs, spoken words, established knowledge, procedure, relationship state or prior visible facts.
- Do not make the scene answer, solve, mirror or cancel Akira's unspoken worry/plan/priority unless there is a visible source.
- Characters may notice a pause, glance, guarded gesture, silence, delayed answer, changed posture or tension; their conclusions may be wrong or incomplete.

RHYTHM CONTROL:
- Good rhythm: Akira anchor -> 1-4 meaningful NPC/world reactions -> next Akira anchor or choice point.
- If 6 or more NPC lines pass without a new Akira anchor or a player choice, stop earlier.
- If Akira is leaving and an NPC throws a hook at her back, stop on that hook unless the player explicitly wrote that she ignores it.

CHARACTER FIDELITY:
- Characters must act strictly according to loaded character files, current relationship state, knowledge_state, current mood, goals, limits and scene pressure.
- If a planned line or reaction contradicts a loaded character file, relationship state, knowledge source, canon identity boundary or witness boundary, rewrite it before sending.

CURRENT STATE:
{_dump(_compact_current_state(current_state), 1800)}

FOCUS CHARACTERS:
active_character_ids: {active_ids}
nearby_character_ids: {nearby_ids}
focus_ids_for_relationships: {focus_ids}

REQUIRED FILES TO LOAD BEFORE SCENE:
{_dump(required_files, 1800)}

KNOWLEDGE TABLE:
{_dump(knowledge_table or turn_contract.get('knowledge_table', {{}}), 1400)}

RELATIONSHIP CONTEXT:
{_dump(_compact_relationships(relationships or {{}}, focus_ids), 1200)}

OUTPUT GATE:
A gameplay answer must include:
1. Scene header.
2. Full scene body.
3. Akira player-input anchors inserted exactly as Akira's speech.
4. Character fidelity.
5. Visible-source fidelity.
6. Canon identity fidelity.
7. Witness/knowledge fidelity.
8. Bottom block: Что можно сделать / Что Акира могла бы сказать / Мысли Акиры.

FORBIDDEN FINAL OUTPUT IN PLAY MODE:
- API/debug/contract commentary.
- Renaming a described invented NPC into a fixed canon character.
- Letting absent/delayed characters know scenes they missed.
- Letting NPCs/staff/procedure react as if Akira's unspoken text was spoken or visible.
"""
    return brief[:MAX_PROMPT_PREVIEW_CHARS]
