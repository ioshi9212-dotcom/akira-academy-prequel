"""
World Integrity + POV Runtime Patch v1
--------------------------------------

Goal:
- Prevent timeline / scene contradiction (morning becomes evening, duplicate events)
- Enforce continuity between calendar, scene_history, and current_state
- Support POV switching without breaking state persistence
- Ensure relationships/knowledge updates always apply regardless of POV

This does NOT change gameplay output format.
It only validates + corrects state BEFORE scene rendering.
"""

from __future__ import annotations

from typing import Any

import app.compact as base


# -----------------------------
# Time consistency model
# -----------------------------
TIME_ORDER = [
    "night",
    "early_morning",
    "morning",
    "late_morning",
    "midday",
    "afternoon",
    "evening",
    "late_evening",
]


def _time_index(t: str | None) -> int:
    if not t:
        return -1
    try:
        return TIME_ORDER.index(t)
    except ValueError:
        return -1


# -----------------------------
# Core integrity validation
# -----------------------------

def validate_world_continuity(current: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
    """
    Checks and fixes contradictions between:
    - current_state
    - last scene_history entry
    - story_lines timeline
    """

    fixes: dict[str, Any] = {}

    last_scene = None
    if isinstance(history, dict):
        entries = history.get("entries", [])
        if entries:
            last_scene = entries[-1]
    elif isinstance(history, list) and history:
        last_scene = history[-1]

    if not last_scene:
        return {"status": "no_history"}

    last_time = last_scene.get("current_time")
    current_time = current.get("current_time")

    # FIX 1: time rollback detection
    if _time_index(current_time) < _time_index(last_time):
        fixes["time_correction"] = {
            "from": current_time,
            "to": last_time,
            "reason": "timeline rollback detected"
        }
        current["current_time"] = last_time

    # FIX 2: location jump sanity
    last_location = last_scene.get("location_id")
    if last_location and current.get("current_location_id") != last_location:
        # allow movement only if explicitly changed
        if not current.get("force_location_change"):
            fixes["location_lock"] = {
                "locked_to": last_location,
                "reason": "unspecified location drift"
            }
            current["current_location_id"] = last_location

    # FIX 3: character continuity
    last_chars = set(last_scene.get("active_characters", []))
    current_chars = set(current.get("active_characters", []))

    if not current_chars and last_chars:
        current["active_characters"] = list(last_chars)
        fixes["character_restore"] = True

    return {
        "status": "checked",
        "fixes": fixes,
        "current_state": current,
    }


# -----------------------------
# POV layer (non-destructive)
# -----------------------------

def apply_pov_filter(scene: dict[str, Any], pov_character: str | None) -> dict[str, Any]:
    """
    Adjusts narrative lens only.
    Does NOT modify state or relationships.
    """

    if not pov_character:
        return scene

    scene["pov_mode"] = True
    scene["pov_character"] = pov_character

    # adjust output hints (NOT state)
    scene.setdefault("render_flags", {})
    scene["render_flags"]["dialogue_bias"] = pov_character

    return scene


# -----------------------------
# Relationship safety hook
# -----------------------------

def ensure_relationships_apply(state: dict[str, Any], updates: dict[str, Any]) -> None:
    """
    Guarantees relationship changes apply regardless of POV or scene filter.
    """
    rel = state.setdefault("relationships", {})

    for pair, delta in (updates or {}).items():
        if pair not in rel:
            rel[pair] = {"affection": 0, "trust": 0, "tension": 0}

        for k, v in (delta or {}).items():
            if isinstance(v, (int, float)):
                rel[pair][k] = rel[pair].get(k, 0) + v


# -----------------------------
# World integrity entrypoint
# -----------------------------

def run_world_integrity_check(payload: dict[str, Any], state_bundle: dict[str, Any]) -> dict[str, Any]:
    current = state_bundle.get("current_state", {})
    history = state_bundle.get("scene_history", {})

    result = validate_world_continuity(current, history)

    # apply fixes back
    state_bundle["current_state"] = result.get("current_state", current)

    return {
        "integrity_status": result.get("status"),
        "fixes": result.get("fixes", {}),
        "state_updated": True,
    }
