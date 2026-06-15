"""
Lore context runtime patch v16.

Academy lore is consolidated into three active files:
- academy_background.yaml: always loaded
- academy_locations.yaml: locations
- academy_full.yaml: uniform/staff/training/discipline/full academy rules
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import app.context_transport_runtime_patch as rt
from app.context_transport_runtime_patch import app
from app import compact as base
import app.compact_context_patch as ccp

app.version = "0.3.37-academy-three-file-lore-v16"
LORE_INDEX_FILE = "canon_lore/index.yaml"
LORE_ALWAYS_FILES = ["canon_lore/core/world_background.yaml", "canon_lore/academy/academy_background.yaml", "canon_lore/hidden/hidden_lore_policy.yaml"]
LORE_TAG_RULES = {
    "echo": {"keywords": ["эхо", "echo", "аномалия", "аномалии", "искажение", "разлом", "физическое эхо"], "files": ["canon_lore/world/echo.yaml"]},
    "kairos": {"keywords": ["кайрос", "кайросы", "kairos", "чистый кайрос", "гибрид", "не человек"], "files": ["canon_lore/world/kairos.yaml"]},
    "continents_worlds": {"keywords": ["континент", "материк", "второй мир", "два материка", "другой мир", "барьер"], "files": ["canon_lore/world/continents_and_worlds.yaml"]},
    "energy": {"keywords": ["энергия", "энергетический", "тип", "пространство", "стихия", "отклик", "импульс", "рейдер"], "files": ["canon_lore/world/energy_system.yaml"]},
    "academy_locations": {"keywords": ["локация", "место", "главный двор", "задний выход", "корт", "баскетбол", "регистрация", "общежитие", "комната", "столовая", "медблок", "стрельбище", "бассейн", "полигон", "аудитория", "тренировочный блок"], "files": ["canon_lore/academy/academy_locations.yaml"]},
    "academy_full": {"keywords": ["академия", "астрейн", "форма", "дресс-код", "эмблема", "пиджак", "жакет", "персонал", "сотрудник", "куратор", "инструктор", "дисциплина", "допуск", "рейтинг", "проверка", "перегруз", "выброс", "датчик", "поток", "прерывание", "спарринг", "захват", "удержание", "стрельбище", "бассейн", "рейдер", "рейдерская подготовка", "северный сектор", "самуэль", "31 августа"], "files": ["canon_lore/academy/academy_full.yaml"]},
}
HIDDEN_AKIRA_RAIDEN_FILE = "canon_lore/hidden/raiden_akira_bond.yaml"
LORE_USAGE_LOCK = "gpt/locks/lore_usage_lock.md"
_ORIGINAL_BUILD_SCENE_CONTEXT_DIGEST = rt.build_scene_context_digest

def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in result:
            result.append(item)
    return result

def _read_text_optional(path: str, session_id: str | None = None) -> str:
    safe_path = str(path or "").strip()
    if not safe_path:
        return ""
    try:
        return base.read_text(safe_path, session_id=session_id)
    except Exception:
        pass
    for root in [getattr(base, "DATA", None), getattr(base, "ROOT", None)]:
        if not root:
            continue
        try:
            file_path = Path(root) / base.safe(safe_path)
            if file_path.exists() and file_path.is_file():
                return file_path.read_text(encoding="utf-8")
        except Exception:
            continue
    return ""

def _cut(text: str, limit: int = 6500) -> str:
    value = str(text or "").strip()
    return value if len(value) <= limit else value[:limit].rstrip() + "\n...<truncated>"

def _collect_scene_text(current: dict[str, Any], story_lines: Any = None) -> str:
    pieces: list[str] = []
    for key in ["current_date", "current_time", "current_location_id", "current_location_text", "current_scene_goal", "last_player_input"]:
        value = current.get(key)
        if value:
            pieces.append(str(value))
    for field in ["active_characters", "nearby_characters", "speaking_character_ids", "observing_character_ids", "addressed_character_ids", "looked_at_character_ids", "mentioned_character_ids", "scheduled_character_ids", "delayed_character_ids"]:
        values = current.get(field, [])
        if isinstance(values, list):
            pieces.extend(str(v) for v in values if v)
    if story_lines:
        try:
            pieces.append(json.dumps(story_lines, ensure_ascii=False))
        except Exception:
            pieces.append(str(story_lines))
    return "\n".join(pieces).lower()

def lore_files_for_context(current: dict[str, Any], scene_character_ids: list[str], story_lines: Any = None) -> list[str]:
    text = _collect_scene_text(current, story_lines)
    files: list[str] = [LORE_INDEX_FILE] + LORE_ALWAYS_FILES
    for rule in LORE_TAG_RULES.values():
        if any(keyword.lower() in text for keyword in rule["keywords"]):
            files.extend(rule["files"])
    normalized_ids = {rt.canonical_id(cid) for cid in scene_character_ids}
    if {"akira", "raiden"} <= normalized_ids:
        files.append(HIDDEN_AKIRA_RAIDEN_FILE)
    return [path for path in _unique(files) if base.repo_file_exists(path)]

def build_lore_slice(session_id: str, current: dict[str, Any], scene_character_ids: list[str], story_lines: Any = None) -> dict[str, Any]:
    files = lore_files_for_context(current, scene_character_ids, story_lines)
    loaded = []
    for path in files:
        limit = 9000 if path == "canon_lore/academy/academy_full.yaml" else 7000
        loaded.append({"path": path, "content": _cut(_read_text_optional(path, session_id=session_id), limit)})
    return {"lore_mode": "canon_lore_v2_academy_three_files", "source_root": "canon_lore/", "academy_policy": "Academy active files: academy_background.yaml, academy_locations.yaml, academy_full.yaml. Old academy microfiles are redirect-stubs.", "loaded_lore_files": files, "load_rules": ["Base world + academy background + hidden policy are always loaded.", "Academy locations load by place/location keywords.", "Academy full loads by uniform/staff/discipline/training/overload/sensor/northern-sector keywords.", "If akira and raiden are both in scene_character_ids, load hidden raiden_akira_bond.", "Hidden lore is for author logic/subtext, not automatic NPC knowledge."], "files": loaded}

def build_scene_context_digest_with_lore(session_id: str) -> str:
    base_digest = _ORIGINAL_BUILD_SCENE_CONTEXT_DIGEST(session_id)
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    chars = rt.scene_character_ids(current, future)
    story_lines = base.read_json("state/story_lines.json", session_id, default={}) or {}
    lore_slice = build_lore_slice(session_id, current, chars, story_lines)
    return base_digest + "\n" + rt._json_block("Lore slice", lore_slice, 22000) + "\n## Lore reminder\nUse canon_lore as background and conditional lore source. Academy lore is practical raider preparation, freedom for strong students, expert supervision, sensors, consequences and Northern Sector hidden sponsorship. Do not expose hidden lore as NPC knowledge unless state/knowledge allows it.\n"

rt.build_lore_slice = build_lore_slice
rt.lore_files_for_context = lore_files_for_context
rt.build_scene_context_digest = build_scene_context_digest_with_lore
if LORE_USAGE_LOCK not in rt.MINIMAL_LOCK_FILES:
    rt.MINIMAL_LOCK_FILES.append(LORE_USAGE_LOCK)
ccp._read_required_file_for_bundle = rt.read_required_file_for_bundle
rt.app.version = app.version
