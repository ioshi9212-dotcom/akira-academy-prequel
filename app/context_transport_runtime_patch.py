"""
Runtime patch v5: lean selective context + safe chunk transport + roster cleanup.

Goals:
- keep gameplay context selective, not full bundle;
- stop stale active_characters from sticking forever;
- expose repairSceneRoster endpoint;
- reduce chunk calls without triggering ResponseTooLargeError.

Install:
    app/server.py -> from app.context_transport_runtime_patch import app
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

# Keep compatibility with previous patch chain.
# state_write_runtime_patch may import compact_context_patch internally.
try:
    import app.state_write_runtime_patch as state_write_patch  # type: ignore
except Exception:
    state_write_patch = None  # noqa: N816

try:
    import app.selective_context_patch as previous_selective  # type: ignore
except Exception:
    previous_selective = None  # noqa: N816

from app import compact as base
import app.compact_context_patch as ccp

app = base.app
app.version = "0.3.20-context-transport-v5"

RUNTIME_DIGEST_FILE = "runtime/scene_context_digest.md"

MINIMAL_LOCK_FILES = [
    "gpt/locks/gameplay_response_gate.md",
    "gpt/locks/player_input_anchor_lock.md",
    "gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md",
    "gpt/locks/dialogue_format_strict_lock.md",
    "gpt/locks/no_empty_scenes_lock.md",
    "gpt/locks/state_update_payload_contract.md",
    "gpt/locks/selective_context_runtime_lock.md",
]

ROSTER_FIELDS = [
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

CHARACTER_FIELDS = [
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

SCENE_GROUP_IDS = {
    "block_b_dorm_staff",
    "new_students_block_b",
    "students",
    "staff",
    "crowd",
    "academy_staff",
}

ID_ALIASES = {
    "char_akira": "akira",
    "livia_cross": "livia",
    "char_livia": "livia",
    "kir_knox": "kir",
    "char_kir": "kir",
    "raiden_sterling": "raiden",
    "char_raiden": "raiden",
    "haru_foster": "haru",
    "char_haru": "haru",
    "kiara_volt": "kiara",
    "char_kiara": "kiara",
    "kael": "kael_north",
    "north": "kael_north",
    "char_kael_north": "kael_north",
}


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value).strip() if value else ""
        if item and item not in result:
            result.append(item)
    return result


def canonical_id(value: Any) -> str:
    raw = str(value or "").strip()
    return ID_ALIASES.get(raw, raw)


def known_character_folder(cid: str) -> str | None:
    canon = canonical_id(cid)
    folders = getattr(ccp, "NEW_CHARACTER_FOLDERS", {}) or {}
    if canon in folders:
        return folders[canon]
    if cid in folders:
        return folders[cid]
    return None


def is_known_character_id(cid: str) -> bool:
    return bool(known_character_folder(cid))


def scene_character_ids(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    current = current or {}
    ids: list[str] = ["akira"]

    for field in CHARACTER_FIELDS:
        for value in current.get(field, []) or []:
            cid = canonical_id(value)
            if cid not in SCENE_GROUP_IDS and is_known_character_id(cid):
                ids.append(cid)

    # Future locks are allowed only when already due/active/triggered, not merely scheduled far ahead.
    future = future or {}
    for lock in (future.get("locks") or {}).values():
        if not isinstance(lock, dict):
            continue
        if lock.get("status") not in {"due", "active", "triggered"}:
            continue
        for value in lock.get("participants", []) or []:
            cid = canonical_id(value)
            if cid not in SCENE_GROUP_IDS and is_known_character_id(cid):
                ids.append(cid)

    return _unique(ids)


def character_files_for_context(cid: str, *, include_past: bool = True) -> list[str]:
    folder = known_character_folder(cid)
    if not folder:
        return []
    candidates = [
        f"characters/{folder}/character.yaml",
    ]
    if include_past:
        candidates.append(f"characters/{folder}/past.yaml")
    # main.yaml is small/optional; include after character/past only when it exists and does not bloat.
    candidates.append(f"characters/{folder}/main.yaml")
    return [p for p in candidates if base.repo_file_exists(p)]


def lean_recommended_files_for_context(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    current = current or {}
    future = future or {}

    chars = scene_character_ids(current, future)
    files: list[str] = []

    # The digest contains compacted current_state, relationships, story_lines, knowledge and short rule digest.
    files.append(RUNTIME_DIGEST_FILE)

    # Keep only small critical locks as full files.
    for path in MINIMAL_LOCK_FILES:
        if base.repo_file_exists(path):
            files.append(path)

    # Small id index helps with unknown names.
    if base.repo_file_exists("characters/character_id_index.md"):
        files.append("characters/character_id_index.md")

    # Full active character slices. This is what preserves scene quality.
    for cid in chars:
        files.extend(character_files_for_context(cid, include_past=True))

    # Hard cap on required file count as a safety valve, but do not drop active character.yaml.
    return _unique(files)


def same_pair(pair_id: str, focus: set[str]) -> bool:
    parts = {canonical_id(part) for part in str(pair_id).split("__") if part}
    return bool(parts and parts <= focus)


def compact_relationships_scene_pairs_only(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = {canonical_id(x) for x in (focus_ids or ["akira"])}
    pairs = state.get("pairs")
    if not isinstance(pairs, dict):
        return state
    filtered = {pair: data for pair, data in pairs.items() if same_pair(str(pair), focus)}
    return {
        "pairs": filtered,
        "_context_filter": {
            "mode": "scene_pairs_only",
            "focus_character_ids": sorted(focus),
            "visible_pairs": len(filtered),
            "total_pairs": len(pairs),
        },
    }


def compact_knowledge_scene_only(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = {canonical_id(x) for x in (focus_ids or ["akira"])}
    filtered = {}
    for key, value in state.items():
        if canonical_id(key) in focus:
            filtered[key] = value
    return {
        **filtered,
        "_context_filter": {
            "mode": "scene_character_knowledge_only",
            "focus_character_ids": sorted(focus),
            "visible_characters": len(filtered),
            "total_characters": len(state),
        },
    }


def compact_story_lines_scene_only(state: Any, focus_ids: list[str], max_events: int = 12) -> Any:
    if not isinstance(state, dict):
        return state
    focus = {canonical_id(x) for x in (focus_ids or ["akira"])}
    lines = state.get("lines")
    visible_lines = {}
    if isinstance(lines, dict):
        for line_id, line in lines.items():
            if not isinstance(line, dict):
                continue
            ids = {canonical_id(x) for x in (line.get("character_ids", []) or [])}
            ids |= {canonical_id(x) for x in (line.get("related_ids", []) or [])}
            if ids & focus or line_id in {"academy_arrival", "akira_livia_friendship"}:
                visible_lines[line_id] = line

    shared_events = state.get("shared_events", [])
    if isinstance(shared_events, list):
        shared_events = shared_events[-max_events:]
    else:
        shared_events = []

    return {
        "schema": state.get("schema"),
        "turn_counter": state.get("turn_counter", {}),
        "calendar_policy": state.get("calendar_policy", {}),
        "daily_timeline": base.compact_if_large(state.get("daily_timeline", {}), 1800),
        "shared_events_recent": shared_events,
        "lines": visible_lines,
        "_context_filter": {
            "mode": "scene_story_lines_only",
            "focus_character_ids": sorted(focus),
            "visible_lines": list(visible_lines.keys()),
            "total_lines": len(lines) if isinstance(lines, dict) else 0,
        },
    }


def _json_block(title: str, value: Any, max_chars: int = 4500) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        text = str(value)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...<truncated>"
    return f"\n## {title}\n```json\n{text}\n```\n"


def build_scene_context_digest(session_id: str) -> str:
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    chars = scene_character_ids(current, future)

    relationships = compact_relationships_scene_pairs_only(
        base.read_json("state/relationships.json", session_id, default={}) or {},
        chars,
    )
    story_lines = compact_story_lines_scene_only(
        base.read_json("state/story_lines.json", session_id, default={}) or {},
        chars,
    )
    knowledge = compact_knowledge_scene_only(
        base.read_json("state/knowledge_state.json", session_id, default={}) or {},
        chars,
    )
    inventory = base.compact_if_large(base.read_json("state/inventory_state.json", session_id, default={}) or {}, 1800)
    academy_schedule = base.compact_if_large(base.read_json("state/academy_schedule.json", session_id, default={}) or {}, 1800)

    rule_digest = {
        "output": [
            "Gameplay only: no API/status/debug summary in final answer.",
            "Dialogue format: **Name/descriptor** — speech. (*short italic remark*)",
            "Descriptions are separate italic paragraphs.",
            "Akira thoughts only in bottom block, not inside the scene body.",
            "No empty scene: add hook/reaction/conflict/consequence or time skip.",
        ],
        "state_write": [
            "Backend does not infer state from prose.",
            "If relationships/story/knowledge/current_state change, send explicit state payload to apply-turn-result.",
            "Roster lists are replacement fields, not append-only fields.",
        ],
        "knowledge": [
            "NPC factual claims require known source; otherwise use question/suspicion/wrong assumption/silence.",
        ],
        "relationships": [
            "Use only relationships between scene characters unless another character is explicitly mentioned or scheduled.",
        ],
    }

    text = "# Runtime scene context digest\n"
    text += "This digest replaces heavy global prompt/canon/state files for normal gameplay. Use exact character files also loaded in required_files.\n"
    text += _json_block("Rule digest", rule_digest, 3600)
    text += _json_block("Scene character ids", chars, 1200)
    text += _json_block("Current state", current, 3600)
    text += _json_block("Relationship slice", relationships, 4000)
    text += _json_block("Story lines slice", story_lines, 5000)
    text += _json_block("Knowledge slice", knowledge, 3500)
    text += _json_block("Inventory slice", inventory, 1800)
    text += _json_block("Calendar slice", academy_schedule, 1800)
    text += "\n## State update reminder\nIf scene changes roster, use current_state_changes with roster fields as full replacement lists.\n"
    return text


def read_required_file_for_bundle(path: str, session_id: str) -> tuple[str | None, str | None]:
    safe_path = str(path).strip()
    if not safe_path:
        return None, None
    if safe_path == RUNTIME_DIGEST_FILE:
        return build_scene_context_digest(session_id), "runtime"
    return ccp._read_required_file_for_bundle(safe_path, session_id)


def split_text_safe(content: str, part_chars: int) -> list[str]:
    # Keep file pieces reasonably small; response JSON overhead matters.
    part_chars = max(6000, min(int(part_chars or 9000), 9000))
    if not content:
        return [""]
    return [content[i:i + part_chars] for i in range(0, len(content), part_chars)]


def required_file_parts_safe(
    session_id: str,
    *,
    file_part_chars: int = 9000,
) -> tuple[list[str], list[Any], list[Any], list[str]]:
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    required_files = lean_recommended_files_for_context(current, future)

    loaded_parts: list[Any] = []
    manifest: list[Any] = []
    missing_files: list[str] = []

    for file_path in required_files:
        content, source = read_required_file_for_bundle(file_path, session_id)
        if content is None:
            missing_files.append(file_path)
            manifest.append(ccp.RequiredFileManifestItem(path=file_path, exists=False, source="missing"))
            continue

        pieces = split_text_safe(content, file_part_chars)
        manifest.append(
            ccp.RequiredFileManifestItem(
                path=file_path,
                exists=True,
                source=source or "project",
                size_chars=len(content),
                parts_total=len(pieces),
            )
        )
        for index, piece in enumerate(pieces):
            loaded_parts.append(
                ccp.RequiredFileBundleItem(
                    path=file_path,
                    content=piece,
                    part_index=index,
                    parts_total=len(pieces),
                    content_chars=len(piece),
                )
            )

    return required_files, loaded_parts, manifest, missing_files


def chunk_loaded_parts_safe(
    loaded_parts: list[Any],
    *,
    max_chars: int = 24000,
    max_items: int = 3,
) -> list[list[Any]]:
    # Ignore dangerous caller values that can trigger ResponseTooLargeError.
    max_chars = max(12000, min(int(max_chars or 24000), 26000))
    max_items = max(1, min(int(max_items or 3), 3))

    chunks: list[list[Any]] = []
    current: list[Any] = []
    current_chars = 0

    for part in loaded_parts:
        part_chars = len(getattr(part, "content", "") or "")
        if current and (len(current) >= max_items or current_chars + part_chars > max_chars):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(part)
        current_chars += part_chars

    if current:
        chunks.append(current)
    return chunks


def required_files_chunk_response_safe(
    session_id: str,
    *,
    chunk_index: int = 0,
    max_chars: int = 24000,
    max_items: int = 3,
):
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)

    required_files, loaded_parts, _manifest, missing_files = required_file_parts_safe(sid)
    chunks = chunk_loaded_parts_safe(loaded_parts, max_chars=max_chars, max_items=max_items)
    chunks_total = len(chunks)

    safe_chunk_index = max(0, min(int(chunk_index or 0), max(chunks_total - 1, 0))) if chunks_total else 0
    selected = chunks[safe_chunk_index] if chunks_total else []
    has_more = bool(chunks_total and safe_chunk_index < chunks_total - 1)
    next_chunk_index = safe_chunk_index + 1 if has_more else None

    return ccp.RequiredFilesChunkResponse(
        session_id=sid,
        required_files=required_files,
        chunk_index=safe_chunk_index,
        chunks_total=chunks_total,
        has_more=has_more,
        next_chunk_index=next_chunk_index,
        loaded_files=selected,
        missing_files=missing_files,
        loaded_count=len({part.path for part in loaded_parts}),
        missing_count=len(missing_files),
        total_loaded_parts=len(loaded_parts),
    )


def deep_merge_roster_replace(dst: Any, src: Any) -> Any:
    if not isinstance(src, dict):
        return dst
    if not isinstance(dst, dict):
        dst = {}

    for key, value in src.items():
        if key in ROSTER_FIELDS and isinstance(value, list):
            dst[key] = _unique([str(v) for v in value if v is not None])
        elif isinstance(value, dict):
            dst[key] = deep_merge_roster_replace(dst.get(key, {}), value)
        elif isinstance(value, list):
            existing = dst.get(key, [])
            if not isinstance(existing, list):
                existing = []
            for item in value:
                if item not in existing:
                    existing.append(item)
            dst[key] = existing
        else:
            dst[key] = value
    return dst


class RepairSceneRosterRequest(BaseModel):
    active_character_ids: list[str] = Field(default_factory=lambda: ["akira", "livia"])
    nearby_character_ids: list[str] = Field(default_factory=list)
    speaking_character_ids: list[str] = Field(default_factory=list)
    observing_character_ids: list[str] = Field(default_factory=list)
    addressed_character_ids: list[str] = Field(default_factory=list)
    looked_at_character_ids: list[str] = Field(default_factory=list)
    mentioned_character_ids: list[str] = Field(default_factory=list)
    scheduled_character_ids: list[str] = Field(default_factory=list)
    delayed_character_ids: list[str] = Field(default_factory=list)


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


# Patch module globals used by compact_context_patch endpoints.
base.active_scene_characters = scene_character_ids
base.recommended_files_for_context = lean_recommended_files_for_context
base.compact_relationships = compact_relationships_scene_pairs_only
base.compact_knowledge = compact_knowledge_scene_only
base.compact_story_lines = compact_story_lines_scene_only
base.deep_merge = deep_merge_roster_replace

ccp.active_scene_characters = scene_character_ids
ccp.recommended_files_for_context = lean_recommended_files_for_context
ccp._read_required_file_for_bundle = read_required_file_for_bundle
ccp._split_text = split_text_safe
ccp._required_file_parts = required_file_parts_safe
ccp._chunk_loaded_parts = chunk_loaded_parts_safe
ccp._required_files_chunk_response = required_files_chunk_response_safe


# Re-register chunk endpoints with safe defaults and safe clamping.
_remove_routes("/api/v1/sessions/{session_id}/required-files-chunk", {"GET"}, "getRequiredFilesChunk")
_remove_routes("/api/v1/sessions/{session_id}/required-files-bundle", {"GET"}, "getRequiredFilesBundle")


@app.get("/api/v1/sessions/{session_id}/required-files-chunk", response_model=ccp.RequiredFilesChunkResponse, operation_id="getRequiredFilesChunk")
def get_required_files_chunk_safe(
    session_id: str,
    chunk_index: int = 0,
    max_chars: int = 24000,
    max_items: int = 3,
):
    return required_files_chunk_response_safe(
        session_id,
        chunk_index=chunk_index,
        max_chars=max_chars,
        max_items=max_items,
    )


@app.get("/api/v1/sessions/{session_id}/required-files-bundle", response_model=ccp.RequiredFilesChunkResponse, operation_id="getRequiredFilesBundle")
def get_required_files_bundle_safe(
    session_id: str,
    chunk_index: int = 0,
    max_chars: int = 24000,
    max_items: int = 3,
):
    return required_files_chunk_response_safe(
        session_id,
        chunk_index=chunk_index,
        max_chars=max_chars,
        max_items=max_items,
    )


@app.post("/api/v1/sessions/{session_id}/repair/scene-roster", operation_id="repairSceneRoster")
def repair_scene_roster(session_id: str, request: RepairSceneRosterRequest = RepairSceneRosterRequest()):
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)

    current = base.read_json("state/current_state.json", sid, default={}) or {}
    current["active_characters"] = _unique([canonical_id(x) for x in request.active_character_ids])
    current["nearby_characters"] = _unique([str(x) for x in request.nearby_character_ids])
    current["speaking_character_ids"] = _unique([canonical_id(x) for x in request.speaking_character_ids])
    current["observing_character_ids"] = _unique([canonical_id(x) for x in request.observing_character_ids])
    current["addressed_character_ids"] = _unique([canonical_id(x) for x in request.addressed_character_ids])
    current["looked_at_character_ids"] = _unique([canonical_id(x) for x in request.looked_at_character_ids])
    current["mentioned_character_ids"] = _unique([canonical_id(x) for x in request.mentioned_character_ids])
    current["scheduled_character_ids"] = _unique([canonical_id(x) for x in request.scheduled_character_ids])
    current["delayed_character_ids"] = _unique([canonical_id(x) for x in request.delayed_character_ids])

    base.write_json("state/current_state.json", current, sid)
    return {
        "status": "repaired",
        "session_id": sid,
        "changed_files": ["state/current_state.json"],
        "active_characters": current["active_characters"],
        "nearby_characters": current["nearby_characters"],
    }


# Re-register health to expose version for diagnostics.
_remove_routes("/health", {"GET"})


@app.get("/health")
def health_with_version():
    base.seed()
    return {
        "status": "ok",
        "app": base.APP_NAME,
        "version": app.version,
        "data_dir": str(base.DATA),
        "volume_seeded": (base.DATA / ".seeded").exists(),
        "public_base_url": base.BASE_URL,
    }
