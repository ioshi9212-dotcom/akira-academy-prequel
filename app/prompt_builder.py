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

    Keep hard gameplay/render rules before long loaded content so they cannot be
    cut off by MAX_PROMPT_PREVIEW_CHARS.
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

CRITICAL POV / PARENTHETICAL RULES:
- Text outside parentheses is exact spoken POV dialogue.
- Text inside parentheses is private POV action/body state/intention/thought. Parenthetical text is NOT spoken.
- NPCs must never know, quote, answer, paraphrase, or directly react to private parenthetical thoughts.
- NPCs may react only to visible signs from parentheticals: gaze direction, pause, facial shift, posture, movement, object handling, silence, hesitation, breathing, or energy/body manifestations.
- NPCs may make imperfect guesses from visible signs, but never a 100% correct read of the thought and never the same wording.
- Example: if POV thinks `(Рэй вообще снимает форму? или спит в ней)`, Ray must NOT answer about sleeping in uniform. He may only notice a look/pause and ask something vague or ignore it.

CRITICAL AKIRA SPEECH:
- Akira speaks short, dry, poisonous-calm, and rarely explains herself.
- If an Akira line sounds neutral/safe/ordinary, rewrite it sharper, drier, and slightly more poisonous.
- Do not make Akira friendly-explanatory, chatty, soft, or generically sarcastic.
- Use loaded `characters/akira/main.yaml` speech_profile for all Akira dialogue and suggested lines.

CRITICAL ROUTE RULES:
- The Academy back entrance path is linear: arrival/dropoff -> back court route -> basketball court/sports площадки -> registration.
- Do NOT offer an alternate choice like "свернуть вниманием к боковому маршруту" if the route already goes through the court.
- Do NOT offer "пойти по официальному маршруту к регистрации" as if it bypasses the court. Registration is after the court path.

CRITICAL BOTTOM UI FORMAT:
- Bottom UI may include: `✦ Что можно сделать`, `✦ Что <POV> могла бы сказать`, `✦ Мысли <POV>`, `✦ Уровни`, `✦ Отношения`.
- In actions, phrases, and thoughts: max 3 items each.
- `✦ Что можно сделать` must include exactly: `Варианты ниже не считаются действием, пока игрок не выбрал.`
- Action options start with `◈` and must be ACTIONS ONLY: movement, posture, observation, object handling, pause, route, attention.
- FORBIDDEN in action options: `сказать`, `ответить`, `спросить`, `позвать`, `предложить`, `пошутить`, exact dialogue, or dialogue intent.
- `✦ Что <POV> могла бы сказать`: exact speech lines only, max 3, strict POV character/goals, no spoilers.
- `✦ Мысли <POV>`: POV-local hints only, max 3, only what POV sees/feels/notices/suspects; no hidden lore or future facts.
- `✦ Уровни`: use compact rows. Preferred start format: `Физика: 40/100 · выносливость: 35/100 · усталость: 15/100` and `Энергия: доступ 10/100 · контроль 8/100 · риск: низкий` when supported.
- `✦ Отношения`: only characters in current scene with loaded pair file. Use `surface_dynamic.display_score` and `display_label`: `Ливия: +53 · старые подруги`. Never write `без изменений` or pair metrics.

PLAYER INPUT SEGMENTS, ORIGINAL ORDER:
{_dump(player, 1000)}

CURRENT FRAME:
{_dump(current, 1200)}

SCENE CORE RULES:
{_cut(scene_core, 2400)}

LOADED RELATIONSHIP PAIRS:
{_dump(relationship_files, 1200)}

LOADED CALENDAR:
{_dump(calendar_files, 1100)}

LOADED LOCATION:
{_dump(location_files, 1100)}

LOADED CHARACTER CARDS:
{_dump(character_files, 2200)}

LOADED CHARACTER MEMORY:
{_dump(memory_files, 900)}

LOADED CONDITIONAL STATE:
{_dump(state_files, 900)}

REQUIRED FILES:
{_dump(required, 800)}

RHYTHM RULES FROM OLD WORKING ACADEMY, KEPT COMPACT:
- Keep input segment order. Do not merge speech across parentheticals.
- If the player gives movement, waiting, following, routine transition, or a chain of actions, resolve to the nearest meaningful point: line, interruption, procedure result, social pressure, visible consequence, or choice.
- Do not split harmless movement into empty micro-turns.
- Do not choose a new major goal, answer, consent, attack, trust shift, time skip, or unrelated location for the player-controlled character.
- The world does not freeze when the POV is silent; NPCs act from loaded character, knowledge, relationship, role, status, visible pressure, and visible POV signs only.
- Good rhythm: POV anchor -> 1-4 meaningful NPC/world reactions -> nearest meaningful beat or choice point.
- If many NPC lines pass without a new player anchor or player choice, stop earlier.
- If the player-controlled character is leaving and someone throws a meaningful hook at their back, stop on that hook unless the player explicitly wrote that they ignore it.

CHARACTER FIDELITY:
- Characters must act according to loaded character files, loaded memories, relationship files, visible state, goals, limits and scene pressure.
- If a planned line/reaction contradicts a loaded card, relationship, knowledge boundary, location, or current state, rewrite before sending.
- If a character is reference-only and not full-loaded, do not give them meaningful new dialogue/action.

OUTPUT GATE:
1. The rendered header exactly.
2. Scene body.
3. Player-input anchors inserted as POV speech/action in original order.
4. Parenthetical privacy: NPCs do not read or answer thoughts.
5. Akira poisonous speech fidelity.
6. Visible-source fidelity.
7. Witness/knowledge fidelity.
8. Bottom UI follows the critical action/speech/thought/levels/relationship format above.

FORBIDDEN FINAL OUTPUT IN PLAY MODE:
- API/debug/contract commentary.
- Renaming a described invented NPC into a fixed canon character.
- Letting absent/delayed/reference characters know or act on scenes they missed.
- Letting NPCs/staff/procedure react as if the POV's unspoken thoughts were spoken or visible.
"""
    return brief[:MAX_PROMPT_PREVIEW_CHARS]
