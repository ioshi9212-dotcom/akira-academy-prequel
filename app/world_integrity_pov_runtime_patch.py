"""Safe world integrity + POV helpers v2.

Diagnostics only: no automatic risky mutation of current_state.
State persistence patch writes diagnostics into state/world_integrity_state.json.
"""
from __future__ import annotations
from typing import Any

TIME_ORDER = ["ночь", "раннее утро", "утро", "позднее утро", "полдень", "день", "послеобеденное время", "вечер", "поздний вечер", "отбой"]


def time_index(value: Any) -> int:
    text = str(value or "").lower()
    for idx, label in enumerate(TIME_ORDER):
        if label in text:
            return idx
    return -1


def analyze_world_continuity(current: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    issues = []
    if len(entries) >= 2:
        prev = entries[-2]
        latest = entries[-1]
        same_date = prev.get("current_date") and latest.get("current_date") and prev.get("current_date") == latest.get("current_date")
        prev_idx = time_index(prev.get("current_time"))
        latest_idx = time_index(latest.get("current_time"))
        if same_date and prev_idx >= 0 and latest_idx >= 0 and latest_idx < prev_idx:
            issues.append({"type": "time_rollback_suspected", "previous_time": prev.get("current_time"), "latest_time": latest.get("current_time"), "severity": "warning"})
    if not current.get("active_characters"):
        issues.append({"type": "empty_active_characters", "severity": "warning"})
    return {"status": "warning" if issues else "ok", "issues": issues, "rule": "Diagnostics only. Corrections must be saved through normal state payloads."}


def apply_pov_render_metadata(scene_meta: dict[str, Any], pov_character_id: str | None) -> dict[str, Any]:
    if not pov_character_id:
        return scene_meta
    scene_meta = dict(scene_meta or {})
    scene_meta["pov_mode"] = True
    scene_meta["pov_character_id"] = pov_character_id
    scene_meta["rule"] = "POV changes camera/voice only. State and relationships update normally from the scene."
    return scene_meta
