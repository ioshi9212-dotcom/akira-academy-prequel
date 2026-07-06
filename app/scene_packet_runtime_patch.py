"""
Scene packet runtime patch v6 — slim packet + ordered input + strict footer UI.

Main gameplay endpoint:
POST /api/v1/sessions/{session_id}/build-scene-packet

v5/v6 fixes:
- buildScenePacket no longer returns duplicated full character/lore/memory content by default;
  required file contents are loaded through required-files-manifest/chunks.
- player input is parsed into ordered segments, so speech/action/speech order is preserved.
- relationship panel is exposed as compact UI data, not prose.
- v6 adds strict footer rules: 3 actions, 3 speech options, 3 thoughts, relationship panel required when items exist.
"""
from __future__ import annotations

from typing import Any
import itertools
import json
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
    include_source_index: bool = False
    max_file_chars: int = Field(default=12000, ge=4000, le=40000)
    max_total_chars: int = Field(default=70000, ge=20000, le=140000)


class ScenePacketResponse(BaseModel):
    session_id: str
    mode: str = "scene_packet"
    usage_note: str = "Use scene_packet for current frame/render rules. Load required file contents through manifest/chunks."
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


# ---------------------------------------------------------------------------
# Small generic helpers
# ---------------------------------------------------------------------------

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


def _compact(value: Any, limit: int = 900) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        text = value.strip()
        return text if len(text) <= limit else text[:limit].rstrip() + "...<truncated>"
    if isinstance(value, list):
        return [_compact(v, limit) for v in value[:12]]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for idx, (key, val) in enumerate(value.items()):
            if idx >= 18:
                out["..."] = "truncated"
                break
            out[str(key)] = _compact(val, limit)
        return out
    return str(value)[:limit]


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


# ---------------------------------------------------------------------------
# Character/file selection
# ---------------------------------------------------------------------------

def _base_scene_chars(current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    values: list[Any] = []
    if base is not None:
        try:
            values.extend(base.active_scene_characters(current, future) or [])
        except Exception:
            pass
    for field in (
        "active_characters", "nearby_characters", "speaking_character_ids",
        "observing_character_ids", "addressed_character_ids", "looked_at_character_ids",
    ):
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


def _relationship_pair_files(chars: list[str]) -> list[str]:
    if sg is not None and hasattr(sg, "_relationship_pair_files"):
        try:
            files = sg._relationship_pair_files(chars)  # type: ignore[attr-defined]
            if files:
                return _unique([str(f) for f in files])
        except Exception:
            pass
    files: list[str] = []
    for a, b in itertools.combinations(_unique([_canon(c) for c in chars]), 2):
        for rel in (f"state/relationship_pairs/{a}__{b}.json", f"state/relationship_pairs/{b}__{a}.json"):
            if _repo_exists(rel):
                files.append(rel)
                break
    return _unique(files)


def _fallback_packet_files(player_input: str, current: dict[str, Any], future: dict[str, Any], active: list[str]) -> list[str]:
    files: list[str] = []
    for rel in [
        "runtime/scene_context_digest.md",
        "gpt/locks/runtime_scene_rules_digest.md",
        "gpt/scene_output_contract_1198.json",
    ]:
        if _repo_exists(rel):
            files.append(rel)
    date = _text(current.get("current_date"))
    if date and _repo_exists(f"calendar/days/{date}.yaml"):
        files.append(f"calendar/days/{date}.yaml")
    for cid in active:
        folder = _folder(cid)
        if folder:
            for rel in (f"characters/{folder}/character.yaml", f"characters/{folder}/main.yaml"):
                if _repo_exists(rel):
                    files.append(rel)
        mem = f"state/character_memory/{cid}.json"
        if _repo_exists(mem):
            files.append(mem)
    files.extend(_relationship_pair_files(active))
    if _repo_exists("state/akira_progress_state.json"):
        files.append("state/akira_progress_state.json")
    return _unique([f for f in files if f not in {"state/knowledge_state.json", "state/relationships.json"} and not f.startswith("state/legacy/")])


def _packet_files(player_input: str, current: dict[str, Any], future: dict[str, Any], active: list[str]) -> list[str]:
    # Use the same selector as getRequiredFilesManifest/getRequiredFilesChunk when available.
    # This prevents buildScenePacket from silently selecting a bigger file set than chunks.
    if sg is not None and hasattr(sg, "_required_files"):
        try:
            files = sg._required_files(current, future)  # type: ignore[attr-defined]
            if files:
                forbidden = {"state/knowledge_state.json", "state/relationships.json"}
                return [str(f) for f in _unique(list(files)) if str(f) not in forbidden and not str(f).startswith("state/legacy/")]
        except Exception:
            pass
    return _fallback_packet_files(player_input, current, future, active)


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
            # Full content is intentionally not placed into scene_packet in v5.
            "content": text,
        })
    return loaded, missing, {"total_chars_sent": total, "truncated_files": truncated, "skipped_after_budget": skipped}


# ---------------------------------------------------------------------------
# Ordered player input parser
# ---------------------------------------------------------------------------

def _pause_level(parenthetical: str) -> str:
    text = _text(parenthetical)
    if not text:
        return "none"
    comma_count = text.count(",") + text.count(";") + text.count(".")
    long_markers = ["подум", "вспом", "изуч", "осмотр", "задерж", "сначала", "затем", "потом", "медленно"]
    if len(text) >= 120 or comma_count >= 3 or any(marker in _lower(text) for marker in long_markers):
        return "long"
    if len(text) >= 55 or comma_count >= 1:
        return "medium"
    return "short"


def _player_input_segments(player_input: str) -> list[dict[str, Any]]:
    """Preserve the exact speech/action order from player input.

    Example:
    "Вы за кого переживаете? (поправить сумку) За меня или академию?"
    -> speech, parenthetical, speech. The writer must not merge speech across
    the parenthetical pause.
    """
    raw = player_input or ""
    segments: list[dict[str, Any]] = []
    pos = 0
    order = 1
    for match in re.finditer(r"\(([^)]{0,800})\)", raw):
        before = raw[pos:match.start()].strip()
        if before:
            segments.append({
                "order": order,
                "type": "speech",
                "text": " ".join(before.split()),
                "render_rule": "Render as exact POV speech before the following parenthetical beat. Do not merge with later speech.",
            })
            order += 1
        action = _text(match.group(1))
        if action:
            pause = _pause_level(action)
            segments.append({
                "order": order,
                "type": "parenthetical",
                "text": action,
                "pause": pause,
                "allows_npc_reaction": pause in {"medium", "long"},
                "render_rule": "Render as POV action/thought/body beat/pause, not as dialogue. Keep it between surrounding speech segments.",
            })
            order += 1
        pos = match.end()
    tail = raw[pos:].strip()
    if tail:
        segments.append({
            "order": order,
            "type": "speech",
            "text": " ".join(tail.split()),
            "render_rule": "Render as exact POV speech after prior parenthetical beat. Do not move it before the beat.",
        })
    return segments


def _parenthetical_actions(player_input: str) -> list[str]:
    return [seg["text"] for seg in _player_input_segments(player_input) if seg.get("type") == "parenthetical" and _text(seg.get("text"))]


def _speech(player_input: str) -> str:
    return " ".join(seg["text"] for seg in _player_input_segments(player_input) if seg.get("type") == "speech" and _text(seg.get("text"))).strip()


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


def _context_needs(player_input: str, active: list[str]) -> dict[str, Any]:
    movement = _has_hint(player_input, MOVEMENT_HINTS)
    past = _has_hint(player_input, PAST_HINTS)
    energy = _has_hint(player_input, ENERGY_HINTS)
    mentions = _mentions(player_input)
    return {
        "player_speech": _speech(player_input),
        "player_actions": _parenthetical_actions(player_input),
        "player_input_segments": _player_input_segments(player_input),
        "player_input_segment_rule": "Render player_input.segments in exact order. Speech outside parentheses is exact POV speech; parentheticals are action/thought/pause beats. Never merge speech across a parenthetical.",
        "mentioned_character_ids_from_input": mentions,
        "directly_relevant_character_ids": _unique(active + [m for m in mentions if m in set(active)]),
        "needs": _unique([
            "current_frame", "scene_output_template", "pov_rules", "active_character_cards",
            "active_character_memory", "scene_relevant_relationship_pairs", "current_calendar_day",
            "ordered_player_input_segments", "relationship_ui_panel", "stop_chain_rules",
            "apply_turn_result_contract",
        ] + (["movement_chain_interruption_check"] if movement else []) + (["past_trigger_check"] if past else []) + (["energy_body_control_rules"] if energy else [])),
        "trigger_flags": {"movement_chain": movement, "past_trigger": past, "energy_trigger": energy, "npc_interruption_must_stop_choice": movement},
        "chain_rule": "Parenthetical movement/action is intention, not guaranteed completion. If an NPC creates a meaningful interruption, stop before completing the chain.",
    }


# ---------------------------------------------------------------------------
# Header/current frame
# ---------------------------------------------------------------------------

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


def _date_ru(value: Any) -> str:
    raw = _text(value)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", raw)
    if not m:
        return raw
    _year, month, day = m.groups()
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
        if any(low in prev.lower() or prev.lower() in low for prev in out):
            continue
        out.append(item)
    return out


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


def _header_values(current: dict[str, Any], active: list[str]) -> dict[str, Any]:
    pov = _pov_info(current, active)
    inv = current.get("visible_inventory") or []
    nearby = current.get("nearby_items") or []
    inv_line: list[str] = []
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
    outfit = _text(values.get("current_outfit_if_relevant"))
    inventory = _text(values.get("visible_inventory_or_nearby_items_if_relevant"))
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
        "visible_inventory": _compact(current.get("visible_inventory"), 700),
        "nearby_items": _compact(current.get("nearby_items"), 700),
        "current_outfit": current.get("current_outfit"),
        "uniform_worn": current.get("uniform_worn"),
        "last_player_input_from_state": current.get("last_player_input"),
        "player_input_for_this_turn": player_input,
        "header_values": header_values,
        "rendered_header": _render_header(header_values),
        "bottom_block_labels": _bottom_labels(str(header_values.get("pov_display_name") or "Акира")),
        "visible_state": _visible_state_ru(_visible_state(current)),
    }


# ---------------------------------------------------------------------------
# UI panels/contracts
# ---------------------------------------------------------------------------

def _read_project_json(path: str, session_id: str, default: Any) -> Any:
    value = _safe_json(path, session_id, None)
    if value is not None:
        return value
    content, _ = _read_source(path, session_id)
    if not content:
        return default
    try:
        return json.loads(content)
    except Exception:
        return default


def _source_index(paths: list[str]) -> list[dict[str, Any]]:
    return [{"path": p, "kind": _source_kind(p), "required_for_packet": True} for p in paths]


def _character_summary(active: list[str], files: list[str]) -> dict[str, Any]:
    paths_by_character: dict[str, list[str]] = {}
    for cid in active:
        folder = _folder(cid)
        if not folder:
            continue
        wanted = [p for p in files if p.startswith(f"characters/{folder}/") or p == f"state/character_memory/{cid}.json"]
        paths_by_character[cid] = wanted
    return {
        "mode": "summary_only_content_loaded_by_required_chunks",
        "active_character_ids": active,
        "paths_by_character": paths_by_character,
        "rule": "Do not expect full character text inside buildScenePacket. Use already loaded required-file chunks as content source.",
    }


def _relationship_score(data: Any) -> int:
    if sg is not None and hasattr(sg, "_relationship_score"):
        try:
            return int(sg._relationship_score(data))  # type: ignore[attr-defined]
        except Exception:
            pass
    if not isinstance(data, dict):
        return 0
    dyn = data.get("surface_dynamic") if isinstance(data.get("surface_dynamic"), dict) else data
    weights = {
        "affection": 1.2, "trust": 1.2, "respect": 1.0, "interest": 0.8, "curiosity": 0.8,
        "warmth": 1.2, "attachment": 1.5, "tension": -0.8, "irritation": -0.7,
        "fear": -1.0, "resentment": -1.2, "suspicion": -1.0, "jealousy": -0.4,
    }
    total = 0.0
    for key, weight in weights.items():
        try:
            total += float(dyn.get(key) or 0) * weight
        except Exception:
            pass
    return max(-100, min(100, int(round(total))))


def _short_label_from_pair(pair_id: str, data: Any, score: int) -> str:
    if isinstance(data, dict):
        dyn = data.get("surface_dynamic") if isinstance(data.get("surface_dynamic"), dict) else data
        raw_label = _text(dyn.get("label")) if isinstance(dyn, dict) else ""
        if raw_label:
            return raw_label.split(";", 1)[0].strip()[:48]
    pair = pair_id.lower()
    if score <= -60:
        return "враждебность"
    if score <= -35:
        return "сильное напряжение"
    if score <= -15:
        return "настороженность"
    if score <= 14:
        return "неясно"
    if "livia" in pair:
        if score >= 55:
            return "тёплая близость"
        if score >= 35:
            return "старые подруги"
        return "тёплый контакт"
    if "kir" in pair:
        return "доверяет неохотно" if score >= 35 else "осторожный интерес"
    if "haru" in pair:
        return "тянется ближе" if score >= 35 else "явный интерес"
    if "raiden" in pair:
        return "молча наблюдает" if score >= 35 else "холодная настороженность"
    return "доверие" if score >= 35 else "интерес"


def _relationship_ui_panel(session_id: str, chars: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for rel in _relationship_pair_files(chars):
        pair_id = rel.rsplit("/", 1)[-1].removesuffix(".json")
        data = _read_project_json(rel, session_id, {})
        score = _relationship_score(data)
        a, _, b = pair_id.partition("__")
        items.append({
            "pair_id": pair_id,
            "display": f"{_display_name(a)} ↔ {_display_name(b)}",
            "score": score,
            "label": _short_label_from_pair(pair_id, data, score),
            "changed_this_turn": False,
            "render_line": f"{_display_name(a)} ↔ {_display_name(b)}: {score} · {_short_label_from_pair(pair_id, data, score)}",
        })
    return {
        "format": "compact_numeric_relationship_panel_v1",
        "items": items,
        "render_rule": "If items is not empty, render ✦ Отношения with up to 3 item.render_line values. Do not write prose summaries like 'Ливия заботится через шум'.",
        "required_when_items_nonempty": True,
        "omit_rule": "Omit the block only when items is empty. Do not use 'Без изменений' while render_line items exist.",
    }


def _levels_ui_panel(session_id: str) -> dict[str, Any]:
    progress = _safe_json("state/akira_progress_state.json", session_id, {})
    state = progress.get("akira_progress_state") if isinstance(progress, dict) else {}
    if not isinstance(state, dict):
        state = {}
    return {
        "format": "compact_numeric_levels_panel_v1",
        "source": "state/akira_progress_state.json",
        "visible_current": {
            key: state.get(key) for key in [
                "physical_power", "stamina", "agility", "combat_habit", "fatigue",
                "injury_level", "energy_access", "energy_control", "energy_capacity_visible", "energy_risk",
            ] if key in state
        },
        "render_rule": "Show only when body/position/resources/risk changed or the player needs the numbers now. Do not mix hidden potential into current usable power.",
    }


def _footer_contract() -> dict[str, Any]:
    return {
        "format": "footer_3x3x3_v1",
        "actions": {
            "label": "✦ Что можно сделать",
            "exact_count_if_shown": 3,
            "rule": "Three concrete player action options, no numbering, no extra fourth/fifth option.",
        },
        "say": {
            "label_template": "✦ Что <POV> могла бы сказать",
            "exact_count_if_shown": 3,
            "forbid_speaker_prefix": True,
            "forbidden_prefix_examples": ["Акира —", "Ливия —", "Райден —", "Хару —", "Кир —"],
            "forbid_quotes": True,
            "rule": "Only the candidate line itself. Match current POV voice; for Akira: short, dry, sharp/poisonous, controlled.",
        },
        "thoughts": {
            "label_template": "✦ Мысли <POV>",
            "exact_count_if_shown": 3,
            "max_chars_each": 140,
            "forbid_paragraph": True,
            "rule": "Three separate short one-line thoughts, current POV only.",
        },
        "relationships": {
            "label": "✦ Отношения",
            "required_when": "scene_packet.ui_panels.relationships.items is not empty",
            "max_lines": 3,
            "format": "Use item.render_line: '<pair>: <score> · <label>'.",
            "forbid_prose_summary": True,
        },
    }


def _strict_output_contract(session_id: str) -> dict[str, Any]:
    contract = _read_project_json("gpt/scene_output_contract_1198.json", session_id, {})
    if not isinstance(contract, dict):
        contract = {}
    return {
        "source": "gpt/scene_output_contract_1198.json",
        "contract_id": contract.get("id", "scene_output_contract_1198"),
        "version": contract.get("version", "v6-footer-3x3x3"),
        "visible_scene_must_start_with_header": True,
        "rendered_header_source": "scene_packet.current_frame.rendered_header",
        "writer_rule": "Copy scene_packet.current_frame.rendered_header exactly as the first visible block. Do not rebuild the header manually.",
        "dialogue_format_required": contract.get("dialogue_format_required", "**Имя/видимый дескриптор** — реплика."),
        "unknown_name_rule": contract.get("unknown_name_rule", []),
        "prose_rules": contract.get("prose_rules", []),
        "player_input_order_rules": contract.get("player_input_order_rules", [
            "Render scene_packet.player_input.segments in exact order.",
            "Speech segments are exact POV speech.",
            "Parenthetical segments are action/thought/pause beats.",
            "Never merge speech across a parenthetical beat.",
        ]),
        "bottom_blocks_order": contract.get("bottom_blocks_order", [
            "✦ Что можно сделать",
            "✦ Что {POV} могла бы сказать / мог(ла) бы сказать",
            "✦ Мысли {POV}",
            "✦ Уровни",
            "✦ Отношения",
        ]),
        "bottom_blocks_rules": contract.get("bottom_blocks_rules", []),
        "relationship_panel_rules": contract.get("relationship_panel_rules", []),
        "footer_count_rules": contract.get("footer_count_rules", _footer_contract()),
        "footer_contract": _footer_contract(),
        "fallback_forbidden": "Never invent a loose markdown header if this contract is present. If packet_status is not ready, do not write scene.",
    }


def _output_template() -> dict[str, Any]:
    return {
        "format": "academy_rendered_header_v6_footer_3x3x3",
        "header": "Copy scene_packet.current_frame.rendered_header exactly; no loose markdown fallback.",
        "dialogue": "**Имя/видимый дескриптор** — реплика.",
        "player_input": "Use scene_packet.player_input.segments in order: speech / parenthetical beat / speech.",
        "bottom_blocks": ["✦ Что можно сделать", "✦ Что [POV] мог(ла) бы сказать", "✦ Мысли [POV]", "✦ Уровни", "✦ Отношения"],
        "footer_contract": _footer_contract(),
        "relationships": "Required numeric compact panel when ui_panels.relationships.items is not empty; no prose summary.",
        "style": "dense readable paragraphs; no micro-lines of 3-5 words",
    }


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
        loaded, missing, source_diag = _load_sources(files, sid, req.max_file_chars, req.max_total_chars) if req.include_sources else ([], [], {"total_chars_sent": 0, "truncated_files": [], "skipped_after_budget": []})

        segments = _player_input_segments(player_input)
        relationship_panel = _relationship_ui_panel(sid, active)
        packet = {
            "packet_version": "scene_packet_v6_slim_ordered_input_footer_3x3x3",
            "packet_status": "ready",
            "mode": req.mode,
            "session_id": sid,
            "current_frame": _current_frame(current, future, active, player_input),
            "player_input": {
                "raw": player_input,
                "speech": _speech(player_input),
                "actions": _parenthetical_actions(player_input),
                "segments": segments,
                "segment_order_rule": "Render segments in exact order. Do not merge speech before/after parentheses. Parentheticals create a pause where the world/NPC may react if the beat is medium/long.",
                "technical_turn_rule": "Debug/audit messages are not gameplay and must not be saved as scene.",
            },
            "context_needs": _context_needs(player_input, active),
            "selection": {
                "full_character_ids": active,
                "reference_character_ids": _reference_ids(current, active),
                "must_load_now_paths": files,
                "rule": "These paths must be loaded through required-files-manifest/chunks. buildScenePacket intentionally contains only slim render/UI data.",
            },
            "characters": _character_summary(active, files),
            "knowledge": {
                "source": "state/character_memory/<id>.json",
                "mode": "content_loaded_by_required_chunks_not_embedded_in_packet",
                "active_character_ids": active,
            },
            "relationships": {
                "source": "state/relationship_pairs/<a>__<b>.json",
                "mode": "compact_ui_panel_not_prose_summary",
                "ui_panel": relationship_panel,
            },
            "ui_panels": {
                "relationships": relationship_panel,
                "levels": _levels_ui_panel(sid),
                "footer": _footer_contract(),
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
                "Do not render relationship block as prose summary; use compact numeric UI or omit.",
                "Do not merge speech segments across parenthetical actions/thoughts.",
                "Do not output more than 3 actions, 3 speech options, or 3 thoughts in footer.",
                "Do not prefix say-options with speaker names like Акира —.",
            ],
            "source_index": _source_index(files) if req.include_source_index else [],
            "render_guard": {
                "packet_owns_scene_format": True,
                "copy_rendered_header_exactly": True,
                "rendered_header_path": "scene_packet.current_frame.rendered_header",
                "do_not_write_scene_if_packet_status_not_ready": True,
                "must_start_with": "🏛️ Академия Астрейн",
                "first_visible_block_must_equal_rendered_header": True,
                "forbidden_header_examples": ["📅 Дата:", "🎒 При себе:", "1198-08-15 · late morning"],
            },
        }
        approx_response_chars = len(json.dumps(packet, ensure_ascii=False))
        diagnostics = {
            "build": "scene_packet_v6_slim_ordered_input_footer_3x3x3",
            "loaded_file_count": len(loaded),
            "missing_file_count": len(missing),
            "selected_path_count": len(files),
            "active_character_count": len(active),
            "approx_scene_packet_chars": approx_response_chars,
            "include_sources": bool(req.include_sources),
            "include_source_index": bool(req.include_source_index),
            **source_diag,
        } if req.include_diagnostics else {}
        return ScenePacketResponse(
            session_id=sid,
            scene_packet=packet,
            loaded_files=[{k: v for k, v in item.items() if k != "content"} for item in loaded] if req.include_sources else [],
            missing_files=missing,
            diagnostics=diagnostics,
        )
    except Exception as exc:  # final safety: never write scene from broken packet
        packet = {
            "packet_version": "scene_packet_v6_slim_ordered_input_footer_3x3x3",
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


app.version = "0.3.77-scene-packet-footer-3x3x3-v6"
