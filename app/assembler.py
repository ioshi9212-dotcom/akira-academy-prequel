from __future__ import annotations

import re
from itertools import combinations
from typing import Any

from fastapi import HTTPException

from app.loader import exists, read_json, read_text, read_yaml

SPEECH_OR_PAREN_RE = re.compile(r"(\([^()]*\))")


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value).strip() if value else ""
        if item and item not in result:
            result.append(item)
    return result


def parse_player_input(user_input: str) -> dict[str, Any]:
    """Split player input into speech/action segments while preserving original order."""
    text = user_input or ""
    segments: list[dict[str, str]] = []
    for part in SPEECH_OR_PAREN_RE.split(text):
        if not part:
            continue
        stripped = part.strip()
        if not stripped:
            continue
        if stripped.startswith("(") and stripped.endswith(")"):
            segments.append({"type": "parenthetical", "text": stripped[1:-1].strip()})
        else:
            segments.append({"type": "speech", "text": stripped})
    return {"raw": text, "segments": segments}


def canonicalize_character(raw: str, character_index: dict[str, Any]) -> str | None:
    if not raw:
        return None
    key = str(raw).strip()
    low = key.lower().replace("ё", "е")
    chars = (character_index or {}).get("characters", {})
    for cid, data in chars.items():
        aliases = data.get("aliases", []) if isinstance(data, dict) else []
        keys = [cid] + aliases
        for item in keys:
            item_low = str(item).lower().replace("ё", "е")
            if low == item_low:
                return data.get("canonical_id") or cid
    return None


def detect_addressed_characters(user_input: str, character_index: dict[str, Any]) -> list[str]:
    # Conservative: only explicit aliases/names in player text.
    found: list[str] = []
    low_text = (user_input or "").lower().replace("ё", "е")
    for cid, data in (character_index.get("characters") or {}).items():
        aliases = data.get("aliases", []) if isinstance(data, dict) else []
        for alias in aliases + [cid]:
            alias_s = str(alias).strip()
            if not alias_s:
                continue
            # Russian names can appear as "Лив,"; latin ids as whole words.
            pattern = r"(?<![\wА-Яа-я])" + re.escape(alias_s.lower().replace("ё", "е")) + r"(?![\wА-Яа-я])"
            if re.search(pattern, low_text):
                found.append(data.get("canonical_id") or cid)
                break
    return unique(found)


LOCATION_KEYWORDS = {
    "basketball_court": ["корт", "мяч", "баскетбол", "площадк"],
    "back_court_route": ["задн", "маршрут", "со стороны корта"],
    "registration_area": ["регистрац", "документ", "стойк"],
    "dorm_block": ["общежит", "коридор", "лифт", "лестниц"],
    "room_214": ["214", "комнат"],
    "cafeteria": ["столов", "кофе", "еда", "завтрак", "обед"],
    "medblock": ["медблок", "медосмотр", "врач", "пластыр"],
    "training_blocks": ["трен", "зал", "маты", "спарринг"],
    "energy_practice_yards": ["энерг", "площадк", "датчик"],
    "shooting_range": ["стрельбищ", "оруж", "мишен"],
    "pool": ["бассейн"],
    "tactical_rooms": ["тактик", "аудитор", "лекц"],
    "administrative_building": ["администрац", "куратор", "кабинет"],
}


def detect_target_location(user_input: str, location_index: dict[str, Any]) -> str | None:
    text = (user_input or "").lower().replace("ё", "е")
    for loc_id, words in LOCATION_KEYWORDS.items():
        if any(word in text for word in words):
            return resolve_location_id(loc_id, location_index)
    return None


def resolve_location_id(raw: str | None, location_index: dict[str, Any]) -> str | None:
    if not raw:
        return None
    aliases = location_index.get("aliases") or {}
    if raw in (location_index.get("locations") or {}):
        return raw
    return aliases.get(raw, raw if raw in (location_index.get("locations") or {}) else None)


def location_path(location_id: str | None, location_index: dict[str, Any]) -> str | None:
    if not location_id:
        return None
    entry = (location_index.get("locations") or {}).get(location_id)
    if isinstance(entry, dict):
        return entry.get("path")
    return None


def current_calendar_beat(calendar_day: dict[str, Any], calendar_runtime: dict[str, Any]) -> dict[str, Any]:
    beat_id = calendar_runtime.get("current_beat_id")
    for beat in calendar_day.get("day_beats", []) or []:
        if isinstance(beat, dict) and beat.get("beat_id") == beat_id:
            return beat
    return {}


def resolve_character_scope(
    *,
    current_state: dict[str, Any],
    calendar_day: dict[str, Any],
    calendar_runtime: dict[str, Any],
    character_index: dict[str, Any],
    location_index: dict[str, Any],
    player_input: str,
    current_location_id: str | None,
    target_location_id: str | None,
) -> tuple[list[str], list[str]]:
    active = [canonicalize_character(x, character_index) or x for x in current_state.get("active_characters", []) or []]
    nearby = [canonicalize_character(x, character_index) or x for x in current_state.get("nearby_characters", []) or []]
    addressed = detect_addressed_characters(player_input, character_index)

    beat = current_calendar_beat(calendar_day, calendar_runtime)
    beat_chars = [canonicalize_character(x, character_index) or x for x in beat.get("character_ids", []) or []]

    full = unique(["akira"] + active + nearby + addressed + beat_chars)

    scheduled = [canonicalize_character(x, character_index) or x for x in current_state.get("scheduled_character_ids", []) or []]
    delayed = [canonicalize_character(x, character_index) or x for x in current_state.get("delayed_character_ids", []) or []]

    # Important scene-specific promotions. These are assembly decisions, not GPT locks.
    if target_location_id == "basketball_court" or current_location_id == "basketball_court":
        if "haru" in scheduled:
            full.append("haru")
        # Raiden stays reference until he speaks/is observed/addressed/nearby in state.
    if "raiden" in addressed:
        full.append("raiden")

    full = unique([x for x in full if x])
    reference = unique([x for x in scheduled + delayed if x and x not in full])
    return full, reference


def relationship_pair_paths(full_character_ids: list[str]) -> list[str]:
    paths: list[str] = []
    for a, b in combinations(full_character_ids, 2):
        direct = f"state/relationship_pairs/{a}__{b}.json"
        reverse = f"state/relationship_pairs/{b}__{a}.json"
        if exists(direct):
            paths.append(direct)
        elif exists(reverse):
            paths.append(reverse)
    return unique(paths)


def conditional_state_paths(
    *,
    player_input: str,
    current_location_id: str | None,
    target_location_id: str | None,
) -> list[str]:
    text = (player_input or "").lower().replace("ё", "е")
    locs = {current_location_id, target_location_id}
    paths: list[str] = []

    if locs & {"dorm_block", "room_214"} or any(w in text for w in ["общежит", "комнат", "214", "засел"]):
        paths.append("state/room_assignments.yaml")
    if any(w in text for w in ["сумк", "телефон", "деньг", "форма", "вещ", "карман", "кофе"]):
        paths.append("state/inventory_state.json")
    if any(w in text for w in ["слух", "смотр", "репутац", "толп", "публич"]):
        paths.append("state/reputation_state.json")
        paths.append("state/rumors_state.json")
    if any(w in text for w in ["энерг", "перегруз", "датчик", "трен", "сила", "контроль"]):
        paths.append("state/power_state.json")
        paths.append("state/akira_progress_state.json")
    return [p for p in unique(paths) if exists(p)]


def render_header(current_state: dict[str, Any], calendar_day: dict[str, Any], location_content: dict[str, Any] | None = None) -> str:
    date = calendar_day.get("day_month") or current_state.get("current_date") or "дата не задана"
    year = calendar_day.get("year") or "1198"
    time = current_state.get("current_time") or "время не задано"
    loc = current_state.get("current_location_text") or (location_content or {}).get("name") or current_state.get("current_location_id") or "локация не задана"
    weather = ((current_state.get("weather") or {}).get("summary")) or "не уточнена"
    goal = current_state.get("current_scene_goal") or calendar_day.get("label") or "текущий кадр"
    akira_state = (current_state.get("akira_state") or {}).get("visible_state") or "состояние не уточнено"
    outfit = current_state.get("current_outfit") or "одежда не уточнена"
    items = ", ".join(current_state.get("visible_inventory") or current_state.get("nearby_items") or []) or "нет явно видимых предметов"

    return "\n".join([
        f"🏛️ Академия Астрейн · {year} г., {date}",
        f"🕒 {time} · 📍 {loc}",
        f"🌦️ Погода: {weather}",
        f"⚙️ Активное состояние сцены: {goal}",
        "",
        f"✦ Акира: {akira_state}",
        f"🧥 {outfit}",
        f"◈ {items}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
    ])


def build_scene_packet(session_id: str, user_input: str = "", mode: str = "play") -> dict[str, Any]:
    current_state = read_json("state/current_state.json", session_id, default={}) or {}
    calendar_runtime = read_json("state/calendar_runtime.json", session_id, default={}) or {}
    character_index = read_yaml("characters/index.yaml", session_id, default={}) or {}
    location_index = read_yaml("locations/index.yaml", session_id, default={}) or {}

    current_date = current_state.get("current_date") or calendar_runtime.get("current_date")
    calendar_day_path = f"calendar/days/{current_date}.yaml" if current_date else ""
    calendar_day = read_yaml(calendar_day_path, session_id, default={}) if calendar_day_path else {}

    raw_current_location = current_state.get("current_location_id")
    current_location_id = resolve_location_id(raw_current_location, location_index)
    target_location_id = detect_target_location(user_input, location_index)

    location_ids = unique([x for x in [current_location_id, target_location_id] if x])
    location_paths = [p for p in (location_path(x, location_index) for x in location_ids) if p]

    full_characters, reference_characters = resolve_character_scope(
        current_state=current_state,
        calendar_day=calendar_day or {},
        calendar_runtime=calendar_runtime,
        character_index=character_index,
        location_index=location_index,
        player_input=user_input,
        current_location_id=current_location_id,
        target_location_id=target_location_id,
    )

    char_paths: list[str] = []
    memory_paths: list[str] = []
    for cid in full_characters:
        entry = (character_index.get("characters") or {}).get(cid, {})
        if entry.get("card_path"):
            char_paths.append(entry["card_path"])
        if entry.get("memory_path") and exists(entry["memory_path"], session_id):
            memory_paths.append(entry["memory_path"])

    relationship_paths = relationship_pair_paths(full_characters)
    conditional_paths = conditional_state_paths(
        player_input=user_input,
        current_location_id=current_location_id,
        target_location_id=target_location_id,
    )

    required_files = unique([
        "rules/scene_core.md",
        "state/current_state.json",
        "state/calendar_runtime.json",
        calendar_day_path,
        "characters/index.yaml",
        "locations/index.yaml",
        *location_paths,
        *char_paths,
        *memory_paths,
        *relationship_paths,
        *conditional_paths,
    ])

    loaded: dict[str, str] = {}
    missing: list[str] = []
    for path in required_files:
        if not path:
            continue
        if exists(path, session_id):
            loaded[path] = read_text(path, session_id)
        else:
            missing.append(path)

    loc_content = {}
    if location_paths:
        loc_content = read_yaml(location_paths[0], session_id, default={}) or {}

    rendered_header = render_header(current_state, calendar_day or {}, loc_content)
    packet_status = "ready" if not missing and bool(current_state) and bool(calendar_day) else "missing_files"

    return {
        "session_id": session_id,
        "mode": mode,
        "packet_status": packet_status,
        "rendered_header": rendered_header,
        "player_input": parse_player_input(user_input),
        "current_frame": {
            "current_date": current_date,
            "current_time": current_state.get("current_time"),
            "current_location_id": current_location_id,
            "target_location_id": target_location_id,
            "current_beat_id": calendar_runtime.get("current_beat_id"),
            "active_characters": current_state.get("active_characters", []),
            "nearby_characters": current_state.get("nearby_characters", []),
            "scheduled_character_ids": current_state.get("scheduled_character_ids", []),
            "delayed_character_ids": current_state.get("delayed_character_ids", []),
        },
        "required_files": required_files,
        "loaded_files": loaded,
        "missing_files": missing,
        "full_character_ids": full_characters,
        "reference_character_ids": reference_characters,
        "location_ids_loaded": location_ids,
        "relationship_pairs_loaded": relationship_paths,
    }
