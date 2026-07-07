from __future__ import annotations

import json
from typing import Any

import yaml

MAX_PROMPT_PREVIEW_CHARS = 9000


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
    """Build a compact render brief in canonical processing order.

    Full file contents are retrieved through required-files-chunk. This preview
    summarizes rule blocks in logical order; earlier blocks are not more
    important than later blocks.
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

ORDER NOTE:
- Blocks follow scene-processing order, not priority order.
- Every block is required. Earlier does not mean more important.
- Do not create priority hacks or duplicate rule layers.

1) CONTEXT ASSEMBLY
- Railway/API builds scene_packet and required_files.
- prompt_preview alone is not enough for gameplay.
- Load required files through /required-files-chunk until has_more=false.
- If chunks are missing, stop with a short technical missing-context message.
- applyTurnResult saves only explicit structured changes, never inferred prose/UI options.

2) PACKET STATUS AND HEADER
packet_status={scene_packet.get("packet_status")}
rendered_header={scene_packet.get("rendered_header")}

3) PLAYER INPUT / POV PRIVACY
{_dump(player, 600)}
- Outside parentheses = exact spoken POV dialogue; preserve it literally.
- Inside parentheses = private POV action/body/intention/thought, not spoken.
- Preserve input segment order.
- NPCs react only to visible signs and known facts, never to private thoughts.

4) CURRENT FRAME
{_dump(current, 600)}

5) LOADED CHARACTER ANCHORS
{_cut(_character_briefs(character_files), 1200)}
- Use loaded unknown_name, appearance, voice and forbidden facts.
- If one court pair member is full-visible, keep both anchored: Haru red-haired, Raiden dark-haired.

6) CALENDAR / LOCATION / STATE / RELATIONSHIPS
calendar={_dump(calendar_files, 350)}
location={_dump(location_files, 400)}
state={_dump(state_files, 350)}
relationships={_dump(relationship_files, 350)}

7) ROUTE AND SCENE POSITION
- 15 Aug route: arrival/dropoff -> back court route -> basketball court/sports area -> registration.
- Do not offer route bypass if the route already passes court.
- Haru/Raiden appear at court only when court/sports area is visible or reached.

8) DIALOGUE TURN-TAKING
- If a full-loaded character is addressed by question/taunt/offer/accusation/challenge, give them a response beat before the same speaker continues.
- Response beat = reply, refusal, gesture, action, interruption, or meaningful silence with pressure.
- Do not let one NPC speak at another full-loaded NPC for multiple lines while they only stare/hold an object.
- If player let another character speak for POV, that character may answer, but the addressed NPC still reacts.

9) SCENE MOTION AND BACKGROUND NPCS
- Academy is alive; NPCs act from role, duty, curiosity, schedule, habit and visible pressure.
- Public locations need brief background motion when pressure changes: whispers, side comments, laughs, movement, bench calls, staff/student reactions.
- Background beats stay short and never replace full-loaded character responses.
- Compress routine to the next meaningful beat.
- Stop for meaningful questions, blocked path, risk, new info/character, consent/refusal, disclosure, conflict, or control choice.

10) NPC PERSISTENCE
- Ordinary background noise is not saved.
- Save background/temporary NPCs only if they create a future hook: identifiable role, repeated presence, threat, promise, conflict, favor, debt, rumor source, witness, access gate, injury, discipline issue, relationship pressure.
- Save uncarded NPCs as compact state threads/open hooks, not full character cards during play.
- Save visible facts/consequences only; no hidden motives/private thoughts.

11) BOTTOM UI
- Blocks order: `✦ Что можно сделать`, `✦ Что <POV> могла бы сказать`, `✦ Мысли <POV>`, `✦ Уровни`, `✦ Отношения`.
- Max 3 items in actions/speech/thoughts.
- If actions exist, add exactly: `Варианты ниже не считаются действием, пока игрок не выбрал.`
- Every action starts with `◈`; actions are physical/attention/movement/object/pause/route/observation/posture only.
- No speech verbs or dialogue intent in actions: no сказать, ответить, спросить, позвать, предложить, пошутить, заметить вслух.
- Speech options start with `—`, are exact possible POV lines, no quotes.
- Thought options start with `—`, POV-local only, invisible to NPCs.
- Levels use loaded numeric state; no prose status/narration.
- Relationships only loaded scene pairs: `<Имя>: +<display_score> · <display_label>`; no absent characters, no `без изменений`, no `Акира ↔ Ливия` arrows.

12) SCENE CORE DIGEST
{_cut(scene_core, 300)}

13) REQUIRED FILES
{_dump(required, 400)}

14) OUTPUT CHECK
- Use rendered_header exactly.
- Preserve player input order.
- Apply character anchors and speech profiles.
- Resolve addressed full-loaded NPC response beats.
- Add brief public background motion when scene pressure calls for it.
- Save only important background NPC hooks.
- Keep NPC knowledge visible-source only.
- Keep scene moving.
- No API/debug commentary in play mode.
"""
    return brief[:MAX_PROMPT_PREVIEW_CHARS]
