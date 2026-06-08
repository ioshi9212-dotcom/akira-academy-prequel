"""
Runtime context selector patch for akira-academy-prequel.

This module intentionally does NOT replace app.compact.
It imports the existing working app.compact and patches only context file selection:
- clean YAML character folders first;
- old characters/main/*.md only as fallback;
- scheduled/mentioned/delayed ids supported when already present in state/calendar-derived state.

No new locks. No heavy lore auto-load.
"""

from __future__ import annotations

from typing import Any

from app import compact as base

app = base.app

NEW_CHARACTER_FOLDERS: dict[str, str] = {
    "akira": "akira",
    "char_akira": "akira",

    "livia": "livia",
    "livia_cross": "livia",
    "char_livia": "livia",

    "kir": "kir",
    "kir_knox": "kir",
    "char_kir": "kir",

    "haru": "haru",
    "haru_foster": "haru",
    "char_haru": "haru",

    "raiden": "raiden",
    "raiden_sterling": "raiden",
    "char_raiden": "raiden",

    "kiara": "kiara",
    "kiara_volt": "kiara",
    "char_kiara": "kiara",

    "kael": "kael_north",
    "kael_north": "kael_north",
    "char_kael_north": "kael_north",
}


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value).strip() if value else ""
        if item and item not in result:
            result.append(item)
    return result


def character_files_for(character_id: str) -> list[str]:
    """
    Prefer clean YAML character folders. Use legacy md only if clean YAML files do not exist.
    """
    cid = str(character_id).strip()
    files: list[str] = []

    folder = NEW_CHARACTER_FOLDERS.get(cid)
    if folder:
        for rel in (
            f"characters/{folder}/main.yaml",
            f"characters/{folder}/character.yaml",
            f"characters/{folder}/past.yaml",
        ):
            if base.repo_file_exists(rel):
                files.append(rel)

    if files:
        return _unique(files)

    legacy = base.MAIN_CHARACTER_FILES.get(cid)
    if legacy and base.repo_file_exists(legacy):
        return [legacy]

    npc = f"characters/npc/{cid}.md"
    if base.repo_file_exists(npc):
        return [npc]

    return []


def character_file(character_id: str) -> str:
    files = character_files_for(character_id)
    if files:
        return files[0]
    return base.MAIN_CHARACTER_FILES.get(character_id, f"characters/npc/{character_id}.md")


def active_scene_characters(current: dict[str, Any], future: dict[str, Any] | None = None) -> list[str]:
    """
    Keep old behavior, but also accept ids already prepared by calendar/state:
    scheduled_character_ids, mentioned_character_ids, delayed_character_ids.
    This does not force Kir or anyone else by itself.
    """
    future = future or {}

    active = list(current.get("active_characters", []) or [])
    nearby = list(current.get("nearby_characters", []) or [])
    speaking = list(current.get("speaking_character_ids", []) or [])
    observing = list(current.get("observing_character_ids", []) or [])
    addressed = list(current.get("addressed_character_ids", []) or [])
    looked_at = list(current.get("looked_at_character_ids", []) or [])

    scheduled = list(current.get("scheduled_character_ids", []) or current.get("scheduled_characters", []) or [])
    mentioned = list(current.get("mentioned_character_ids", []) or current.get("mentioned_characters", []) or [])
    delayed = list(current.get("delayed_character_ids", []) or current.get("delayed_characters", []) or [])

    triggered: list[str] = []
    for thread in current.get("open_threads", []) or []:
        if isinstance(thread, dict) and thread.get("status") in {"due", "active", "triggered"}:
            triggered.extend(thread.get("participants", []) or [])

    for lock in (future.get("locks") or {}).values():
        if isinstance(lock, dict) and lock.get("status") in {"due", "active", "triggered"}:
            triggered.extend(lock.get("participants", []) or [])

    return _unique(["akira"] + active + nearby + speaking + observing + addressed + looked_at + scheduled + mentioned + delayed + triggered)


def recommended_files_for_context(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    """
    Same contract as base.recommended_files_for_context, but with clean YAML character folders.
    No heavy lore auto-load. No new locks.
    """
    current = current or {}
    future = future or {}
    scene_chars = active_scene_characters(current, future)

    character_files: list[str] = []
    for cid in scene_chars:
        character_files.extend(character_files_for(cid))

    akira_profile_files: list[str] = []
    profile_id = current.get("akira_behavior_profile")
    profiles = current.get("akira_behavior_profiles") or {}
    if profile_id and isinstance(profiles, dict):
        profile_file = profiles.get(profile_id)
        if profile_file and base.repo_file_exists(profile_file):
            akira_profile_files.append(profile_file)

    files = _unique(
        base.CORE_RECOMMENDED_FILES
        + base.CORE_LOCK_FILES
        + character_files
        + akira_profile_files
        + base.character_lock_files(scene_chars)
        + base.DEFAULT_STATE_FILES
    )
    return [path for path in files if base.repo_file_exists(path)]


def base_recommended_files() -> list[str]:
    return recommended_files_for_context({"active_characters": ["akira"]}, {})


# Monkey-patch only the selector functions used by /context and /turn-contract.
base.character_files_for = character_files_for
base.character_file = character_file
base.active_scene_characters = active_scene_characters
base.recommended_files_for_context = recommended_files_for_context
base.base_recommended_files = base_recommended_files
