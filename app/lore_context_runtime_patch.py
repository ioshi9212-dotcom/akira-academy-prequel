"""Lore context runtime patch v19: compact academy lore, no automatic hidden-relationship lore."""
from __future__ import annotations
import json
from typing import Any
import app.context_transport_runtime_patch as rt
from app.context_transport_runtime_patch import app
from app import compact as base
import app.compact_context_patch as ccp

app.version = "0.3.44-compact-academy-lore-no-hidden-relationship-v19"

LORE_INDEX_FILE = "canon_lore/index.yaml"
LORE_ALWAYS_FILES = [
    "canon_lore/core/world_background.yaml",
    "canon_lore/academy/academy_background.yaml",
    "canon_lore/hidden/hidden_lore_policy.yaml",
]
LORE_USAGE_LOCK = "gpt/locks/lore_usage_lock.md"
_ORIG = rt.build_scene_context_digest


def _unique(xs):
    result = []
    for x in xs:
        if x and x not in result:
            result.append(x)
    return result


def _read(path, session_id=None):
    try:
        return base.read_text(path, session_id=session_id)
    except Exception:
        return ""


def _cut(text, n=5000):
    text = str(text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + "\n...<truncated>"


def _scene_text(current, story=None):
    parts = []
    for key in ["current_location_id", "current_location_text", "current_scene_goal", "last_player_input", "current_date", "current_time"]:
        if current.get(key):
            parts.append(str(current.get(key)))
    for field in ["active_characters", "nearby_characters", "mentioned_character_ids", "scheduled_character_ids", "delayed_character_ids"]:
        values = current.get(field, [])
        if isinstance(values, list):
            parts += [str(v) for v in values if v]
    if story:
        try:
            parts.append(json.dumps(story, ensure_ascii=False))
        except Exception:
            parts.append(str(story))
    return "\n".join(parts).lower()


def _has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def lore_files_for_context(current: dict[str, Any], scene_character_ids: list[str], story_lines: Any = None) -> list[str]:
    text = _scene_text(current, story_lines)
    files = [LORE_INDEX_FILE] + LORE_ALWAYS_FILES

    if _has_any(text, ["академ", "астрейн", "форма", "дресс", "регистрац", "медосмотр", "медблок", "куратор", "инструктор", "дисциплин", "рейтинг", "допуск", "провер", "физический блок", "старшекурс"]):
        files.append("canon_lore/academy/academy_full.yaml")
    if _has_any(text, ["локац", "мест", "двор", "вход", "корт", "общежит", "комнат", "столов", "медблок", "зал", "площад", "стрельбищ", "бассейн", "маршрут"]):
        files.append("canon_lore/academy/academy_locations.yaml")
    if _has_any(text, ["энерг", "фон", "фонит", "отклик", "поток", "перегруз", "выброс", "датчик", "резонанс", "иней", "тепло", "холод", "вибрац", "смещен", "магнит"]):
        files.append("canon_lore/world/energy_system.yaml")
    if _has_any(text, ["эхо", "аномал", "искаж", "разлом"]):
        files.append("canon_lore/world/echo.yaml")
    if _has_any(text, ["кайрос", "гибрид", "чистый кайрос", "не человек"]):
        files.append("canon_lore/world/kairos.yaml")
    if _has_any(text, ["материк", "континент", "второй мир", "северный сектор", "восточный сектор"]):
        files.append("canon_lore/world/continents_and_worlds.yaml")

    # Do not automatically load long hidden-lore files from character combinations.
    # Hidden behavior boundaries are covered by hidden_lore_policy + character cards + state/knowledge.
    return [path for path in _unique(files) if base.repo_file_exists(path)]


def build_lore_slice(session_id, current, scene_character_ids, story_lines=None):
    files = lore_files_for_context(current, scene_character_ids, story_lines)
    payload = []
    for path in files:
        limit = 6500 if path.endswith(("academy_full.yaml", "academy_locations.yaml")) else 4200
        payload.append({"path": path, "content": _cut(_read(path, session_id), limit)})
    return {
        "lore_mode": "canon_lore_v7_compact_academy_no_auto_hidden",
        "hidden_policy": "Only hidden_lore_policy is always loaded. No relationship hidden file is auto-loaded.",
        "loaded_lore_files": files,
        "files": payload,
    }


def build_scene_context_digest_with_lore(session_id):
    base_digest = _ORIG(session_id)
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    chars = rt.scene_character_ids(current, future)
    story = base.read_json("state/story_lines.json", session_id, default={}) or {}
    return (
        base_digest
        + "\n"
        + rt._json_block("Lore slice", build_lore_slice(session_id, current, chars, story), 18000)
        + "\n## Lore reminder\nUse compact academy/world lore as background. Do not load or reveal hidden relationship lore automatically. Academy technology is modern-realistic, not super-scanner sci-fi.\n"
    )


rt.build_lore_slice = build_lore_slice
rt.lore_files_for_context = lore_files_for_context
rt.build_scene_context_digest = build_scene_context_digest_with_lore
if LORE_USAGE_LOCK not in rt.MINIMAL_LOCK_FILES:
    rt.MINIMAL_LOCK_FILES.append(LORE_USAGE_LOCK)
ccp._read_required_file_for_bundle = rt.read_required_file_for_bundle
rt.app.version = app.version
