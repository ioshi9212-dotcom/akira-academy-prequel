"""
Response size guard runtime patch v5.

Keeps getSessionContext and getSessionTurnContract small.
Adds progress panel files to the compact contract and computes relationship panel totals
from relationships.json when the stored visible panel is missing or stale.
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
        return [_compact_text(item, limit=limit) for item in value[:12]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 20:
                out["..."] = "truncated"
                break
            out[str(key)] = _compact_text(item, limit=limit)
        return out
    return str(value)[:limit]


def _scene_chars(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
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
    values: list[Any] = ["akira"]
    for field in fields:
        values.extend(current.get(field, []) or [])
    for thread in current.get("open_threads", []) or []:
        if isinstance(thread, dict) and thread.get("status") in {"due", "active", "triggered"}:
            values.extend(thread.get("participants", []) or [])
    for lock in (future.get("locks") or {}).values():
        if isinstance(lock, dict) and lock.get("status") in {"due", "active", "triggered"}:
            values.extend(lock.get("participants", []) or [])

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
    for rel in (
        f"characters/{folder}/character.yaml",
        f"characters/{folder}/main.yaml",
    ):
        try:
            if base.repo_file_exists(rel):
                files.append(rel)
        except Exception:
            pass
    return files


def _existing_files(paths: list[str]) -> list[str]:
    result: list[str] = []
    for rel in paths:
        try:
            if rel == "runtime/scene_context_digest.md" or base.repo_file_exists(rel):
                result.append(rel)
        except Exception:
            if rel == "runtime/scene_context_digest.md":
                result.append(rel)
    return result


def _required_files(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    files: list[str] = _existing_files([
        "runtime/scene_context_digest.md",
        "gpt/locks/runtime_scene_rules_digest.md",
        "gpt/scene_format.md",
        "characters/character_id_index.md",
    ])
    for cid in _scene_chars(current, future):
        files.extend(_character_files_compact(cid))
    files.extend(_existing_files([
        "gpt/locks/npc_living_scene_rules.md",
        "gpt/locks/outfit_state_lock.md",
    ]))
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
    for cid in chars[:12]:
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
        if parts and parts <= focus:
            out[pair_id] = _compact_text(data, 900)
        if len(out) >= 20:
            break
    return {"pairs": out, "_context_filter": "focus_pairs_only_size_guard"}


def _story_slice(story: Any) -> dict[str, Any]:
    if not isinstance(story, dict):
        return {}
    shared = story.get("shared_events")
    if isinstance(shared, list):
        shared = shared[-12:]
    else:
        shared = []
    return {
        "turn_counter": _compact_text(story.get("turn_counter"), 1000),
        "daily_timeline": _compact_text(story.get("daily_timeline"), 1600),
        "shared_events_recent": _compact_text(shared, 1000),
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

    result: dict[str, Any] = {}
    for pair_id in wanted:
        data = pairs.get(pair_id)
        if data is None and pair_id == "akira__kir":
            data = pairs.get("akira__kir_knox")
        if data is None and pair_id == "akira__haru_foster":
            data = pairs.get("akira__haru")
        if data is None and pair_id == "akira__raiden_sterling":
            data = pairs.get("akira__raiden")

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
        "visible_panel_rule": "Show current total scores, not only per-scene deltas. Prefer computed_relationship_score_panel when available.",
    }


class SizeGuardContextResponse(BaseModel):
    session_id: str
    mode: str = "size_guard_compact_context"
    current_state: dict[str, Any] = Field(default_factory=dict)
    active_character_ids: list[str] = Field(default_factory=list)
    nearby_character_ids: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    usage_note: str = (
        "This endpoint is intentionally small. For full context, call "
        "getRequiredFilesManifest and then getRequiredFilesChunk until has_more=false."
    )


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
    usage_note: str = (
        "Do not stop after this compact contract. Next call getRequiredFilesManifest, "
        "then getRequiredFilesChunk from chunk_index=0 until has_more=false."
    )


def _small_output_contract() -> dict[str, Any]:
    return {
        "format": "academy_old_visual_novel_header_v2",
        "scene_header_required": True,
        "bottom_blocks": [
            "✦ Что можно сделать",
            "✦ Что Акира могла бы сказать",
            "✦ Мысли Акиры",
            "✦ Состояние",
            "✦ Отношения",
        ],
        "rules": [
            "Final gameplay answer must be the scene only, not API/status/debug summary.",
            "Use latest visible scene facts before stale state or old options.",
            "Bottom-block options are not facts until player chooses them.",
            "Player controls only Akira; do not invent Akira speech unless written outside parentheses.",
            "Characters know only what they saw, heard, were told, or can infer from visible signs.",
            "Delayed/absent/off-screen characters cannot know scenes they missed unless told or saved in knowledge_state.",
            "Do not rename invented/unnamed NPCs into fixed canon characters after description.",
            "Do not make the scene answer Akira's unspoken text without visible source.",
            "Show current total progress/relationship scores in the panel, not only scene delta.",
            "Relationship details stay internal; visible panel shows score plus short label.",
            "Prefer computed_relationship_score_panel over stale stored panel values.",
            "Training can improve stats but may also increase fatigue, risk, or injury.",
            "Stop at a player choice point when Akira is directly challenged or questioned.",
        ],
    }


def _small_prompt_preview(chars: list[str], required_files: list[str]) -> str:
    return (
        "PLAY MODE SIZE-GUARD BRIEF\n"
        "- This turn-contract is intentionally compact to avoid ResponseTooLargeError.\n"
        "- Do not stop here. Load getRequiredFilesManifest, then all getRequiredFilesChunk chunks.\n"
        "- Render scene only after chunks are loaded.\n"
        f"- Focus characters: {', '.join(chars)}.\n"
        f"- Required files count: {len(required_files)}.\n"
        "- Enforce: latest visible facts, canon identity boundary, witness/knowledge boundary, "
        "visible-source rule, player action boundary, scene-only final answer.\n"
        "- End panel: show current total physical/energy/relationship scores, not just last-scene delta.\n"
        "- Relationship panel must use computed totals from relationships.json when possible.\n"
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
        "Do not stop because getSessionContext was compact; chunks contain the full render context.",
        "Use latest visible scene facts before stale current_state.",
        "Do not grant absent/delayed characters knowledge of scenes they missed.",
        "Do not rename invented/session NPCs into fixed canon characters.",
        "End panel must show current total progress/relationship scores, not only per-scene deltas.",
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
            "visible_inventory": _compact_text(current.get("visible_inventory", []), 900),
            "nearby_items": _compact_text(current.get("nearby_items", []), 900),
            "akira_inventory_state": _compact_text((inventory.get("akira") or {}) if isinstance(inventory, dict) else {}, 900),
        },
        relationship_context=_relationship_slice(relationships, chars),
        story_context=story_context,
        prompt_preview=_small_prompt_preview(chars, files),
    )


app.version = "0.3.60-relationship-panel-compute-v1"
