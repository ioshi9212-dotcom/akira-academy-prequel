"""
Compact prompt preview builder for academy-prequel turn-contract.

This is not a user-visible scene.
It is an internal rendering brief that tells the GPT what to do after API/state/files
are loaded: output the scene, not the API/state/status.
"""

from __future__ import annotations

import json
from typing import Any

MAX_PROMPT_PREVIEW_CHARS = 10000


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
- Immediately after getSessionTurnContract and before any gameplay scene, load required files through the CHUNKED protocol:
  1) call getRequiredFilesManifest for this same session_id;
  2) call getRequiredFilesChunk from chunk_index=0;
  3) continue with next_chunk_index until has_more=false;
  4) treat all returned chunk loaded_files/parts as the actual loaded required file contents.
- Do NOT replace chunked loading with getProjectFile or only main.yaml files.
- Do NOT render from only main.yaml files if required_files also contains character.yaml, past.yaml, locks or state files.
- Output the gameplay scene only after required file chunks are loaded.
- Do NOT show API status, session status, current_state summary, file list, contract summary, setup explanation or prompt_preview.
- Do NOT ask permission to continue/render/start.
- If user wrote "начнем", "старт", "первая сцена", or gave an in-character action, that is already permission to render the scene.
- In technical/debug mode only, technical output is allowed.

PLAYER INPUT ANCHOR PROTOCOL:
- Everything the user writes outside parentheses is Akira's exact spoken line. Insert it as Akira's line; do not paraphrase, shorten, improve, or give it to another character.
- If the current player input contains no spoken text outside parentheses, do NOT create any new line in the scene body in the form **Акира** — ... / **Akira** — ... . Akira may act, pause, look, move, gesture, stay silent, or physically react only.
- Possible Akira lines that were not explicitly written by the player belong only in the bottom block "Что Акира могла бы сказать", never in the scene body.
- Everything inside parentheses is Akira's action, gesture, body state, intention, movement or inner pause. It is not speech and it is not an instruction for NPCs to obey automatically.
- If two Akira lines are separated by parenthetical action, treat that action as a pause. Fill the pause with world/NPC reaction, body movement, silence, glances, social pressure, rumor, atmosphere or distance changes.
- The scene must be built around Akira's player-provided lines as anchor points. Do not let NPC dialogue swallow Akira after the first line.
- Livia and Kir may comment, tease and cover pauses, but must not answer for Akira when an NPC addresses Akira directly.
- If an NPC asks Akira a direct question, throws a social jab, challenges her, names her, blocks her, or changes the power balance, stop and give the player the choice instead of auto-answering or moving past it.
- If the player said Akira moves somewhere, begin that movement, but do not skip over a meaningful direct hook addressed to Akira on the way.

VISIBLE SCENE BEFORE STATE / NO STATUS SUMMARY:
- In gameplay mode the final visible answer must be the gameplay scene, not a tool/status summary.
- First render the complete user-visible scene. Only after the scene text is ready may state changes be prepared/applied.
- apply-turn-result is a persistence step; it never replaces the visible scene.
- After apply-turn-result, the final answer must still be the scene with header/body/dialogue/bottom blocks.
- If apply-turn-result was called before a visible scene was shown, output a repair-render of the already-saved scene and do not apply state again.
- Forbidden as final gameplay answers: "Сцена отработана", "Ключевые моменты", "Следующая точка", "Если хочешь, могу отрендерить", or any equivalent status/offer replacing the scene.

RHYTHM CONTROL:
- Do not compress a saturated player turn into a recap.
- Do not expand a saturated player turn into a long NPC-only dialogue where Akira disappears.
- Good rhythm: Akira anchor -> 1-4 meaningful NPC/world reactions -> next Akira anchor or choice point.
- If 6-10 NPC lines pass without a new Akira anchor or a player choice, stop earlier.
- Stop at the first point where Akira can meaningfully choose: answer, ignore, turn back, let Livia/Kir cover, continue moving, or change tone.

CHARACTER FIDELITY:
- Characters must act strictly according to their loaded character files, current relationship state, knowledge_state, current mood, goals, limits and scene pressure.
- Do not smooth characters into generic friendly NPCs.
- Do not make characters say, feel, forgive, flirt, obey, explain or cooperate if their card/relationship/knowledge does not support it.
- If a planned line or reaction contradicts a loaded character file, relationship state or knowledge source, rewrite it before sending.
- A character can be quiet, evasive, wrong, rude, jealous, curious, scared, dismissive or resistant if that fits their profile and current context.

CURRENT STATE:
{_dump(_compact_current_state(current_state), 2000)}

FOCUS CHARACTERS:
active_character_ids: {active_ids}
nearby_character_ids: {nearby_ids}
focus_ids_for_this_turn: {focus_ids}

REQUIRED FILES TO LOAD BEFORE SCENE:
{_dump(required_files, 2200)}

REQUIRED FILE LOADING PROTOCOL:
- The list above is not enough by itself. It is only a manifest.
- Call getRequiredFilesManifest(session_id), then getRequiredFilesChunk(session_id, chunk_index=0), then next chunks until has_more=false.
- Use all returned chunks as the loaded required file contents before writing gameplay prose.
- If chunks were not loaded, do not invent missing character relationships from main.yaml only.

KNOWLEDGE TABLE:
{_dump(knowledge_table or turn_contract.get("knowledge_table", {}), 2200)}

RELATIONSHIP CONTEXT:
{_dump(_compact_relationships(relationships or {}, focus_ids), 1800)}

STORY / FUTURE CONTEXT:
story_lines_contract: {_dump(turn_contract.get("story_lines_contract", {}), 1200)}
canon_locks: {_dump(turn_contract.get("canon_locks", []), 1000)}

OUTPUT GATE:
A gameplay answer must include:
1. Scene header: short date, time, location, Akira state, visible items / atmosphere.
2. Full scene body, not recap/status/summary.
3. Akira player-input anchors inserted exactly as Akira's speech.
4. Parenthetical player actions rendered as action/pause/body/movement, not as speech.
5. NPC/world reaction that does not steal Akira's agency.
6. Dialogue in required format.
7. Character fidelity: every NPC line/reaction must fit loaded character files, relationships and knowledge sources.
8. At least one scene movement: plot, relationship, knowledge, conflict, reputation, body/energy state, rumor, schedule, open_thread or future hook.
9. Stop at a point where the player can answer if a direct hook to Akira appears.
10. Bottom block:
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
- rendering a scene after reading only 1-3 main.yaml files while required_files contains more files
- compressing the player's input into a short recap
- letting Livia/Kir answer a direct challenge addressed to Akira
- continuing 10+ NPC lines after Akira is directly challenged without giving the player a choice
- any API/debug/contract commentary
- "Сцена отработана" or any scene-complete status summary replacing the scene
- "Ключевые моменты" as the final gameplay response instead of a scene
- "Следующая точка" as a status line instead of a scene
- "Если хочешь, могу отрендерить" / offering to render instead of rendering
- creating a new Akira spoken line when the current player input contains no spoken text outside parentheses

SELF-CHECK BEFORE SENDING:
If header, full scene body, player input anchoring, NPC/world reaction, character fidelity, scene movement, or bottom block is missing,
rewrite silently before sending. Do not apologize inside gameplay.
If Akira disappears from a saturated dialogue, stop earlier and give a choice.
If the current player input contains no spoken text outside parentheses but the scene body contains an Akira dialogue line, rewrite it into physical action/silence and move possible phrases to the bottom block.
If an NPC direct challenge to Akira was auto-resolved, rewrite and stop at that choice point.
If the final output became a status/summary after apply-turn-result, rewrite as the visible gameplay scene.
If apply-turn-result was called before a visible scene was shown, output a repair-render of the already-saved event without applying state again.
""".strip()

    return _cut(brief, MAX_PROMPT_PREVIEW_CHARS)
