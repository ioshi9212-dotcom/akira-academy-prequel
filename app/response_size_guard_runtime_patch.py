"""
Response size guard runtime patch v1.

Keeps getSessionContext and getSessionTurnContract small so GPT Actions do not stop
with ResponseTooLargeError after a long session.

Full state and required file contents must be loaded through:
- getRequiredFilesManifest
- getRequiredFilesChunk
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
    try:
        chars = base.active_scene_characters(current, future)
        if chars:
            return _unique(chars)
    except Exception:
        pass
    fields = [
        "active_characters", "nearby_characters", "speaking_character_ids",
        "observing_character_ids", "addressed_character_ids", "looked_at_character_ids",
        "mentioned_character_ids", "scheduled_character_ids", "delayed_character_ids",
    ]
    values: list[Any] = ["akira"]
    for field in fields:
        values.extend(current.get(field, []) or [])
    return _unique(values)


def _required_files(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    try:
        files = base.recommended_files_for_context(current, future)
        if files:
            return _unique(files)
    except Exception:
        pass
    try:
        files = ccp.recommended_files_for_context(current, future)
        if files:
            return _unique(files)
    except Exception:
        pass
    return [
        "runtime/scene_context_digest.md",
        "gpt/locks/runtime_scene_rules_digest.md",
        "gpt/scene_format.md",
        "characters/character_id_index.md",
        "characters/akira/character.yaml",
        "characters/akira/past.yaml",
        "characters/akira/main.yaml",
    ]


def _current_state_slice(current: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "current_date", "current_time", "current_location_id", "current_location_text",
        "current_scene_goal", "akira_behavior_profile", "akira_state", "current_outfit",
        "uniform_worn", "visible_inventory", "nearby_items", "active_characters",
        "nearby_characters", "scheduled_character_ids", "delayed_character_ids",
        "mentioned_character_ids", "speaking_character_ids", "observing_character_ids",
        "addressed_character_ids", "looked_at_character_ids", "last_player_input", "open_threads",
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


class SizeGuardTurnContractResponse(BaseModel):
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


@app.get(TURN_CONTRACT_PATH, response_model=SizeGuardTurnContractResponse, operation_id="getSessionTurnContract")
def get_session_turn_contract_size_guard(session_id: str) -> SizeGuardTurnContractResponse:
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
    ]

    return SizeGuardTurnContractResponse(
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
        story_context=_story_slice(story_lines),
        prompt_preview=_small_prompt_preview(chars, files),
    )


app.version = "0.3.56-response-size-guard-v1"
