from __future__ import annotations

import json
from typing import Any

import yaml

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


def _load_yaml_text(text: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _first_text(value: Any, max_len: int = 150) -> str:
    if isinstance(value, list):
        value = "; ".join(str(x).strip() for x in value if str(x).strip())
    elif isinstance(value, dict):
        value = "; ".join(f"{k}:{v}" for k, v in value.items())
    value = str(value or "").strip()
    return value[:max_len].rstrip()


def _character_brief_from_yaml(path: str, text: str) -> str:
    data = _load_yaml_text(text)
    if not data:
        return f"{path}: unreadable"

    cid = str(data.get("slug") or data.get("id") or path).replace("char_", "")
    display = data.get("display") or {}
    appearance = data.get("appearance") or {}
    speech = data.get("speech_profile") or {}

    known = display.get("known_name") or (data.get("name") or {}).get("first") or cid
    unknown = display.get("unknown_name") or display.get("unknown_formal") or known
    overall = _first_text(appearance.get("overall"), 120)
    hair = _first_text((appearance.get("hair") or {}).get("color") if isinstance(appearance.get("hair"), dict) else appearance.get("hair"), 80)
    voice_label = speech.get("label") or ""
    voice_core = _first_text(speech.get("core"), 170)

    hard = []
    hard.extend(appearance.get("forbidden") or [])
    hard.extend(speech.get("forbidden_speech") or [])
    forbidden = _first_text(hard, 170)

    return (
        f"- {cid}: known={known}; unknown={unknown}; "
        f"appearance={overall}; hair={hair}; "
        f"voice={voice_label}: {voice_core}; forbidden={forbidden}"
    )


def _character_briefs(character_files: dict[str, str]) -> str:
    return "\n".join(_character_brief_from_yaml(path, text) for path, text in sorted(character_files.items()))


def build_prompt_preview(scene_packet: dict[str, Any]) -> str:
    """Build a compact render brief.

    Full file contents are retrieved through required-files-chunk. This preview
    carries only critical non-negotiable rules and compact character anchors.
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
        if path.startswith("state/") and "character_memory" not in path and "relationship_pairs" not in path
    }

    brief = f"""
ACADEMY 1198 RENDER BRIEF

CHUNK PROTOCOL REQUIRED:
- scene_packet/prompt_preview is not enough for gameplay rendering.
- Before writing a gameplay scene, load every required file through `/required-files-chunk`.
- Keep calling chunks with next_chunk_index until has_more=false.
- If required chunks were not loaded, do not write gameplay prose; return a technical missing-context message.
- Never substitute guesses for unloaded full character cards, location slices, calendar beat, or relationship files.

ROLE SPLIT:
- Railway/API assembles scene_packet and required_files.
- GPT renders only from scene_packet plus loaded required chunks.
- applyTurnResult must save only explicit structured state changes. Do not infer state from prose.

PACKET STATUS:
{scene_packet.get("packet_status")}

RENDERED HEADER:
{scene_packet.get("rendered_header")}

CHARACTER ANCHORS FROM LOADED FULL CARDS:
{_character_briefs(character_files)}

POV / PARENTHETICAL PRIVACY:
- Outside parentheses = exact spoken POV dialogue.
- Inside parentheses = private POV action/body state/intention/thought, not spoken.
- NPCs never know, quote, answer, paraphrase, or directly react to private parenthetical thoughts.
- NPCs may react only to visible signs: gaze, pause, posture, movement, silence, object handling, body/energy manifestation.
- NPC guesses must be imperfect and based on visible signs only.

DIALOGUE TURN-TAKING:
- If a full-loaded character is directly addressed by speech/question/taunt/offer/accusation/visible challenge, give them a response beat before the same speaker continues pressing them.
- Response beat may be a verbal reply, visible refusal, gesture, action, interruption by another active character, or intentional silence that changes scene pressure.
- Do not let one NPC talk at another full-loaded NPC for multiple consecutive lines while the addressed NPC only stares/holds an object.
- If the player allowed another character to speak for the POV, that character may answer, but the addressed NPC still reacts to that answer.

ROUTE:
- 15 August route is linear: arrival/dropoff -> back court route -> basketball court/sports area -> registration.
- Do not offer a side route or a registration bypass when the route already passes the court.
- Haru and Raiden are at the court only when the court/sports area is visible or reached.
- If one of the court pair is full-visible, keep both anchored: Haru is red-haired; Raiden is dark-haired.

SCENE MOTION AND BACKGROUND NPCS:
- Academy is alive; NPCs act from role, duty, curiosity, pressure, schedule, habit, and visible scene facts.
- In public locations, add short background motion when pressure changes: whispers, side comments, laughs, someone moving aside, someone calling from a bench, staff/students reacting.
- Background beats must be brief and relevant; they do not replace full-loaded character responses.
- Compress routine movement/procedures to the next meaningful point.
- Stop for meaningful NPC questions, blocked path, risk, important information, new important character, consent/refusal, disclosure, conflict, or control choice.
- Do not stop for empty continuation choices when nothing changed.

BOTTOM UI:
- Use only useful blocks: `✦ Что можно сделать`, `✦ Что <POV> могла бы сказать`, `✦ Мысли <POV>`, `✦ Уровни`, `✦ Отношения`.
- Max 3 items in actions, speech, and thoughts.
- Actions are physical/attention/movement/object/pause/route/observation/posture only.
- No speech verbs in actions: no сказать, ответить, спросить, позвать, предложить, пошутить.
- Speech block contains exact possible spoken lines only.
- Thoughts are POV-local only and invisible to NPCs.
- Levels use loaded numeric state when available.
- Relationships show only loaded scene relationships; no absent characters, no `без изменений`.

PLAYER INPUT SEGMENTS:
{_dump(player, 900)}

CURRENT FRAME:
{_dump(current, 1000)}

COMPACT SCENE CORE:
{_cut(scene_core, 1200)}

CALENDAR / LOCATION / STATE DIGEST:
calendar={_dump(calendar_files, 700)}
location={_dump(location_files, 700)}
state={_dump(state_files, 650)}
relationships={_dump(relationship_files, 700)}

REQUIRED FILES:
{_dump(required, 800)}

OUTPUT GATE:
1. Use rendered_header exactly.
2. Preserve player input order.
3. Respect loaded character anchors and speech profiles.
4. If a full-loaded NPC is addressed, resolve their response beat or meaningful silence.
5. Add brief public-background motion when the location pressure calls for it.
6. Keep NPC knowledge visible-source only.
7. Keep scene moving to meaningful beats.
8. Do not output API/debug commentary in play mode.
"""
    return brief[:MAX_PROMPT_PREVIEW_CHARS]
