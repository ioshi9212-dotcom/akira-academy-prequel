"""
Scene packet runtime patch v4 — pre-rendered header contract.

Main gameplay endpoint:
POST /api/v1/sessions/{session_id}/build-scene-packet

This version deliberately does NOT depend on helper functions added by earlier
optimization patches. If Railway has only this file + header hotfix, the endpoint
still builds a packet instead of returning 500.
"""
from __future__ import annotations

from typing import Any
import itertools
import re

from pydantic import BaseModel, Field

try:
    from app.context_transport_runtime_patch import app
except Exception:  # pragma: no cover
    from app.runtime_speed_patch import app  # type: ignore

from app import compact as base

try:
    import app.context_transport_runtime_patch as rt
except Exception:  # pragma: no cover
    rt = None  # type: ignore

try:
    import app.response_size_guard_runtime_patch as sg
except Exception:  # pragma: no cover
    sg = None  # type: ignore

SCENE_PACKET_PATH = "/api/v1/sessions/{session_id}/build-scene-packet"


class BuildScenePacketRequest(BaseModel):
    player_input: str | None = None
    mode: str = "game_turn"
    include_sources: bool = False
    include_diagnostics: bool = True
    include_source_index: bool = True
    max_file_chars: int = Field(default=12000, ge=4000, le=40000)
    max_total_chars: int = Field(default=70000, ge=20000, le=140000)


class ScenePacketResponse(BaseModel):
    session_id: str
    mode: str = "scene_packet"
    usage_note: str = "Use scene_packet as the main gameplay context. Do not manually load the whole project."
    scene_packet: dict[str, Any] = Field(default_factory=dict)
    loaded_files: list[dict[str, Any]] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


CHARACTER_FOLDERS: dict[str, str] = {
    "akira": "akira",
    "livia": "livia",
    "haru": "haru",
    "raiden": "raiden",
    "kir": "kir",
    "kiara": "kiara",
    "kael_north": "kael_north",
}

ALIASES: dict[str, str] = {
    "кира": "akira",
    "акира": "akira",
    "livia_cross": "livia",
    "ливия": "livia",
    "лив": "livia",
    "haru_foster": "haru",
    "хару": "haru",
    "рыжий": "haru",
    "рыжего": "haru",
    "raiden_sterling": "raiden",
    "рейдон": "raiden",
    "райден": "raiden",
    "стерлинг": "raiden",
    "стэрлинг": "raiden",
    "кир": "kir",
    "киара": "kiara",
    "каэл": "kael_north",
    "каел": "kael_north",
    "ray": "ray_carter",
    "ray_carter": "ray_carter",
    "рэй": "ray_carter",
    "рей": "ray_carter",
    "jun": "jun_carter",
    "jun_carter": "jun_carter",
    "джун": "jun_carter",
    "samuel": "samuel_sterling",
    "samuel_sterling": "samuel_sterling",
    "самуэль": "samuel_sterling",
    "asher": "asher_lane",
    "asher_lane": "asher_lane",
    "ашер": "asher_lane",
    "kai": "kai_renwick",
    "kai_renwick": "kai_renwick",
    "кай": "kai_renwick",
}

MENTION_HINTS: dict[str, list[str]] = {
    "akira": ["акира", "кира"],
    "livia": ["ливия", "лив"],
    "haru": ["хару", "рыж", "мяч", "баскет"],
    "raiden": ["райден", "рейдон", "тёмн", "темн", "стерлинг", "стэрлинг"],
    "kir": ["кир"],
    "kiara": ["киара"],
    "kael_north": ["каэл", "каел"],
    "ray_carter": ["рэй", "рей картер", "картер"],
    "jun_carter": ["джун"],
    "asher_lane": ["ашер"],
    "kai_renwick": ["кай", "слепая зона", "ставка"],
}

DISPLAY_NAMES: dict[str, str] = {
    "akira": "Акира",
    "livia": "Ливия",
    "haru": "Хару",
    "raiden": "Райден",
    "kir": "Кир",
    "kiara": "Киара",
    "kael_north": "Каэл",
    "ray_carter": "Рэй",
    "jun_carter": "Джун",
    "samuel_sterling": "Самуэль",
    "asher_lane": "Ашер",
    "kai_renwick": "Кай",
}

MOVEMENT_HINTS = [
    "идти", "пойти", "уйти", "выйти", "зайти", "подойти", "пройти", "дойти",
    "подняться", "спуститься", "к выходу", "к двери", "в комнат", "в душ", "по коридор",
    "на лестниц", "к стойке", "на корт", "в спорт", "в столов", "в общежит",
]
PAST_HINTS = ["прошл", "вспом", "сон", "травм", "детств", "мать", "отец", "пожар", "кай", "ашер", "самуэль", "джун", "эйрен"]
ENERGY_HINTS = ["энерг", "холод", "жар", "огонь", "простран", "давлен", "свет", "импульс", "вибрац", "иней", "перегруз", "датчик"]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower().replace("ё", "е")


def _unique(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        item = _text(value)
        if item and item not in out:
            out.append(item)
    return out


def _canon(value: Any) -> str:
    raw = _lower(value)
    if not raw:
        return ""
    if rt is not None:
        try:
            cid = rt.canonical_id(value)  # type: ignore[attr-defined]
            if cid:
                return str(cid)
        except Exception:
            pass
    return ALIASES.get(raw, raw)


def _folder(cid: str) -> str | None:
    cid = _canon(cid)
    if rt is not None:
        try:
            folder = rt.known_character_folder(cid)  # type: ignore[attr-defined]
            if folder:
                return str(folder)
        except Exception:
            pass
    return CHARACTER_FOLDERS.get(cid)


def _display_name(cid: Any) -> str:
    canon = _canon(cid)
    return DISPLAY_NAMES.get(canon, _text(cid) or canon or "POV")


def _repo_exists(path: str) -> bool:
    if path == "runtime/scene_context_digest.md":
        return True
    if sg is not None and hasattr(sg, "_repo_exists"):
        try:
            return bool(sg._repo_exists(path))  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        return bool(base.repo_file_exists(path))
    except Exception:
        return False


def _safe_json(path: str, session_id: str, default: Any) -> Any:
    try:
        value = base.read_json(path, session_id, default=default)
        return value if value is not None else default
    except Exception:
        return default


def _compact(value: Any, limit: int = 1200) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= limit else text[:limit].rstrip() + "...<truncated>"
    if isinstance(value, list):
        return [_compact(v, limit) for v in value[:16]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for idx, (key, val) in enumerate(value.items()):
            if idx >= 28:
                out["..."] = "truncated"
                break
            out[str(key)] = _compact(val, limit)
        return out
    return str(value)[:limit]


def _read_source(path: str, session_id: str) -> tuple[str | None, str | None]:
    if sg is not None and hasattr(sg, "_read_required_file_for_bundle_size_guard"):
        try:
            content, source = sg._read_required_file_for_bundle_size_guard(path, session_id)  # type: ignore[attr-defined]
            if content is not None:
                return str(content), source or "project"
        except Exception:
            pass
    if rt is not None and hasattr(rt, "read_required_file_for_bundle"):
        try:
            content, source = rt.read_required_file_for_bundle(path, session_id)  # type: ignore[attr-defined]
            if content is not None:
                return str(content), source or "project"
        except Exception:
            pass
    try:
        return base.read_text(path, session_id=session_id), "session"
    except Exception:
        pass
    try:
        return base.read_text(path, session_id=None), "project"
    except Exception:
        return None, None


def _source_kind(path: str) -> str:
    if path.startswith("characters/"):
        return "character_past_triggered" if path.endswith("/past.yaml") else "character_card"
    if path.startswith("state/character_memory/"):
        return "character_memory"
    if path.startswith("state/relationship_pairs/"):
        return "relationship_pair"
    if path.startswith("calendar/days/"):
        return "current_calendar_day"
    if path.startswith("canon_lore/academy/"):
        return "academy_lore"
    if path.startswith("canon_lore/world/") or path.startswith("canon_lore/core/"):
        return "world_lore_triggered"
    if path.startswith("gpt/") or path.startswith("engine/") or path.startswith("runtime/"):
        return "rules"
    if path.startswith("state/"):
        return "state_slice"
    return "project"


def _base_scene_chars(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    if base is not None:
        try:
            values.extend(base.active_scene_characters(current, future) or [])
        except Exception:
            pass
    for field in ("active_characters", "nearby_characters", "speaking_character_ids", "observing_character_ids", "addressed_character_ids", "looked_at_character_ids"):
        values.extend(current.get(field, []) or [])
    for thread in current.get("open_threads", []) or []:
        if isinstance(thread, dict) and thread.get("status") in {"due", "active", "triggered"}:
            values.extend(thread.get("participants", []) or [])
    if not values:
        values = ["akira"]
    out: list[str] = []
    for raw in values:
        cid = _canon(raw)
        if cid and cid not in {"students", "staff", "crowd", "academy_staff", "new_students_block_b"}:
            if _folder(cid) or cid in {"akira", "ray_carter", "jun_carter", "samuel_sterling", "asher_lane", "kai_renwick"}:
                out.append(cid)
    return _unique(out)


def _active_chars(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    if sg is not None and hasattr(sg, "_scene_chars"):
        try:
            chars = sg._scene_chars(current, future)  # type: ignore[attr-defined]
            if chars:
                return _unique([_canon(c) for c in chars])
        except Exception:
            pass
    return _base_scene_chars(current, future)


def _reference_ids(current: dict[str, Any], active: list[str]) -> list[str]:
    values: list[Any] = []
    for field in ("scheduled_character_ids", "delayed_character_ids", "mentioned_character_ids"):
        values.extend(current.get(field, []) or [])
    active_set = set(active)
    return _unique([_canon(v) for v in values if _canon(v) and _canon(v) not in active_set])


def _pov_info(current: dict[str, Any], active: list[str]) -> dict[str, Any]:
    target = current.get("pov") or (active[0] if active else "akira")
    if rt is not None and hasattr(rt, "pov_mode_info"):
        try:
            info = rt.pov_mode_info(current)  # type: ignore[attr-defined]
            if isinstance(info, dict):
                target = info.get("target_character_id") or target
        except Exception:
            pass
    target = _canon(target) or "akira"
    return {
        "pov_character_id": target,
        "pov_display": _display_name(target),
        "rule": "Player controls current POV. Low-stakes automatic POV lines are allowed; meaningful choices stop for player input.",
    }


def _parenthetical_actions(player_input: str) -> list[str]:
    return [_text(x) for x in re.findall(r"\(([^)]{1,500})\)", player_input or "") if _text(x)]


def _speech(player_input: str) -> str:
    return " ".join(re.sub(r"\([^)]*\)", " ", player_input or "").split()).strip()


def _has_hint(text: str, hints: list[str]) -> bool:
    low = _lower(text)
    return any(h in low for h in hints)


def _mentions(text: str) -> list[str]:
    low = _lower(text)
    out: list[str] = []
    for cid, hints in MENTION_HINTS.items():
        if any(h in low for h in hints):
            out.append(cid)
    return _unique(out)


def _relationship_pair_files(chars: list[str]) -> list[str]:
    files: list[str] = []
    for a, b in itertools.combinations(_unique([_canon(c) for c in chars]), 2):
        for rel in (f"state/relationship_pairs/{a}__{b}.json", f"state/relationship_pairs/{b}__{a}.json"):
            if _repo_exists(rel):
                files.append(rel)
                break
    return _unique(files)


def _character_files(chars: list[str]) -> list[str]:
    files: list[str] = []
    for cid in chars:
        folder = _folder(cid)
        if folder:
            for rel in (f"characters/{folder}/character.yaml", f"characters/{folder}/main.yaml"):
                if _repo_exists(rel):
                    files.append(rel)
        mem = f"state/character_memory/{cid}.json"
        if _repo_exists(mem):
            files.append(mem)
    return _unique(files)


def _current_day_file(current: dict[str, Any]) -> list[str]:
    date = _text(current.get("current_date"))
    if not date:
        return []
    rel = f"calendar/days/{date}.yaml"
    return [rel] if _repo_exists(rel) else []


def _base_rule_files() -> list[str]:
    candidates = [
        "runtime/scene_context_digest.md",
        "gpt/locks/runtime_scene_rules_digest.md",
        "gpt/scene_output_contract_1198.json",
        "state/context_loading/scene_context_builder_rules_1198.json",
        "state/context_loading/character_selection_rules_1198.json",
        "state/context_loading/forbidden_fallback_rules_1198.json",
    ]
    return [p for p in candidates if _repo_exists(p)]


def _academy_lore_files() -> list[str]:
    return [p for p in ["canon_lore/academy/academy_background.yaml", "canon_lore/academy/academy_locations.yaml"] if _repo_exists(p)]


def _update_contract_files() -> list[str]:
    return [p for p in [
        "state/update_contracts/turn_update_pipeline_1198.json",
        "state/update_contracts/character_memory_patch_rules_1198.json",
        "state/update_contracts/relationship_pair_patch_rules_1198.json",
        "state/update_contracts/scene_state_patch_rules_1198.json",
        "gpt/locks/state_update_payload_contract.md",
    ] if _repo_exists(p)]


def _trigger_files(player_input: str, active: list[str]) -> list[str]:
    files: list[str] = []
    if _has_hint(player_input, ENERGY_HINTS):
        files.extend([p for p in ["canon_lore/world/energy_system.yaml", "canon_lore/world/kairos.yaml"] if _repo_exists(p)])
    if _has_hint(player_input, PAST_HINTS):
        for cid in active:
            folder = _folder(cid)
            rel = f"characters/{folder}/past.yaml" if folder else ""
            if rel and _repo_exists(rel):
                files.append(rel)
        if any(x in _lower(player_input) for x in ["кай", "ашер", "слеп"]):
            rel = "state/knowledge_threads/kai_asher_school_thread.json"
            if _repo_exists(rel):
                files.append(rel)
    return _unique(files)


def _packet_files(player_input: str, current: dict[str, Any], future: dict[str, Any], active: list[str]) -> list[str]:
    files: list[str] = []
    files.extend(_base_rule_files())
    files.extend(_current_day_file(current))
    files.extend(_character_files(active))
    files.extend(_relationship_pair_files(active))
    for rel in ["state/akira_progress_state.json", "state/open_threads.json", "state/inventory_state.json", "state/scene_history.json", "state/story_lines.json"]:
        if _repo_exists(rel):
            files.append(rel)
    files.extend(_academy_lore_files())
    files.extend(_trigger_files(player_input, active))
    files.extend(_update_contract_files())
    forbidden = {"state/knowledge_state.json", "state/relationships.json"}
    return [f for f in _unique(files) if f not in forbidden and not f.startswith("state/legacy/")]


def _load_sources(paths: list[str], session_id: str, max_file_chars: int, max_total_chars: int) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    missing: list[str] = []
    total = 0
    truncated: list[str] = []
    skipped: list[str] = []
    for path in paths:
        if total >= max_total_chars:
            skipped.append(path)
            continue
        content, source = _read_source(path, session_id)
        if content is None:
            missing.append(path)
            continue
        text = str(content)
        original = len(text)
        file_limit = max(1000, min(max_file_chars, max_total_chars - total))
        cut = original > file_limit
        if cut:
            text = text[:file_limit].rstrip() + "\n...<truncated by scene_packet>"
            truncated.append(path)
        total += len(text)
        loaded.append({
            "path": path,
            "kind": _source_kind(path),
            "source": source or "project",
            "chars_original": original,
            "chars_sent": len(text),
            "truncated": cut,
            "content": text,
        })
    return loaded, missing, {"total_chars_sent": total, "truncated_files": truncated, "skipped_after_budget": skipped}


def _memory_table(session_id: str, chars: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for cid in chars:
        rel = f"state/character_memory/{cid}.json"
        if _repo_exists(rel):
            out[cid] = _compact(_safe_json(rel, session_id, {}), 1400)
    return {"source": "state/character_memory/<id>.json", "mode": "per_character_runtime_memory_only", "characters": out}


def _relationship_table(session_id: str, chars: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rel in _relationship_pair_files(chars):
        pair_id = rel.rsplit("/", 1)[-1].removesuffix(".json")
        out[pair_id] = _compact(_safe_json(rel, session_id, {}), 1200)
    return {"source": "state/relationship_pairs/<a>__<b>.json", "mode": "scene_relevant_pairs_only", "pairs": out}


def _context_needs(player_input: str, active: list[str]) -> dict[str, Any]:
    movement = _has_hint(player_input, MOVEMENT_HINTS)
    past = _has_hint(player_input, PAST_HINTS)
    energy = _has_hint(player_input, ENERGY_HINTS)
    mentions = _mentions(player_input)
    return {
        "player_speech": _speech(player_input),
        "player_actions": _parenthetical_actions(player_input),
        "mentioned_character_ids_from_input": mentions,
        "directly_relevant_character_ids": _unique(active + [m for m in mentions if m in set(active)]),
        "needs": _unique([
            "current_frame", "scene_output_template", "pov_rules", "active_character_cards",
            "active_character_memory", "scene_relevant_relationship_pairs", "current_calendar_day",
            "academy_location_lore", "stop_chain_rules", "apply_turn_result_contract",
        ] + (["movement_chain_interruption_check"] if movement else []) + (["past_trigger_check"] if past else []) + (["energy_body_control_rules"] if energy else [])),
        "trigger_flags": {"movement_chain": movement, "past_trigger": past, "energy_trigger": energy, "npc_interruption_must_stop_choice": movement},
        "chain_rule": "Parenthetical movement/action is intention, not guaranteed completion. If an NPC creates a meaningful interruption, stop before completing the chain.",
    }



_MONTHS_RU = {
    "01": "января", "02": "февраля", "03": "марта", "04": "апреля", "05": "мая", "06": "июня",
    "07": "июля", "08": "августа", "09": "сентября", "10": "октября", "11": "ноября", "12": "декабря",
}
_TIME_RU = {
    "early_morning": "раннее утро",
    "morning": "утро",
    "late_morning": "позднее утро",
    "midday": "полдень",
    "afternoon": "день",
    "evening": "вечер",
    "night": "ночь",
    "late_night": "поздняя ночь",
}


def _date_ru(value: Any) -> str:
    raw = _text(value)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if not m:
        return raw
    year, month, day = m.groups()
    return f"{int(day)} {_MONTHS_RU.get(month, month)}"


def _time_ru(value: Any) -> str:
    raw = _text(value)
    return _TIME_RU.get(raw, raw.replace("_", " "))


def _visible_state(current: dict[str, Any]) -> str:
    akira_state = current.get("akira_state") if isinstance(current.get("akira_state"), dict) else {}
    return _text(akira_state.get("visible_state") or current.get("visible_state") or "видимо спокойна")


def _weather_text(current: dict[str, Any]) -> str:
    weather = current.get("weather") if isinstance(current.get("weather"), dict) else {}
    summary = _text(weather.get("summary"))
    if not summary or summary == "set in first scene":
        return "погода не акцентирована"
    return summary


_VISIBLE_STATE_RU = {
    "calm outside": "внешне спокойна",
    "controlled": "собрана",
    "tense": "напряжена",
    "tired": "устала",
}
_SCENE_GOAL_RU = {
    "Fixed start: Ray drops Akira and Livia at Academy; short bag dialogue before first player choice and route toward back court entrance.":
        "первый вход в Академию; Рэй высаживает Акиру и Ливию, дальше — регистрация и выбор маршрута",
}


def _ru_value(value: Any, table: dict[str, str]) -> str:
    raw = _text(value)
    return table.get(raw, raw)


def _visible_state_ru(value: Any) -> str:
    raw = _text(value)
    return _VISIBLE_STATE_RU.get(raw, raw or "внешне спокойна")


def _scene_goal_ru(value: Any) -> str:
    raw = _text(value)
    return _SCENE_GOAL_RU.get(raw, raw or "первый вход в Академию; пауза перед выбором маршрута")


def _dedupe_visible_items(items: list[str]) -> list[str]:
    out: list[str] = []
    for raw in items:
        item = _text(raw)
        if not item:
            continue
        low = item.lower()
        # Do not repeat a shorter nearby item if the longer visible inventory already says the same thing.
        if any(low in prev.lower() or prev.lower() in low for prev in out):
            continue
        out.append(item)
    return out


def _header_values(current: dict[str, Any], active: list[str]) -> dict[str, Any]:
    pov = _pov_info(current, active)
    inv = current.get("visible_inventory") or []
    nearby = current.get("nearby_items") or []
    inv_line = []
    if isinstance(inv, list):
        inv_line.extend([_text(x) for x in inv if _text(x)])
    elif _text(inv):
        inv_line.append(_text(inv))
    if isinstance(nearby, list):
        inv_line.extend([_text(x) for x in nearby if _text(x)])
    elif _text(nearby):
        inv_line.append(_text(nearby))
    return {
        "current_date": _date_ru(current.get("current_date")),
        "current_time_or_phase": _time_ru(current.get("current_time")),
        "current_location_text": current.get("current_location_text"),
        "weather_if_relevant": _weather_text(current),
        "current_scene_goal_or_tension": _scene_goal_ru(current.get("current_scene_goal")),
        "pov_display_name": pov.get("pov_display") or pov.get("pov_character_id"),
        "visible_state": _visible_state_ru(_visible_state(current)),
        "current_outfit_if_relevant": current.get("current_outfit"),
        "visible_inventory_or_nearby_items_if_relevant": "; ".join(_dedupe_visible_items(inv_line)[:4]),
    }

def _render_header(values: dict[str, Any]) -> str:
    lines = [
        f"🏛️ Академия Астрейн · 1198 г., {values.get('current_date') or '15 августа'}",
        f"🕒 {values.get('current_time_or_phase') or 'позднее утро'} · 📍 {values.get('current_location_text') or 'Академия Астрейн'}",
        f"🌦️ {values.get('weather_if_relevant') or 'погода не акцентирована'} · ⚙️ {values.get('current_scene_goal_or_tension') or 'первый вход в Академию'}",
        f"✦ POV: {values.get('pov_display_name') or 'Акира'} · {values.get('visible_state') or 'внешне спокойна'}",
    ]
    outfit = _text(values.get('current_outfit_if_relevant'))
    inventory = _text(values.get('visible_inventory_or_nearby_items_if_relevant'))
    if outfit:
        lines.append(f"🧥 {outfit}")
    if inventory:
        lines.append(f"◈ {inventory}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


_GENITIVE_RU = {
    "Акира": "Акиры",
    "Ливия": "Ливии",
    "Киара": "Киары",
    "Райден": "Райдена",
    "Хару": "Хару",
    "Кир": "Кира",
    "Рэй": "Рэя",
    "Каэл": "Каэла",
}
_FEMALE_NAMES = {"Акира", "Ливия", "Киара"}


def _bottom_labels(pov_display: str) -> dict[str, str]:
    pov = pov_display or "Акира"
    gen = _GENITIVE_RU.get(pov, pov)
    say_aux = "могла бы" if pov in _FEMALE_NAMES else "мог бы"
    return {
        "actions": "✦ Что можно сделать",
        "say": f"✦ Что {pov} {say_aux} сказать",
        "thoughts": f"✦ Мысли {gen}",
        "levels": "✦ Уровни",
        "relationships": "✦ Отношения",
    }


def _current_frame(current: dict[str, Any], future: dict[str, Any], active: list[str], player_input: str) -> dict[str, Any]:
    header_values = _header_values(current, active)
    return {
        "date": current.get("current_date"),
        "time": current.get("current_time"),
        "location_id": current.get("current_location_id"),
        "location_text": current.get("current_location_text"),
        "scene_goal": current.get("current_scene_goal"),
        "pov": _pov_info(current, active),
        "full_character_ids": active,
        "reference_character_ids": _reference_ids(current, active),
        "active_character_ids_from_state": _unique(current.get("active_characters", []) or []),
        "nearby_character_ids_from_state": _unique(current.get("nearby_characters", []) or []),
        "scheduled_do_not_full_load": _unique(current.get("scheduled_character_ids", []) or []),
        "delayed_do_not_full_load": _unique(current.get("delayed_character_ids", []) or []),
        "visible_inventory": _compact(current.get("visible_inventory"), 1000),
        "nearby_items": _compact(current.get("nearby_items"), 1000),
        "current_outfit": current.get("current_outfit"),
        "uniform_worn": current.get("uniform_worn"),
        "last_player_input_from_state": current.get("last_player_input"),
        "player_input_for_this_turn": player_input,
        "header_values": header_values,
        "rendered_header": _render_header(header_values),
        "bottom_block_labels": _bottom_labels(str(header_values.get("pov_display_name") or "Акира")),
        "visible_state": _visible_state_ru(_visible_state(current)),
    }



def _read_project_json(path: str, session_id: str, default: Any) -> Any:
    """Read project/session JSON defensively without turning scene packet into 500."""
    value = _safe_json(path, session_id, None)
    if value is not None:
        return value
    content, _ = _read_source(path, session_id)
    if not content:
        return default
    try:
        import json
        return json.loads(content)
    except Exception:
        return default


def _source_index(paths: list[str]) -> list[dict[str, Any]]:
    return [{"path": p, "kind": _source_kind(p), "required_for_packet": True} for p in paths]


def _character_table(session_id: str, chars: list[str]) -> dict[str, Any]:
    """Compact full-character cards for active/full characters only."""
    out: dict[str, Any] = {}
    for cid in chars:
        folder = _folder(cid)
        if not folder:
            continue
        selected_path = ""
        content = ""
        for rel in (f"characters/{folder}/character.yaml", f"characters/{folder}/main.yaml"):
            if _repo_exists(rel):
                selected_path = rel
                raw, _source = _read_source(rel, session_id)
                content = raw or ""
                break
        if selected_path:
            out[cid] = {
                "path": selected_path,
                "mode": "compact_full_character_card_for_scene_packet",
                "content_excerpt": _compact(content, 3600),
            }
    return {"mode": "active_full_characters_only", "characters": out}


def _lore_packet(session_id: str, paths: list[str]) -> dict[str, Any]:
    """Small lore slice; enough for scene, not the whole project."""
    out: dict[str, Any] = {}
    for path in paths:
        if path.startswith("canon_lore/academy/") or path.startswith("canon_lore/world/"):
            raw, _source = _read_source(path, session_id)
            if raw:
                out[path] = _compact(raw, 2200)
    return {"mode": "scene_relevant_lore_only", "items": out}


def _strict_output_contract(session_id: str) -> dict[str, Any]:
    contract = _read_project_json("gpt/scene_output_contract_1198.json", session_id, {})
    if not isinstance(contract, dict) or not contract:
        contract = {}
    header_template = contract.get("header_template") or [
        "🏛️ Академия Астрейн · 1198 г., {current_date}",
        "🕒 {current_time_or_phase} · 📍 {current_location_text}",
        "🌦️ {weather_if_relevant} · ⚙️ {current_scene_goal_or_tension}",
        "✦ POV: {pov_display_name} · {visible_state}",
        "🧥 {current_outfit_if_relevant}",
        "◈ {visible_inventory_or_nearby_items_if_relevant}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    bottom_blocks_order = contract.get("bottom_blocks_order") or [
        "✦ Что можно сделать",
        "✦ Что [POV] мог(ла) бы сказать",
        "✦ Мысли [POV]",
        "✦ Уровни",
        "✦ Отношения",
    ]
    return {
        "source": "gpt/scene_output_contract_1198.json",
        "contract_id": contract.get("id", "scene_output_contract_1198"),
        "version": contract.get("version", "fallback_v3"),
        "visible_scene_must_start_with_header": True,
        "must_use_header_template_exactly": True,
        "header_template": header_template,
        "rendered_header_source": "scene_packet.current_frame.rendered_header",
        "writer_rule": "Copy scene_packet.current_frame.rendered_header exactly as the first block of the visible scene. Do not rebuild the header manually.",
        "header_render_rules": {
            "date": "Используй готовую строку rendered_header; дату не пересобирай вручную.",
            "time": "Используй rendered_header; не оставляй английские late_morning/late morning.",
            "location": "Используй rendered_header; место не сокращай до markdown-строки.",
            "weather_goal": "Используй rendered_header; не пиши placeholder.",
            "pov_state": "Используй rendered_header: ✦ POV: <имя> · <видимое состояние>.",
            "outfit": "Используй строку 🧥 из rendered_header, если она есть.",
            "inventory": "Используй строку ◈ из rendered_header, если она есть.",
            "separator": "Разделитель уже есть в rendered_header; не удаляй его.",
        },
        "dialogue_format_required": contract.get("dialogue_format_required", "**Имя/видимый дескриптор** — реплика."),
        "unknown_name_rule": contract.get("unknown_name_rule", []),
        "prose_rules": contract.get("prose_rules", []),
        "bottom_blocks_order": bottom_blocks_order,
        "bottom_blocks_rules": contract.get("bottom_blocks_rules", []),
        "fallback_forbidden": "Never invent a loose markdown header if this contract is present. If packet_status is not ready, do not write scene.",
    }

def _output_template() -> dict[str, Any]:
    # Kept for backward compatibility; strict contract is now in output_contract.
    return {
        "format": "academy_old_visual_novel_header_v2",
        "strict_contract_location": "scene_packet.output_contract",
        "header": "Copy scene_packet.current_frame.rendered_header exactly; no loose markdown fallback.",
        "dialogue": "**Имя/видимый дескриптор** — реплика.",
        "bottom_blocks": ["✦ Что можно сделать", "✦ Что [POV] мог(ла) бы сказать", "✦ Мысли [POV]", "✦ Уровни", "✦ Отношения"],
        "style": "dense readable paragraphs; no micro-lines of 3-5 words",
    }


def _story_slice(story: Any) -> Any:
    if sg is not None and hasattr(sg, "_story_slice"):
        try:
            return sg._story_slice(story)  # type: ignore[attr-defined]
        except Exception:
            pass
    return _compact(story, 1400)


def _scene_history(session_id: str) -> dict[str, Any]:
    history = _safe_json("state/scene_history.json", session_id, {})
    entries = history.get("entries") if isinstance(history, dict) else []
    entries = entries if isinstance(entries, list) else []
    return {"recent_entries": _compact(entries[-5:], 1800), "last_entry": _compact(entries[-1], 1200) if entries else None}


def _save_contract() -> dict[str, Any]:
    return {
        "after_scene_call": "applyTurnResult",
        "save_only_meaningful_changes": True,
        "targets": {
            "character_memory": "state/character_memory/<id>.json",
            "relationship_pairs": "state/relationship_pairs/<a>__<b>.json",
            "scene_state": "state/current_state.json",
            "scene_history": "state/scene_history.json",
            "open_threads": "state/open_threads.json",
        },
        "do_not_save": ["debug/audit as gameplay", "routine steps without consequence", "old global knowledge_state/relationships"],
    }


@app.post(SCENE_PACKET_PATH, response_model=ScenePacketResponse, operation_id="buildScenePacket")
def build_scene_packet(session_id: str, request: BuildScenePacketRequest | None = None) -> ScenePacketResponse:
    sid = base.safe_session_id(session_id)
    try:
        req = request or BuildScenePacketRequest()
        base.ensure_session(sid)
        player_input = _text(req.player_input)
        current = _safe_json("state/current_state.json", sid, {})
        future = _safe_json("state/future_locks_progress.json", sid, {})
        active = _active_chars(current, future)
        files = _packet_files(player_input, current, future, active)
        loaded, missing, source_diag = _load_sources(files, sid, req.max_file_chars, req.max_total_chars) if req.include_sources else ([], [], {"total_chars_sent": 0})
        inventory = _safe_json("state/inventory_state.json", sid, {})
        story = _safe_json("state/story_lines.json", sid, {})
        packet = {
            "packet_version": "scene_packet_v4_rendered_header",
            "packet_status": "ready",
            "mode": req.mode,
            "session_id": sid,
            "current_frame": _current_frame(current, future, active, player_input),
            "player_input": {
                "raw": player_input,
                "speech": _speech(player_input),
                "actions": _parenthetical_actions(player_input),
                "technical_turn_rule": "Debug/audit messages are not gameplay and must not be saved as scene.",
            },
            "context_needs": _context_needs(player_input, active),
            "selection": {
                "full_character_ids": active,
                "reference_character_ids": _reference_ids(current, active),
                "must_load_now_paths": files,
                "rule": "Railway selected sources for this turn. GPT should not fetch all project files manually.",
            },
            "characters": _character_table(sid, active),
            "knowledge": _memory_table(sid, active),
            "relationships": _relationship_table(sid, active),
            "lore": _lore_packet(sid, files),
            "story_context": _story_slice(story),
            "scene_history": _scene_history(sid),
            "inventory": {
                "visible_inventory": _compact(current.get("visible_inventory"), 1000),
                "nearby_items": _compact(current.get("nearby_items"), 1000),
                "current_outfit": _compact(current.get("current_outfit"), 1000),
                "akira_inventory_state": _compact((inventory.get("akira") or {}) if isinstance(inventory, dict) else {}, 1000),
            },
            "output_contract": _strict_output_contract(sid),
            "output_template": _output_template(),
            "save_contract": _save_contract(),
            "forbidden_context": [
                "Do not use state/knowledge_state.json as runtime knowledge source.",
                "Do not use state/relationships.json as runtime relationship source.",
                "Do not full-load scheduled/delayed characters before entrance/current_frame promotion.",
                "Do not reveal hidden lore as narrator fact, NPC fact, sensor result, or unexplained thought.",
                "Do not complete a movement chain after meaningful NPC interruption; stop at choice.",
            ],
            "source_index": _source_index(files) if req.include_source_index else [],
            "loaded_sources": loaded if req.include_sources else [],
            "render_guard": {
                "packet_owns_scene_format": True,
                "copy_rendered_header_exactly": True,
                "rendered_header_path": "scene_packet.current_frame.rendered_header",
                "do_not_call_manifest_chunks_for_render": True,
                "do_not_write_scene_if_packet_status_not_ready": True,
                "must_start_with": "🏛️ Академия Астрейн",
                "first_visible_block_must_equal_rendered_header": True,
                "forbidden_header_examples": ["1198-08-15 · late morning", "Академия Астрейн, ... / POV: Акира as plain markdown"],
            },
        }
        diagnostics = {
            "build": "scene_packet_v4_rendered_header_default_no_sources",
            "loaded_file_count": len(loaded),
            "missing_file_count": len(missing),
            "selected_path_count": len(files),
            "active_character_count": len(active),
            **source_diag,
        } if req.include_diagnostics else {}
        return ScenePacketResponse(
            session_id=sid,
            scene_packet=packet,
            loaded_files=[{k: v for k, v in item.items() if k != "content"} for item in loaded] if req.include_sources else [],
            missing_files=missing,
            diagnostics=diagnostics,
        )
    except Exception as exc:  # final safety: never hide route behind 500 if possible
        packet = {
            "packet_version": "scene_packet_v4_rendered_header",
            "packet_status": "error_no_scene",
            "session_id": sid,
            "error_rule": "Do not write a gameplay scene from this packet. Fix API or use technical diagnostics.",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
        }
        return ScenePacketResponse(
            session_id=sid,
            usage_note="Scene packet failed internally. Do not write gameplay scene from compact context fallback.",
            scene_packet=packet,
            diagnostics={"packet_status": "error_no_scene", "error_type": type(exc).__name__, "error_message": str(exc)[:1000]},
        )


app.version = "0.3.75-scene-packet-rendered-header-v4"
