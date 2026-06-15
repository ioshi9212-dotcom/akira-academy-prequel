"""
Runtime state persistence patch v1.

Fixes:
- relationship_changes with nested pairs/deltas;
- state/scene_history.json append on gameplay apply;
- state/calendar_runtime.json section support;
- richer state/last_apply_result.json diagnostics.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import app.compact_context_patch as ccp
from app.compact_context_patch import app
from app import compact as base

APPLY_TURN_RESULT_PATH = ccp.APPLY_TURN_RESULT_PATH
LAST_APPLY_RESULT_FILE = "state/last_apply_result.json"
SCENE_HISTORY_FILE = "state/scene_history.json"
CALENDAR_RUNTIME_FILE = "state/calendar_runtime.json"

ID_ALIASES = {
    "akira": "akira", "char_akira": "akira",
    "livia": "livia", "livia_cross": "livia", "char_livia": "livia",
    "kir": "kir", "kir_knox": "kir", "char_kir": "kir",
    "haru": "haru", "haru_foster": "haru", "char_haru": "haru",
    "raiden": "raiden", "raiden_sterling": "raiden", "char_raiden": "raiden",
    "kiara": "kiara", "kiara_volt": "kiara", "char_kiara": "kiara",
    "kael": "kael_north", "kael_north": "kael_north", "north": "kael_north", "char_kael_north": "kael_north",
}

REL_METRICS = list(getattr(base, "REL_METRICS", ["affection", "trust", "tension", "jealousy", "respect", "curiosity", "resentment"]))

EXTRA_STATE_SECTION_MAP = [
    (CALENDAR_RUNTIME_FILE, ["calendar_runtime_changes", "calendar_runtime", "calendar_changes"]),
]


def canonical_id(value: Any) -> str:
    item = str(value or "").strip()
    return ID_ALIASES.get(item, item)


def pair_parts(pair_id: str) -> list[str]:
    return [part for part in str(pair_id).split("__") if part]


def same_pair(a: str, b: str) -> bool:
    a_parts = [canonical_id(p) for p in pair_parts(a)]
    b_parts = [canonical_id(p) for p in pair_parts(b)]
    return len(a_parts) == 2 and len(b_parts) == 2 and set(a_parts) == set(b_parts)


def resolve_relationship_pair_key(pairs: dict[str, Any], requested_pair: str) -> str:
    requested_pair = str(requested_pair).strip()
    if requested_pair in pairs:
        return requested_pair
    for existing_pair in pairs.keys():
        if same_pair(str(existing_pair), requested_pair):
            return str(existing_pair)
    parts = pair_parts(requested_pair)
    if len(parts) == 2:
        return f"{canonical_id(parts[0])}__{canonical_id(parts[1])}"
    return requested_pair


def find_section(payload: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in payload:
            return payload[name]
    data = payload.get("data")
    if isinstance(data, dict):
        for name in names:
            if name in data:
                return data[name]
    return None


def default_relationship(status: str = "отношения появились после сцены") -> dict[str, Any]:
    if hasattr(base, "default_relationship"):
        return base.default_relationship(status)
    data = {metric: 0 for metric in REL_METRICS}
    data.update({
        "status": status,
        "notes": [],
        "memory": [],
        "open_threads": [],
        "behavior_next": [],
        "triggers": [],
        "last_interaction": None,
    })
    return data


def merge_unique_list(rel: dict[str, Any], field: str, value: Any) -> bool:
    if value is None:
        return False
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list):
        return False
    target = rel.setdefault(field, [])
    if not isinstance(target, list):
        target = []
        rel[field] = target
    changed = False
    for item in items:
        if item and item not in target:
            target.append(item)
            changed = True
    return changed


def normalize_relationship_items(section: Any) -> list[dict[str, Any]]:
    if not section:
        return []

    if isinstance(section, list):
        return [item for item in section if isinstance(item, dict)]

    if not isinstance(section, dict):
        return []

    if isinstance(section.get("changes"), list):
        return [item for item in section["changes"] if isinstance(item, dict)]

    if isinstance(section.get("items"), list):
        return [item for item in section["items"] if isinstance(item, dict)]

    if isinstance(section.get("pairs"), dict):
        items: list[dict[str, Any]] = []
        for pair_id, value in section["pairs"].items():
            if isinstance(value, dict):
                items.append({"pair_id": pair_id, **value})
        return items

    if any(key in section for key in ["pair", "pair_id", "id"]):
        return [section]

    items: list[dict[str, Any]] = []
    for key, value in section.items():
        if "__" in str(key) and isinstance(value, dict):
            items.append({"pair_id": key, **value})
    return items


def apply_relationship_changes_robust(session_id: str, payload: dict[str, Any], dry_run: bool) -> bool:
    section = find_section(payload, ["relationship_changes", "relationships_changes", "relationship_deltas", "relationships"])
    items = normalize_relationship_items(section)
    if not items:
        return False

    state = base.read_json("state/relationships.json", session_id, default={}) or {}
    pairs = state.setdefault("pairs", {})
    changed = False

    for item in items:
        pair = item.get("pair") or item.get("pair_id") or item.get("id")
        if isinstance(pair, list) and len(pair) == 2:
            pair = f"{pair[0]}__{pair[1]}"
        if not pair or "__" not in str(pair):
            continue

        pair_key = resolve_relationship_pair_key(pairs, str(pair))
        rel = pairs.setdefault(pair_key, default_relationship())

        deltas = item.get("deltas") if isinstance(item.get("deltas"), dict) else {}
        values = item.get("values") if isinstance(item.get("values"), dict) else {}

        for metric in REL_METRICS:
            delta_key = f"{metric}_delta"
            delta_value = item.get(delta_key, deltas.get(metric, deltas.get(delta_key)))
            if delta_value is not None:
                rel[metric] = max(0, min(100, int(rel.get(metric, 0)) + int(delta_value or 0)))
                changed = True
                continue
            absolute_value = item.get(metric, values.get(metric))
            if isinstance(absolute_value, int):
                rel[metric] = max(0, min(100, int(absolute_value)))
                changed = True

        if isinstance(item.get("status"), str):
            rel["status"] = item["status"]
            changed = True

        notes = item.get("notes") or item.get("add_notes") or item.get("note")
        if merge_unique_list(rel, "notes", notes):
            changed = True

        for field in ["memory", "open_threads", "behavior_next", "triggers"]:
            value = item.get(field) or item.get(f"add_{field}")
            if merge_unique_list(rel, field, value):
                changed = True

        if item.get("last_interaction") is not None:
            rel["last_interaction"] = item.get("last_interaction")
            changed = True

    if changed and not dry_run:
        base.write_json("state/relationships.json", state, session_id)
    return changed


def apply_json_section_robust(session_id: str, payload: dict[str, Any], file_path: str, names: list[str], dry_run: bool) -> bool:
    section = find_section(payload, names)
    if not isinstance(section, dict) or not section:
        return False
    state = base.read_json(file_path, session_id, default={}) or {}
    old_dump = json.dumps(state, ensure_ascii=False, sort_keys=True)
    new_state = base.deep_merge(state, section)
    new_dump = json.dumps(new_state, ensure_ascii=False, sort_keys=True)
    if new_dump != old_dump:
        if not dry_run:
            base.write_json(file_path, new_state, session_id)
        return True
    return False


def payload_section_summary(payload: dict[str, Any]) -> dict[str, bool]:
    return {
        "relationship_changes": bool(find_section(payload, ["relationship_changes", "relationships_changes", "relationship_deltas", "relationships"])),
        "story_lines_changes": bool(find_section(payload, ["story_lines_changes", "story_line_changes", "story_lines", "story_lines_state"])),
        "knowledge_changes": bool(find_section(payload, ["knowledge_changes", "knowledge_state_changes", "knowledge_state"])),
        "current_state_changes": bool(find_section(payload, ["current_state_changes", "current_state", "state_changes"])),
        "reputation_changes": bool(find_section(payload, ["reputation_changes", "reputation_state_changes", "reputation_state"])),
        "rumors_changes": bool(find_section(payload, ["rumor_changes", "rumors_changes", "rumors_state_changes", "rumors_state"])),
        "inventory_changes": bool(find_section(payload, ["inventory_changes", "inventory_state_changes", "inventory_state"])),
        "future_locks_changes": bool(find_section(payload, ["future_locks_changes", "future_locks_progress_changes", "future_locks_progress"])),
        "calendar_runtime_changes": bool(find_section(payload, ["calendar_runtime_changes", "calendar_runtime", "calendar_changes"])),
    }


def extract_scene_text(request: ccp.ApplyTurnResultWithVisibleSceneRequest, payload: dict[str, Any]) -> str:
    candidates = [
        request.visible_scene_text,
        payload.get("visible_scene_text"),
        payload.get("final_scene_text"),
        payload.get("scene_text"),
    ]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("visible_scene_text"), data.get("final_scene_text"), data.get("scene_text")])
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def append_scene_history(session_id: str, payload: dict[str, Any], scene_text: str, changed_files: list[str], dry_run: bool) -> bool:
    if dry_run or not scene_text:
        return False

    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    story = base.read_json("state/story_lines.json", session_id, default={}) or {}
    counter = story.get("turn_counter", {}) if isinstance(story, dict) else {}
    turn_number = 0
    if isinstance(counter, dict):
        for key in ["game_turn_number", "total_game_turns", "game_turn", "turn_number", "scene_count"]:
            try:
                turn_number = int(counter.get(key) or 0)
            except Exception:
                turn_number = 0
            if turn_number:
                break

    player_input = current.get("last_player_input") or payload.get("player_input") or ""
    entry = {
        "id": f"scene_{turn_number or 'unknown'}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "kind": "gameplay",
        "is_gameplay": True,
        "turn_number": turn_number or None,
        "created_at": datetime.utcnow().isoformat(),
        "current_date": current.get("current_date"),
        "current_time": current.get("current_time"),
        "location_id": current.get("current_location_id"),
        "location_text": current.get("current_location_text"),
        "active_characters": current.get("active_characters", []),
        "nearby_characters": current.get("nearby_characters", []),
        "player_input": player_input,
        "visible_scene_text": scene_text,
        "scene_text": scene_text,
        "changed_files_snapshot": list(changed_files),
    }

    history = base.read_json(SCENE_HISTORY_FILE, session_id, default={"schema": "scene_history_v2", "entries": []})
    if isinstance(history, list):
        if history and isinstance(history[-1], dict) and history[-1].get("visible_scene_text") == scene_text:
            return False
        history.append(entry)
        base.write_json(SCENE_HISTORY_FILE, history, session_id)
        return True

    if not isinstance(history, dict):
        history = {"schema": "scene_history_v2", "entries": []}
    entries = history.setdefault("entries", [])
    if not isinstance(entries, list):
        entries = []
        history["entries"] = entries
    if entries and isinstance(entries[-1], dict) and entries[-1].get("visible_scene_text") == scene_text:
        return False
    entries.append(entry)
    history["schema"] = history.get("schema") or "scene_history_v2"
    history["total_entries"] = len(entries)
    history["last_updated_at"] = datetime.utcnow().isoformat()
    base.write_json(SCENE_HISTORY_FILE, history, session_id)
    return True


def remove_route(path: str, method: str = "POST", operation_id: str | None = None) -> None:
    keep = []
    for route in app.router.routes:
        if getattr(route, "path", None) == path and method in (getattr(route, "methods", set()) or set()):
            if operation_id is None or getattr(route, "operation_id", None) == operation_id:
                continue
        keep.append(route)
    app.router.routes = keep


base.apply_relationship_changes = apply_relationship_changes_robust

remove_route(APPLY_TURN_RESULT_PATH, "POST")


@app.post(APPLY_TURN_RESULT_PATH, response_model=ccp.ApplyTurnResultWithVisibleSceneResponse, operation_id="applyTurnResult")
def apply_turn_result_persistent(
    session_id: str,
    request: ccp.ApplyTurnResultWithVisibleSceneRequest = ccp.ApplyTurnResultWithVisibleSceneRequest(),
) -> ccp.ApplyTurnResultWithVisibleSceneResponse:
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)
    source, payload = base.read_turn_payload(sid, request)
    changed_files: list[str] = []

    if apply_relationship_changes_robust(sid, payload, request.dry_run):
        changed_files.append("state/relationships.json")

    for path, names in list(base.STATE_SECTION_MAP) + EXTRA_STATE_SECTION_MAP:
        if apply_json_section_robust(sid, payload, path, names, request.dry_run):
            changed_files.append(path)

    scene_text = extract_scene_text(request, payload)
    if append_scene_history(sid, payload, scene_text, changed_files, request.dry_run):
        changed_files.append(SCENE_HISTORY_FILE)

    section_summary = payload_section_summary(payload)
    status = "applied" if changed_files else "no_changes_detected"
    warning = None
    if section_summary.get("relationship_changes") and "state/relationships.json" not in changed_files:
        warning = "relationship_changes section was present, but no valid pair delta/item was applied."
    if scene_text and SCENE_HISTORY_FILE not in changed_files:
        warning = (warning + " " if warning else "") + "visible_scene_text was present but scene_history was not changed, likely duplicate scene text."

    last_apply_result = {
        "status": status,
        "session_id": sid,
        "source": source,
        "dry_run": request.dry_run,
        "changed_files": changed_files,
        "payload_sections_present": section_summary,
        "scene_history_written": SCENE_HISTORY_FILE in changed_files,
        "relationship_state_written": "state/relationships.json" in changed_files,
        "state_write_warning": warning,
    }
    if not request.dry_run:
        base.write_json(LAST_APPLY_RESULT_FILE, last_apply_result, sid)
        if LAST_APPLY_RESULT_FILE not in changed_files:
            changed_files.append(LAST_APPLY_RESULT_FILE)

    return ccp.ApplyTurnResultWithVisibleSceneResponse(
        status="applied" if changed_files else status,
        session_id=sid,
        source=source,
        dry_run=request.dry_run,
        changed_files=changed_files,
        visible_scene_text=scene_text or request.visible_scene_text,
        final_scene_text=scene_text or request.visible_scene_text,
        render_packet_received=isinstance(request.render_packet, dict),
    )


app.version = "0.3.45-state-persistence-v1"
