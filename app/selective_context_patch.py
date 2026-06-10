"""
Selective context runtime patch for akira-academy-prequel.

Goal:
- keep gameplay context below ~24 chunks by default;
- load only scene-relevant characters, relationship pairs, story lines, knowledge and calendar slices;
- keep full-context mode available for diagnostics through current_state flags.

This patch is intentionally a thin runtime layer. It imports the previous state-write
patch if present, otherwise falls back to compact_context_patch.
"""
from __future__ import annotations

import json
import math
from itertools import combinations
from typing import Any

# Preserve previous runtime/state-write patch if it exists.
try:  # pragma: no cover - runtime optional import
    from app import state_write_runtime_patch as runtime  # type: ignore
except Exception:  # pragma: no cover
    from app import compact_context_patch as runtime  # type: ignore

from app import compact as base

app = runtime.app
app.version = "0.3.17-selective-context"

RUNTIME_DIGEST_FILE = "runtime/scene_context_digest.md"
SELECTIVE_CONTEXT_LOCK_FILE = "gpt/locks/selective_context_runtime_lock.md"
STATE_UPDATE_CONTRACT_FILE = "gpt/locks/state_update_payload_contract.md"

# Target: not a hard truncation of important active data, but prevent 50+ chunks in normal play.
TARGET_MAX_CHUNKS = 24
DEFAULT_PART_CHARS = int(getattr(runtime, "DEFAULT_FILE_PART_CHARS", 12000) or 12000)

CANONICAL_ID_ALIASES: dict[str, str] = {
    "char_akira": "akira",
    "akira": "akira",
    "livia_cross": "livia",
    "livia": "livia",
    "char_livia": "livia",
    "kir_knox": "kir",
    "kir": "kir",
    "char_kir": "kir",
    "haru_foster": "haru",
    "haru": "haru",
    "char_haru": "haru",
    "raiden_sterling": "raiden",
    "raiden": "raiden",
    "char_raiden": "raiden",
    "kiara_volt": "kiara",
    "kiara": "kiara",
    "char_kiara": "kiara",
    "kael": "kael_north",
    "north": "kael_north",
    "kael_north": "kael_north",
    "char_kael_north": "kael_north",
    "asher_lane": "asher",
    "asher": "asher",
    "kai_renwick": "kai",
    "kai": "kai",
}

CHARACTER_FOLDER_BY_CANON: dict[str, str] = {
    "akira": "akira",
    "livia": "livia",
    "kir": "kir",
    "haru": "haru",
    "raiden": "raiden",
    "kiara": "kiara",
    "kael_north": "kael_north",
}

MINIMAL_GAMEPLAY_FILES = [
    "gpt/engine_prompt.md",
    "gpt/scene_format.md",
    "gpt/locks/gameplay_response_gate.md",
    "gpt/locks/player_input_anchor_lock.md",
    "gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md",
    "gpt/locks/dialogue_format_strict_lock.md",
    "gpt/locks/no_empty_scenes_lock.md",
    "gpt/locks/apply_state_after_turn_lock.md",
    STATE_UPDATE_CONTRACT_FILE,
    SELECTIVE_CONTEXT_LOCK_FILE,
    "canon/source_usage_rules.md",
    "canon/relationship_memory_rules.md",
    "characters/character_id_index.md",
    RUNTIME_DIGEST_FILE,
]

OPTIONAL_SCENE_FILES = [
    "canon/character_story_roles.md",
    "canon/academy_rules_index.md",
    "canon/academy_combat_and_weapon_rules.md",
    "canon/character_depth_and_rotation.md",
    "gpt/locks/story_lines_memory_lock.md",
    "gpt/locks/character_presence_rotation_lock.md",
]


def canonical_id(value: Any) -> str:
    raw = str(value or "").strip()
    return CANONICAL_ID_ALIASES.get(raw, raw)


def unique(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        item = canonical_id(value)
        if item and item not in out:
            out.append(item)
    return out


def full_context_requested(current: dict[str, Any]) -> bool:
    return bool(
        current.get("force_full_context")
        or current.get("context_mode") in {"full", "diagnostic", "debug"}
        or current.get("debug_full_required_files")
    )


def active_scene_characters(current: dict[str, Any], future: dict[str, Any] | None = None) -> list[str]:
    future = future or {}
    values: list[Any] = []
    for key in [
        "active_characters", "nearby_characters", "speaking_character_ids",
        "observing_character_ids", "addressed_character_ids", "looked_at_character_ids",
        "scheduled_character_ids", "scheduled_characters", "mentioned_character_ids",
        "mentioned_characters", "delayed_character_ids", "delayed_characters",
    ]:
        current_values = current.get(key, []) or []
        if isinstance(current_values, list):
            values.extend(current_values)

    for thread in current.get("open_threads", []) or []:
        if isinstance(thread, dict) and thread.get("status") in {"due", "active", "triggered"}:
            values.extend(thread.get("participants", []) or [])

    for lock in (future.get("locks") or {}).values():
        if isinstance(lock, dict) and lock.get("status") in {"due", "active", "triggered"}:
            values.extend(lock.get("participants", []) or [])

    return unique(["akira"] + values)


def scene_character_files(scene_chars: list[str]) -> list[str]:
    files: list[str] = []
    for cid in scene_chars:
        folder = CHARACTER_FOLDER_BY_CANON.get(canonical_id(cid))
        if not folder:
            # fallback to existing runtime resolver if this is a secondary/NPC id
            try:
                files.extend(runtime.character_files_for(cid))
            except Exception:
                pass
            continue
        # main.yaml is usually short but important; character.yaml is behavior; past.yaml is triggers/knowledge.
        for rel in (
            f"characters/{folder}/main.yaml",
            f"characters/{folder}/character.yaml",
            f"characters/{folder}/past.yaml",
        ):
            if base.repo_file_exists(rel):
                files.append(rel)
    return unique(files)


def estimate_file_parts(path: str) -> int:
    if path == RUNTIME_DIGEST_FILE:
        # digest is dynamic; reserve enough room for a useful state slice.
        return 2
    try:
        if path.startswith("state/"):
            content = base.read_text(path)
        else:
            content = base.read_text(path)
        return max(1, math.ceil(len(content) / DEFAULT_PART_CHARS))
    except Exception:
        return 1


def keep_with_budget(paths: list[str], *, budget: int = TARGET_MAX_CHUNKS) -> list[str]:
    kept: list[str] = []
    parts = 0
    for path in unique(paths):
        if path != RUNTIME_DIGEST_FILE and not base.repo_file_exists(path):
            continue
        cost = estimate_file_parts(path)
        if kept and parts + cost > budget:
            continue
        kept.append(path)
        parts += cost
    return kept


def recommended_files_for_context(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    current = current or {}
    future = future or {}

    # Explicit diagnostic mode preserves original heavy behavior.
    if full_context_requested(current):
        return runtime.recommended_files_for_context(current, future)

    scene_chars = active_scene_characters(current, future)

    profile_files: list[str] = []
    profile_id = current.get("akira_behavior_profile")
    profiles = current.get("akira_behavior_profiles") or {}
    if profile_id and isinstance(profiles, dict):
        profile_file = profiles.get(profile_id)
        if profile_file and base.repo_file_exists(profile_file):
            profile_files.append(profile_file)

    # Priority order matters. Character files and digest are kept before optional global lore.
    priority_files = (
        MINIMAL_GAMEPLAY_FILES
        + scene_character_files(scene_chars)
        + profile_files
        + OPTIONAL_SCENE_FILES
    )
    return keep_with_budget(priority_files, budget=TARGET_MAX_CHUNKS)


def pair_parts(pair_id: str) -> list[str]:
    return [canonical_id(part) for part in str(pair_id).split("__") if part]


def pair_in_focus(pair_id: str, focus_ids: set[str]) -> bool:
    parts = pair_parts(pair_id)
    return bool(parts and all(part in focus_ids for part in parts))


def compact_relationships(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = set(unique(focus_ids or ["akira"]))
    pairs = state.get("pairs")
    if isinstance(pairs, dict):
        filtered = {pair: data for pair, data in pairs.items() if pair_in_focus(str(pair), focus)}
        return {
            "pairs": filtered,
            "_context_filter": {
                "mode": "selective_scene_pairs_only",
                "focus_character_ids": sorted(focus),
                "visible_pairs": len(filtered),
                "total_pairs": len(pairs),
                "note": "Only relationships between characters in the current scene are shown. Use /json/state/relationships.json for full memory.",
            },
        }
    return state


def compact_story_lines(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = set(unique(focus_ids or ["akira"]))
    lines = state.get("lines") or state.get("active_lines")
    visible: dict[str, Any] = {}
    if isinstance(lines, dict):
        for line_id, line in lines.items():
            if not isinstance(line, dict):
                continue
            ids = set(unique(list(line.get("character_ids", []) or []) + list(line.get("related_ids", []) or []) + list(line.get("characters", []) or []) + list(line.get("participants", []) or [])))
            if ids & focus or str(line_id) in {"academy_arrival", "line_academy", "line_reputation", "line_social_media_rumors", "line_obligations"}:
                visible[str(line_id)] = line

    shared_events = state.get("shared_events", [])
    visible_events: list[Any] = []
    if isinstance(shared_events, list):
        for event in shared_events:
            if not isinstance(event, dict):
                continue
            ids = set(unique(list(event.get("participants", []) or []) + list(event.get("witnesses", []) or []) + list(event.get("heard_by", []) or []) + list(event.get("known_by", []) or [])))
            if ids & focus:
                visible_events.append(event)
        visible_events = visible_events[-12:]

    return {
        "schema": state.get("schema"),
        "turn_counter": state.get("turn_counter", {}),
        "calendar_policy": state.get("calendar_policy", {}),
        "shared_events_recent": visible_events,
        "lines": visible,
        "next_beats": state.get("next_beats", [])[:10] if isinstance(state.get("next_beats"), list) else state.get("next_beats", {}),
        "_context_filter": {
            "mode": "selective_scene_story_lines_only",
            "focus_character_ids": sorted(focus),
            "visible_lines": list(visible.keys()),
            "total_lines": len(lines) if isinstance(lines, dict) else 0,
            "note": "Only global/scene-related lines are shown. Use /json/state/story_lines.json for full memory.",
        },
    }


def compact_knowledge(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = set(unique(focus_ids or ["akira"]))
    filtered = {canonical_id(cid): data for cid, data in state.items() if canonical_id(cid) in focus}
    return {
        **filtered,
        "_context_filter": {
            "mode": "selective_scene_knowledge_only",
            "focus_character_ids": sorted(focus),
            "visible_characters": len([k for k in filtered if k != "_context_filter"]),
            "total_characters": len(state),
            "note": "Only knowledge for current scene characters is shown. Use /json/state/knowledge_state.json for full memory.",
        },
    }


def truncate(value: Any, max_chars: int = 7000) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... <truncated by selective context>"


def build_scene_context_digest(session_id: str) -> str:
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    story = base.read_json("state/story_lines.json", session_id, default={}) or {}
    relationships = base.read_json("state/relationships.json", session_id, default={}) or {}
    knowledge = base.read_json("state/knowledge_state.json", session_id, default={}) or {}
    schedule = base.read_json("state/academy_schedule.json", session_id, default={}) or {}

    scene_chars = active_scene_characters(current, future)
    rel_slice = compact_relationships(relationships, scene_chars)
    story_slice = compact_story_lines(story, scene_chars)
    knowledge_slice = compact_knowledge(knowledge, scene_chars)

    parts = [
        "# Runtime scene context digest",
        "",
        "This file is generated at request time by selective_context_patch.",
        "It replaces the need to load full state files in normal gameplay.",
        "",
        "## Scene characters",
        truncate(scene_chars, 2000),
        "",
        "## Current state",
        truncate(current, 5000),
        "",
        "## Relationship slice — only pairs where both sides are in scene focus",
        truncate(rel_slice, 8000),
        "",
        "## Story lines slice — global + scene/date/participant relevant",
        truncate(story_slice, 9000),
        "",
        "## Knowledge slice — only scene characters",
        truncate(knowledge_slice, 7000),
        "",
        "## Future locks slice",
        truncate(future, 5000),
        "",
        "## Calendar slice",
        truncate(schedule, 4000),
        "",
        "## State update reminder",
        "After gameplay scene, if anything changed, apply-turn-result payload must include relationship_changes/story_lines_changes/knowledge_changes/current_state_changes as needed.",
        "If apply-turn-result returns no_changes_detected after a meaningful scene, the turn is technically unfinished.",
    ]
    return "\n".join(parts) + "\n"


_ORIGINAL_READ_REQUIRED_FILE = runtime._read_required_file_for_bundle


def _read_required_file_for_bundle(path: str, session_id: str) -> tuple[str | None, str | None]:
    if str(path).strip() == RUNTIME_DIGEST_FILE:
        return build_scene_context_digest(session_id), "runtime"
    return _ORIGINAL_READ_REQUIRED_FILE(path, session_id)


# Patch runtime + base selectors used by /context, /turn-contract, required-files manifest/chunks.
runtime.active_scene_characters = active_scene_characters
runtime.recommended_files_for_context = recommended_files_for_context
runtime.compact_relationships = compact_relationships
runtime.compact_story_lines = compact_story_lines
runtime.compact_knowledge = compact_knowledge
runtime._read_required_file_for_bundle = _read_required_file_for_bundle

base.active_scene_characters = active_scene_characters
base.recommended_files_for_context = recommended_files_for_context
base.compact_relationships = compact_relationships
base.compact_story_lines = compact_story_lines
base.compact_knowledge = compact_knowledge


def patch_after_routes() -> None:
    # Keep compatibility with app.session_routes if it exists.
    try:
        runtime.patch_after_routes()
    except Exception:
        pass
    try:
        import app.session_routes as routes  # type: ignore
    except Exception:
        return
    routes.active_scene_characters = active_scene_characters
    routes.recommended_files_for_context = recommended_files_for_context


patch_after_routes()
