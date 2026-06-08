"""
Compact prompt preview builder for academy-prequel turn-contract.

This is not a user-visible scene.
It is an internal rendering brief that tells the GPT what to do after API/state/files
are loaded: output the scene, not the API/state/status.
"""

from __future__ import annotations

import json
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


def _compact_current_state(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": current.get("current_date"),
        "time": current.get("current_time"),
        "location_id": current.get("current_location_id"),
        "location_text": current.get("current_location_text"),
        "scene_goal": current.get("current_scene_goal"),
        "akira_behavior_profile": current.get("akira_behavior_profile"),
        "akira_state": current.get("akira_state"),
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "active_characters": current.get("active_characters", []),
        "nearby_characters": current.get("nearby_characters", []),
        "scheduled_character_ids": current.get("scheduled_character_ids", []),
        "mentioned_character_ids": current.get("mentioned_character_ids", []),
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
        if left not in focus and right not in focus:
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
                "notes": (data.get("notes") or [])[-5:] if isinstance(data.get("notes"), list) else data.get("notes"),
                "open_threads": (data.get("open_threads") or [])[-5:] if isinstance(data.get("open_threads"), list) else data.get("open_threads"),
                "behavior_next": (data.get("behavior_next") or [])[-5:] if isinstance(data.get("behavior_next"), list) else data.get("behavior_next"),
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
    focus_ids = []
    for item in ["akira"] + active_ids + nearby_ids + list(current_state.get("scheduled_character_ids", []) or []):
        if item and item not in focus_ids:
            focus_ids.append(item)

    brief = f"""
PLAY MODE RENDER BRIEF
session_id: {session_id}

TASK:
- Use this contract and required_files internally.
- Output the gameplay scene immediately.
- Do NOT show API status, session status, current_state summary, file list, contract summary, setup explanation or prompt_preview.
- Do NOT ask permission to continue/render/start.
- If user wrote "начнем", "старт", "первая сцена", or gave an in-character action, that is already permission to render the scene.
- In technical/debug mode only, technical output is allowed.

CHARACTER FIDELITY:
- Characters must act strictly according to their loaded character files, current relationship state, knowledge_state, current mood, goals, limits and scene pressure.
- Do not smooth characters into generic friendly NPCs.
- Do not make characters say, feel, forgive, flirt, obey, explain or cooperate if their card/relationship/knowledge does not support it.
- If a planned line or reaction contradicts a loaded character file, relationship state or knowledge source, rewrite it before sending.
- A character can be quiet, evasive, wrong, rude, jealous, curious, scared, dismissive or resistant if that fits their profile and current context.

CURRENT STATE:
{_dump(_compact_current_state(current_state), 1800)}

FOCUS CHARACTERS:
active_character_ids: {active_ids}
nearby_character_ids: {nearby_ids}
focus_ids_for_this_turn: {focus_ids}

REQUIRED FILES TO USE INTERNALLY:
{_dump(required_files, 2200)}

KNOWLEDGE TABLE:
{_dump(knowledge_table or turn_contract.get("knowledge_table", {}), 2200)}

RELATIONSHIP CONTEXT:
{_dump(_compact_relationships(relationships or {}, focus_ids), 1800)}

STORY / FUTURE CONTEXT:
story_lines_contract: {_dump(turn_contract.get("story_lines_contract", {}), 1200)}
canon_locks: {_dump(turn_contract.get("canon_locks", []), 1000)}

OUTPUT GATE:
A gameplay answer must include:
1. Scene header: date, time, location, Akira state, visible items / atmosphere.
2. Full scene body, not recap/status/summary.
3. NPC/world reaction.
4. Dialogue in required format.
5. Character fidelity: every NPC line/reaction must fit loaded character files, relationships and knowledge sources.
6. At least one scene movement: plot, relationship, knowledge, conflict, reputation, body/energy state, rumor, schedule, open_thread or future hook.
7. Bottom block:
   - Что можно сделать:
   - Что Акира могла бы сказать:
   - Мысли Акиры:

FORBIDDEN FINAL OUTPUT IN PLAY MODE:
- "Сессия создана"
- "Контракт собран"
- "API вернул"
- "Я загрузил"
- "Хочешь продолжить?"
- "Могу разыграть сцену?"
- "Это внутреннее состояние игры"
- generic character behavior that ignores loaded character files
- any API/debug/contract commentary

SELF-CHECK BEFORE SENDING:
If header, full scene body, NPC/world reaction, character fidelity, scene movement, or bottom block is missing,
rewrite silently before sending. Do not apologize inside gameplay.
""".strip()

    return _cut(brief, MAX_PROMPT_PREVIEW_CHARS)
