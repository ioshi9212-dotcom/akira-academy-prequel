"""
Response size guard runtime patch v6-minimal-lock-restore.

Keeps getSessionContext and getSessionTurnContract small, but does not starve the scene
assembly. Calendar/day/state files stay available through chunked required files.

Also separates visible header state from numeric progress levels:
- header state = short current visible condition;
- bottom levels panel = physical/energy numeric totals;
- relationship panel = computed total scores, not per-scene deltas.

Minimal restore note:
- this file intentionally restores only the old runtime locks that guarded scene behavior;
- it does not restore README clutter, patch_notes, old duplicated format files, or v3 logic.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

import app.context_transport_runtime_patch as rt
from app.context_transport_runtime_patch import app
from app import compact as base
import app.compact_context_patch as ccp

CONTEXT_PATH = "/api/v1/sessions/{session_id}/context"
TURN_CONTRACT_PATH = "/api/v1/sessions/{session_id}/turn-contract"

PROGRESS_FILES = [
    "gpt/locks/progress_panel_rules.md",
    "state/akira_progress_state.json",
    "state/relationship_score_panel.json",
]

LIGHT_STATE_FILES = [
    "state/current_state.json",
    "state/inventory_state.json",
    "state/story_lines.json",
    "state/relationships.json",
    "state/knowledge_state.json",
    "state/calendar_runtime.json",
    "state/location_registry.md",
]

BASE_RULE_FILES = [
    "runtime/scene_context_digest.md",
    "gpt/locks/runtime_scene_rules_digest.md",
    "gpt/scene_format.md",
    "gpt/locks/npc_living_scene_rules.md",
    "gpt/locks/state_update_payload_contract.md",

    # Minimal restore from the old working repo. These files are not decorative:
    # they protect player agency, roster continuity, calendar/lore boundaries,
    # outfit source, non-empty scenes and progress panels.
    "gpt/locks/player_input_anchor_lock.md",
    "gpt/locks/character_presence_rotation_lock.md",
    "gpt/locks/story_lines_memory_lock.md",
    "gpt/locks/calendar_usage_lock.md",
    "gpt/locks/lore_usage_lock.md",
    "gpt/locks/no_empty_scenes_lock.md",
    "gpt/locks/outfit_state_lock.md",
]

DISPLAY_NAMES = {
    "livia_cross": "Ливия",
    "livia": "Ливия",
    "kir": "Кир",
    "kir_knox": "Кир",
    "haru": "Хару",
    "haru_foster": "Хару",
    "raiden": "Райден",
    "raiden_sterling": "Райден",
}


def _remove_routes(path: str, methods: set[str] | None = None, operation_id: str | None = None) -> None:
    keep = []
    for route in app.router.routes:
        route_path = getattr(route, "path", None)
        route_methods = set(getattr(route, "methods", set()) or set())
        route_operation_id = getattr(route, "operation_id", None)
        match_path = route_path == path
        match_methods = methods is None or bool(route_methods & methods)
        match_operation = operation_id is None or route_operation_id == operation_id
        if match_path and match_methods and match_operation:
            continue
        keep.append(route)
    app.router.routes = keep


def _unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in result:
            result.append(item)
    return result


def _canonical_id(value: Any) -> str:
    try:
        return rt.canonical_id(value)
    except Exception:
        return str(value or "").strip()


def _known_character_folder(cid: str) -> str | None:
    try:
        return rt.known_character_folder(cid)
    except Exception:
        folders = getattr(ccp, "NEW_CHARACTER_FOLDERS", {}) or {}
        return folders.get(cid)


def _repo_exists(path: str) -> bool:
    if path == "runtime/scene_context_digest.md":
        return True
    try:
        return bool(base.repo_file_exists(path))
    except Exception:
        return False


def _safe_read_json(path: str, session_id: str, default: Any) -> Any:
    try:
        return base.read_json(path, session_id, default=default) or default
    except Exception:
        return default


def _compact_text(value: Any, limit: int = 900) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= limit else text[:limit].rstrip() + "...<truncated>"
    if isinstance(value, list):
        return [_compact_text(item, limit=limit) for item in value[:14]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 24:
                out["..."] = "truncated"
                break
            out[str(key)] = _compact_text(item, limit=limit)
        return out
    return str(value)[:limit]


def _base_scene_chars(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    try:
        chars = base.active_scene_characters(current, future)
        if chars:
            return _unique([_canonical_id(c) for c in chars])
    except Exception:
        pass
    try:
        chars = ccp.active_scene_characters(current, future)  # type: ignore[attr-defined]
        if chars:
            return _unique([_canonical_id(c) for c in chars])
    except Exception:
        pass
    return []


def _scene_chars(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    values: list[Any] = ["akira"]
    values.extend(_base_scene_chars(current, future))

    fields = [
        "active_characters",
        "nearby_characters",
        "speaking_character_ids",
        "observing_character_ids",
        "addressed_character_ids",
        "looked_at_character_ids",
        "mentioned_character_ids",
        "scheduled_character_ids",
        "delayed_character_ids",
    ]
    for field in fields:
        values.extend(current.get(field, []) or [])

    for thread in current.get("open_threads", []) or []:
        if isinstance(thread, dict) and thread.get("status") in {"due", "active", "triggered"}:
            values.extend(thread.get("participants", []) or [])

    for lock in (future.get("locks") or {}).values():
        if isinstance(lock, dict) and lock.get("status") in {"due", "active", "triggered"}:
            values.extend(lock.get("participants", []) or [])

    # First-day Academy entry needs these files even if the compact state forgot to list them.
    if str(current.get("current_date") or "") == "1198-08-15":
        values.extend(["livia_cross", "haru_foster", "raiden_sterling", "kir"])

    result: list[str] = []
    for value in values:
        cid = _canonical_id(value)
        if not cid or cid in {"students", "staff", "crowd", "academy_staff", "new_students_block_b"}:
            continue
        if _known_character_folder(cid) or cid == "akira":
            result.append(cid)
    return _unique(result)


def _character_files_compact(cid: str) -> list[str]:
    folder = _known_character_folder(cid)
    if not folder:
        return []
    files: list[str] = []
    # character.yaml gives voice/behavior; main.yaml gives appearance/energy; past only for active scene chars when needed via chunks, not compact contract.
    for rel in (
        f"characters/{folder}/character.yaml",
        f"characters/{folder}/main.yaml",
    ):
        if _repo_exists(rel):
            files.append(rel)
    return files


def _calendar_files(current: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for rel in ("calendar/calendar_index.yaml",):
        if _repo_exists(rel):
            files.append(rel)
    current_date = str(current.get("current_date") or "").strip()
    if current_date:
        day_file = f"calendar/days/{current_date}.yaml"
        if _repo_exists(day_file):
            files.append(day_file)
    # Legacy fallback still contains some first-scene scheduling in older setups.
    if _repo_exists("state/academy_schedule.json"):
        files.append("state/academy_schedule.json")
    return files


def _existing_files(paths: list[str]) -> list[str]:
    return [rel for rel in paths if _repo_exists(rel)]


def _required_files(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    files: list[str] = []
    files.extend(_existing_files(BASE_RULE_FILES))
    if _repo_exists("characters/character_id_index.md"):
        files.append("characters/character_id_index.md")
    files.extend(_existing_files(LIGHT_STATE_FILES))
    files.extend(_calendar_files(current))
    for cid in _scene_chars(current, future):
        files.extend(_character_files_compact(cid))
    files.extend(_existing_files(PROGRESS_FILES))
    return _unique(files)


def _current_state_slice(current: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "current_date",
        "current_time",
        "current_location_id",
        "current_location_text",
        "current_scene_goal",
        "akira_behavior_profile",
        "akira_state",
        "current_outfit",
        "uniform_worn",
        "visible_inventory",
        "nearby_items",
        "active_characters",
        "nearby_characters",
        "scheduled_character_ids",
        "delayed_character_ids",
        "mentioned_character_ids",
        "speaking_character_ids",
        "observing_character_ids",
        "addressed_character_ids",
        "looked_at_character_ids",
        "last_player_input",
        "open_threads",
    ]
    return {key: _compact_text(current.get(key), 1000) for key in keys if key in current}


def _knowledge_slice(knowledge: Any, chars: list[str]) -> dict[str, Any]:
    if not isinstance(knowledge, dict):
        return {}
    out: dict[str, Any] = {}
    for cid in chars[:14]:
        if cid in knowledge:
            out[cid] = _compact_text(knowledge.get(cid), 1200)
    return out


def _relationship_slice(relationships: Any, chars: list[str]) -> dict[str, Any]:
    if not isinstance(relationships, dict):
        return {}
    pairs = relationships.get("pairs")
    if not isinstance(pairs, dict):
        return {}
    focus = set(chars)
    out: dict[str, Any] = {}
    for pair_id, data in pairs.items():
        parts = {part for part in str(pair_id).split("__") if part}
        if parts and (parts <= focus or "akira" in parts):
            out[pair_id] = _compact_text(data, 900)
        if len(out) >= 24:
            break
    return {"pairs": out, "_context_filter": "focus_pairs_and_akira_pairs_size_guard"}


def _story_slice(story: Any) -> dict[str, Any]:
    if not isinstance(story, dict):
        return {}
    shared = story.get("shared_events")
    if isinstance(shared, list):
        shared = shared[-14:]
    else:
        shared = []
    return {
        "turn_counter": _compact_text(story.get("turn_counter"), 1000),
        "daily_timeline": _compact_text(story.get("daily_timeline"), 1800),
        "shared_events_recent": _compact_text(shared, 1200),
        "next_beats": _compact_text(story.get("next_beats"), 1200),
    }


def _clamp_score(value: float) -> int:
    return max(-100, min(100, int(round(value))))


def _relationship_score(data: Any) -> int:
    if not isinstance(data, dict):
        return 0
    positive = {
        "affection": 1.2,
        "trust": 1.2,
        "respect": 1.0,
        "interest": 0.8,
        "curiosity": 0.8,
        "warmth": 1.2,
        "attachment": 1.5,
    }
    negative = {
        "tension": -0.8,
        "irritation": -0.7,
        "fear": -1.0,
        "resentment": -1.2,
        "suspicion": -1.0,
        "jealousy": -0.4,
    }
    total = 0.0
    for key, weight in positive.items():
        total += float(data.get(key) or 0) * weight
    for key, weight in negative.items():
        total += float(data.get(key) or 0) * weight
    return _clamp_score(total)


def _label_for_pair(pair_id: str, score: int) -> str:
    pair = pair_id.lower()
    if score <= -60:
        return "враждебность"
    if score <= -35:
        return "сильное напряжение"
    if score <= -15:
        return "настороженность"
    if score <= 14:
        return "неясно"
    if "livia" in pair:
        if score >= 75:
            return "почти семья"
        if score >= 55:
            return "тёплая близость"
        if score >= 35:
            return "старые подруги"
        return "тёплый контакт"
    if "kir" in pair:
        if score >= 55:
            return "свой, но язвит"
        if score >= 35:
            return "доверяет неохотно"
        return "осторожный интерес"
    if "haru" in pair:
        if score >= 55:
            return "сильная симпатия"
        if score >= 35:
            return "тянется ближе"
        return "явный интерес"
    if "raiden" in pair:
        if score >= 55:
            return "держится рядом"
        if score >= 35:
            return "молча наблюдает"
        return "холодная настороженность"
    if score <= 34:
        return "интерес"
    if score <= 54:
        return "доверие"
    if score <= 74:
        return "близость"
    return "сильная привязанность"


def _display_name_for_pair(pair_id: str) -> str:
    parts = [p for p in pair_id.split("__") if p and p != "akira"]
    other = parts[0] if parts else pair_id
    return DISPLAY_NAMES.get(other, other)


def _computed_relationship_panel(relationships: Any, stored_panel: Any) -> dict[str, Any]:
    pairs = relationships.get("pairs") if isinstance(relationships, dict) else {}
    if not isinstance(pairs, dict):
        return stored_panel if isinstance(stored_panel, dict) else {}
    stored_items = {}
    if isinstance(stored_panel, dict):
        stored_items = stored_panel.get("relationship_score_panel") or {}
        if not isinstance(stored_items, dict):
            stored_items = {}
    wanted = [
        "akira__livia_cross",
        "akira__kir",
        "akira__haru_foster",
        "akira__raiden_sterling",
    ]
    aliases = {
        "akira__kir": ["akira__kir", "akira__kir_knox"],
        "akira__haru_foster": ["akira__haru_foster", "akira__haru"],
        "akira__raiden_sterling": ["akira__raiden_sterling", "akira__raiden"],
    }
    result: dict[str, Any] = {}
    for pair_id in wanted:
        data = pairs.get(pair_id)
        for alt in aliases.get(pair_id, []):
            if data is None:
                data = pairs.get(alt)
        if isinstance(data, dict):
            score = _relationship_score(data)
            result[pair_id] = {
                "display_name": _display_name_for_pair(pair_id),
                "score": score,
                "label": _label_for_pair(pair_id, score),
                "source": "computed_from_relationships_json",
            }
        elif pair_id in stored_items:
            result[pair_id] = stored_items[pair_id]
        else:
            result[pair_id] = {
                "display_name": _display_name_for_pair(pair_id),
                "score": 0,
                "label": "неясно",
                "source": "default_no_relationship_pair",
            }
    return result


def _progress_slice(session_id: str, relationships: Any | None = None) -> dict[str, Any]:
    progress = _safe_read_json("state/akira_progress_state.json", session_id, {})
    relationship_panel = _safe_read_json("state/relationship_score_panel.json", session_id, {})
    computed_panel = _computed_relationship_panel(relationships or {}, relationship_panel)
    return {
        "akira_progress_state": _compact_text(progress, 1400),
        "relationship_score_panel": _compact_text(relationship_panel, 1400),
        "computed_relationship_score_panel": _compact_text(computed_panel, 1400),
        "visible_panel_rule": "Header state is short condition text. Bottom 'Уровни' is numeric physical/energy totals. Relationship panel shows current total scores, not per-scene deltas.",
    }


class SizeGuardContextResponse(BaseModel):
    session_id: str
    mode: str = "size_guard_compact_context"
    current_state: dict[str, Any] = Field(default_factory=dict)
    active_character_ids: list[str] = Field(default_factory=list)
    nearby_character_ids: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    usage_note: str = "Compact endpoint. Load full context through getRequiredFilesManifest + getRequiredFilesChunk."


class TurnContractWithPromptPreview(BaseModel):
    session_id: str
    mode: str = "size_guard_turn_contract"
    active_character_ids: list[str] = Field(default_factory=list)
    nearby_character_ids: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    output_format_contract: dict[str, Any] = Field(default_factory=dict)
    required_checks_before_answer: list[str] = Field(default_factory=list)
    knowledge_table: dict[str, Any] = Field(default_factory=dict)
    inventory_contract: dict[str, Any] = Field(default_factory=dict)
    relationship_context: dict[str, Any] = Field(default_factory=dict)
    story_context: dict[str, Any] = Field(default_factory=dict)
    prompt_preview: str = ""
    prompt_preview_usage: str = "Small brief only. Load manifest/chunks before rendering gameplay."
    usage_note: str = "Do not stop after this compact contract. Load manifest/chunks next."


def _small_output_contract() -> dict[str, Any]:
    return {
        "format": "academy_old_visual_novel_header_v2",
        "scene_header_required": True,
        "header_state_rule": "Header ✦ is short visible/current condition, not numeric power level.",
        "bottom_blocks": [
            "✦ Что можно сделать",
            "✦ Что Акира могла бы сказать",
            "✦ Мысли Акиры",
            "✦ Уровни",
            "✦ Отношения",
        ],
        "rules": [
            "Final gameplay answer must be the scene only, not API/status/debug summary.",
            "Normal narration is plain text; italics only for short stage remarks or brief physical detail.",
            "Do not wrap scene dialogue or speech options in quotation marks.",
            "Dialogue format: **Name/descriptor** — text without quotes. (*short remark if needed*)",
            "Action choices must be direct actions; do not start with 'Акира может'.",
            "Do not put ready spoken lines inside action choices; exact lines go only to 'Что Акира могла бы сказать'.",
            "Use latest visible scene facts before stale state or old options.",
            "Player controls only Akira; do not invent Akira speech unless written outside parentheses.",
            "Characters know only what they saw, heard, were told, or can infer from visible signs.",
            "Do not rename invented/unnamed NPCs into fixed canon characters after description.",
            "Header outfit must include all saved current_outfit items; do not omit top if state says top.",
            "Bottom 'Уровни' shows numeric physical/energy totals only, not text mood.",
            "Bottom 'Отношения' shows current total score plus label, not per-scene delta.",
            "Prefer computed_relationship_score_panel over stale stored panel values.",
            "Training can improve stats but may also increase fatigue, risk, or injury.",
            "Stop at a player choice point when Akira is directly challenged or questioned.",
        ],
    }


def _small_prompt_preview(chars: list[str], required_files: list[str]) -> str:
    return (
        "PLAY MODE SIZE-GUARD BRIEF\n"
        "- This turn-contract is compact; do not stop here.\n"
        "- Next load getRequiredFilesManifest, then all getRequiredFilesChunk chunks.\n"
        "- Render scene only after chunks are loaded.\n"
        f"- Focus characters: {', '.join(chars)}.\n"
        f"- Required files count: {len(required_files)}.\n"
        "- First-day/caledar files must be used for scheduled characters and scene setup.\n"
        "- Header ✦ = short current visible condition. Bottom ✦ Уровни = numeric physical/energy levels.\n"
        "- No quotation marks around dialogue or speech options.\n"
        "- Action choices are direct actions, never 'Акира может...'.\n"
    )


_remove_routes(CONTEXT_PATH, {"GET"}, "getSessionContext")
_remove_routes(TURN_CONTRACT_PATH, {"GET"}, "getSessionTurnContract")


@app.get(CONTEXT_PATH, response_model=SizeGuardContextResponse, operation_id="getSessionContext")
def get_session_context_size_guard(session_id: str) -> SizeGuardContextResponse:
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)
    current = _safe_read_json("state/current_state.json", sid, {})
    future = _safe_read_json("state/future_locks_progress.json", sid, {})
    files = _required_files(current, future)
    return SizeGuardContextResponse(
        session_id=sid,
        current_state=_current_state_slice(current),
        active_character_ids=_unique(current.get("active_characters", []) or []),
        nearby_character_ids=_unique(current.get("nearby_characters", []) or []),
        required_files=files,
    )


@app.get(TURN_CONTRACT_PATH, response_model=TurnContractWithPromptPreview, operation_id="getSessionTurnContract")
def get_session_turn_contract_size_guard(session_id: str) -> TurnContractWithPromptPreview:
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)
    current = _safe_read_json("state/current_state.json", sid, {})
    future = _safe_read_json("state/future_locks_progress.json", sid, {})
    knowledge = _safe_read_json("state/knowledge_state.json", sid, {})
    inventory = _safe_read_json("state/inventory_state.json", sid, {})
    relationships = _safe_read_json("state/relationships.json", sid, {})
    story_lines = _safe_read_json("state/story_lines.json", sid, {})
    chars = _scene_chars(current, future)
    files = _required_files(current, future)

    required_checks = [
        "Call getRequiredFilesManifest next.",
        "Then call getRequiredFilesChunk starting with chunk_index=0 until has_more=false.",
        "Do not render gameplay from this compact contract alone.",
        "Use calendar/day files for first scene scheduled characters, including Haru/Raiden when scheduled.",
        "Use latest visible scene facts before stale current_state.",
        "Header ✦ is short visible condition; bottom ✦ Уровни is numeric levels only.",
        "Do not use quotation marks around dialogue or speech choices.",
        "Do not start action choices with 'Акира может'.",
        "Use computed_relationship_score_panel from relationships.json when available.",
    ]

    story_context = _story_slice(story_lines)
    story_context["progress_panel"] = _progress_slice(sid, relationships)

    return TurnContractWithPromptPreview(
        session_id=sid,
        active_character_ids=_unique(current.get("active_characters", []) or []),
        nearby_character_ids=_unique(current.get("nearby_characters", []) or []),
        required_files=files,
        output_format_contract=_small_output_contract(),
        required_checks_before_answer=required_checks,
        knowledge_table=_knowledge_slice(knowledge, chars),
        inventory_contract={
            "visible_inventory": _compact_text(current.get("visible_inventory", []), 1000),
            "nearby_items": _compact_text(current.get("nearby_items", []), 1000),
            "current_outfit": _compact_text(current.get("current_outfit"), 1000),
            "uniform_worn": current.get("uniform_worn"),
            "akira_inventory_state": _compact_text((inventory.get("akira") or {}) if isinstance(inventory, dict) else {}, 1000),
        },
        relationship_context=_relationship_slice(relationships, chars),
        story_context=story_context,
        prompt_preview=_small_prompt_preview(chars, files),
    )


app.version = "0.3.64-minimal-lock-restore-v1"
