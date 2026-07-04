"""
Scene packet runtime patch v1.

Adds one main gameplay endpoint:
POST /api/v1/sessions/{session_id}/build-scene-packet

Goal:
- GPT sends the latest player input.
- Railway/API builds one compact scene_packet from current state, POV, active/nearby
  characters, character_memory, relationship_pairs, current calendar beat, academy lore
  slice and scene rules.
- GPT writes the scene from that packet instead of manually loading manifest/chunks.
"""
from __future__ import annotations

from typing import Any
import re

from pydantic import BaseModel, Field

from app.context_transport_runtime_patch import app
from app import compact as base
import app.response_size_guard_runtime_patch as sg

SCENE_PACKET_PATH = "/api/v1/sessions/{session_id}/build-scene-packet"


class BuildScenePacketRequest(BaseModel):
    player_input: str | None = None
    mode: str = "game_turn"
    include_sources: bool = True
    include_diagnostics: bool = True
    max_file_chars: int = Field(default=18000, ge=4000, le=60000)
    max_total_chars: int = Field(default=130000, ge=20000, le=220000)


class ScenePacketResponse(BaseModel):
    session_id: str
    mode: str = "scene_packet"
    usage_note: str = (
        "Use this packet as the main gameplay context. Do not call required-files chunks "
        "unless diagnostics or an explicit missing optional source requires it."
    )
    scene_packet: dict[str, Any] = Field(default_factory=dict)
    loaded_files: list[dict[str, Any]] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


CHARACTER_MENTION_HINTS: dict[str, list[str]] = {
    "akira": ["акира", "кира"],
    "livia": ["ливия", "лив", "ливи"],
    "haru": ["хару", "рыж", "рыжий", "мяч", "баскет"],
    "raiden": ["райден", "рейдон", "рей", "тёмн", "темн", "стерлинг", "стэрлинг"],
    "kir": ["кир"],
    "kiara": ["киара", "соперниц"],
    "kael_north": ["каэл", "каел", "норт"],
    "ray_carter": ["рэй", "рей картер", "картер"],
    "jun_carter": ["джун"],
}

MOVEMENT_CHAIN_HINTS = [
    "идти", "пойти", "уйти", "выйти", "зайти", "подойти", "пройти", "дойти",
    "подняться", "спуститься", "к выходу", "к двери", "в комнат", "в душ", "по коридор",
    "на лестниц", "к стойке", "на корт", "в спорт", "в столов", "в общежит",
]

PAST_TRIGGER_HINTS = [
    "прошл", "вспом", "сон", "снится", "травм", "детств", "мать", "отец",
    "пожар", "школ", "кай", "ашер", "самуэль", "джун", "эйрен", "наблюдатель",
]

ENERGY_TRIGGER_HINTS = [
    "энерг", "холод", "жар", "огонь", "простран", "давлен", "свет", "импульс",
    "вибрац", "иней", "перегруз", "контроль", "датчик",
]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower().replace("ё", "е")


def _unique(values: list[Any]) -> list[str]:
    return sg._unique(values)  # type: ignore[attr-defined]


def _canon(value: Any) -> str:
    return sg._canonical_id(value)  # type: ignore[attr-defined]


def _safe_json(path: str, session_id: str, default: Any) -> Any:
    return sg._safe_read_json(path, session_id, default)  # type: ignore[attr-defined]


def _compact(value: Any, limit: int = 1400) -> Any:
    return sg._compact_text(value, limit)  # type: ignore[attr-defined]


def _read_source(path: str, session_id: str) -> tuple[str | None, str | None]:
    return sg._read_required_file_for_bundle_size_guard(path, session_id)  # type: ignore[attr-defined]


def _source_kind(path: str) -> str:
    if path.startswith("characters/"):
        if path.endswith("/past.yaml"):
            return "character_past_triggered"
        return "character_card"
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


def _extract_parenthetical_actions(player_input: str) -> list[str]:
    if not player_input:
        return []
    found = re.findall(r"\(([^)]{1,500})\)", player_input)
    return [_text(item) for item in found if _text(item)]


def _speech_outside_parentheses(player_input: str) -> str:
    if not player_input:
        return ""
    text = re.sub(r"\([^)]*\)", " ", player_input)
    return " ".join(text.split()).strip()


def _mentioned_by_input(player_input: str) -> list[str]:
    low = _lower(player_input)
    result: list[str] = []
    for cid, hints in CHARACTER_MENTION_HINTS.items():
        if any(hint in low for hint in hints):
            result.append(cid)
    return _unique(result)


def _has_any_hint(player_input: str, hints: list[str]) -> bool:
    low = _lower(player_input)
    return any(hint in low for hint in hints)


def _reference_ids(current: dict[str, Any], active: list[str]) -> list[str]:
    values: list[Any] = []
    for field in ("scheduled_character_ids", "delayed_character_ids", "mentioned_character_ids"):
        values.extend(current.get(field, []) or [])
    active_set = set(active)
    result = []
    for raw in values:
        cid = _canon(raw)
        if cid and cid not in active_set:
            result.append(cid)
    return _unique(result)


def _pov_info(current: dict[str, Any], active: list[str]) -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        raw = sg.rt.pov_mode_info(current)  # type: ignore[attr-defined]
        if isinstance(raw, dict):
            info.update(raw)
    except Exception:
        pass
    target = info.get("target_character_id") or current.get("pov") or (active[0] if active else "akira")
    target = _canon(target) or "akira"
    return {
        "pov_character_id": target,
        "pov_display": info.get("target_display_name") or target,
        "rule": "Player controls current POV. Low-stakes automatic POV lines are allowed; meaningful choices stop for player input.",
    }


def _context_needs(player_input: str, current: dict[str, Any], active: list[str]) -> dict[str, Any]:
    actions = _extract_parenthetical_actions(player_input)
    speech = _speech_outside_parentheses(player_input)
    mentions = _mentioned_by_input(player_input)
    movement = _has_any_hint(player_input, MOVEMENT_CHAIN_HINTS)
    past_trigger = _has_any_hint(player_input, PAST_TRIGGER_HINTS)
    energy_trigger = _has_any_hint(player_input, ENERGY_TRIGGER_HINTS)

    directly_relevant = _unique(active + [m for m in mentions if m in set(active)])
    needs = [
        "current_frame",
        "scene_output_template",
        "pov_rules",
        "active_character_cards",
        "active_character_memory",
        "scene_relevant_relationship_pairs",
        "current_calendar_day",
        "academy_location_lore",
        "stop_chain_rules",
        "apply_turn_result_contract",
    ]
    if movement:
        needs.append("movement_chain_interruption_check")
    if past_trigger:
        needs.append("past_trigger_check")
    if energy_trigger:
        needs.append("energy_body_control_rules")
    return {
        "player_speech": speech,
        "player_actions": actions,
        "mentioned_character_ids_from_input": mentions,
        "directly_relevant_character_ids": directly_relevant,
        "needs": _unique(needs),
        "trigger_flags": {
            "movement_chain": movement,
            "past_trigger": past_trigger,
            "energy_trigger": energy_trigger,
            "npc_interruption_must_stop_choice": movement,
        },
        "chain_rule": (
            "A parenthetical movement/action is an intention, not guaranteed completion. "
            "If an NPC meaningfully speaks, blocks, reveals risk, or creates a choice on the way, stop before completing the chain."
        ),
    }


def _extra_lore_files(player_input: str, current: dict[str, Any]) -> list[str]:
    files: list[str] = []
    location = _lower(current.get("current_location_id") or current.get("current_location_text"))
    # Academy slice is small enough and relevant for almost all Academy scenes.
    for rel in (
        "canon_lore/academy/academy_background.yaml",
        "canon_lore/academy/academy_locations.yaml",
    ):
        if sg._repo_exists(rel):  # type: ignore[attr-defined]
            files.append(rel)
    if _has_any_hint(player_input, ENERGY_TRIGGER_HINTS):
        for rel in ("canon_lore/world/energy_system.yaml", "canon_lore/world/kairos.yaml"):
            if sg._repo_exists(rel):  # type: ignore[attr-defined]
                files.append(rel)
    if any(word in location for word in ("academy", "court", "sport", "arrival", "dropoff")):
        pass
    return _unique(files)


def _past_trigger_files(player_input: str, active: list[str]) -> list[str]:
    if not _has_any_hint(player_input, PAST_TRIGGER_HINTS):
        return []
    files: list[str] = []
    for cid in active:
        folder = sg._known_character_folder(cid)  # type: ignore[attr-defined]
        if folder:
            rel = f"characters/{folder}/past.yaml"
            if sg._repo_exists(rel):  # type: ignore[attr-defined]
                files.append(rel)
    if any(name in _lower(player_input) for name in ("кай", "ашер", "слеп")):
        rel = "state/knowledge_threads/kai_asher_school_thread.json"
        if sg._repo_exists(rel):  # type: ignore[attr-defined]
            files.append(rel)
    return _unique(files)


def _packet_file_list(player_input: str, current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    active = sg._scene_chars(current, future)  # type: ignore[attr-defined]
    files: list[str] = []
    files.extend(sg._required_files(current, future))  # type: ignore[attr-defined]
    files.extend(_extra_lore_files(player_input, current))
    files.extend(_past_trigger_files(player_input, active))
    # Always include update rules in packet as compact save contract, not as chunk-only afterthought.
    for rel in (
        "state/update_contracts/turn_update_pipeline_1198.json",
        "state/update_contracts/character_memory_patch_rules_1198.json",
        "state/update_contracts/relationship_pair_patch_rules_1198.json",
        "state/update_contracts/scene_state_patch_rules_1198.json",
    ):
        if sg._repo_exists(rel):  # type: ignore[attr-defined]
            files.append(rel)
    forbidden = {"state/knowledge_state.json", "state/relationships.json"}
    return [f for f in _unique(files) if f not in forbidden and not f.startswith("state/legacy/")]


def _load_sources(paths: list[str], session_id: str, *, max_file_chars: int, max_total_chars: int) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    missing: list[str] = []
    total_chars = 0
    truncated_files: list[str] = []
    skipped_after_budget: list[str] = []
    for path in paths:
        if total_chars >= max_total_chars:
            skipped_after_budget.append(path)
            continue
        content, source = _read_source(path, session_id)
        if content is None:
            missing.append(path)
            continue
        text = str(content)
        original_len = len(text)
        remaining = max_total_chars - total_chars
        file_limit = max(1000, min(max_file_chars, remaining))
        truncated = original_len > file_limit
        if truncated:
            text = text[:file_limit].rstrip() + "\n...<truncated by scene_packet>"
            truncated_files.append(path)
        total_chars += len(text)
        loaded.append({
            "path": path,
            "kind": _source_kind(path),
            "source": source or "project",
            "chars_original": original_len,
            "chars_sent": len(text),
            "truncated": truncated,
            "content": text,
        })
    diagnostics = {
        "total_chars_sent": total_chars,
        "truncated_files": truncated_files,
        "skipped_after_budget": skipped_after_budget,
    }
    return loaded, missing, diagnostics


def _latest_scene_history(session_id: str) -> dict[str, Any]:
    history = _safe_json("state/scene_history.json", session_id, {})
    entries = history.get("entries") if isinstance(history, dict) else []
    if not isinstance(entries, list):
        entries = []
    return {
        "recent_entries": _compact(entries[-5:], 1800),
        "last_entry": _compact(entries[-1], 1200) if entries else None,
    }


def _current_frame(current: dict[str, Any], future: dict[str, Any], player_input: str) -> dict[str, Any]:
    active = sg._scene_chars(current, future)  # type: ignore[attr-defined]
    refs = _reference_ids(current, active)
    return {
        "date": current.get("current_date"),
        "time": current.get("current_time"),
        "location_id": current.get("current_location_id"),
        "location_text": current.get("current_location_text"),
        "scene_goal": current.get("current_scene_goal"),
        "pov": _pov_info(current, active),
        "full_character_ids": active,
        "reference_character_ids": refs,
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
        "do_not_save": [
            "debug/audit user messages as scene turns",
            "routine steps without consequence",
            "old global state/knowledge_state.json as gameplay memory",
            "old global state/relationships.json as gameplay relationship source",
        ],
    }


@app.post(SCENE_PACKET_PATH, response_model=ScenePacketResponse, operation_id="buildScenePacket")
def build_scene_packet(session_id: str, request: BuildScenePacketRequest | None = None) -> ScenePacketResponse:
    req = request or BuildScenePacketRequest()
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)
    player_input = _text(req.player_input)
    current = _safe_json("state/current_state.json", sid, {})
    future = _safe_json("state/future_locks_progress.json", sid, {})
    active = sg._scene_chars(current, future)  # type: ignore[attr-defined]
    tiers = sg._required_file_tiers(current, future)  # type: ignore[attr-defined]
    files = _packet_file_list(player_input, current, future)
    loaded, missing, source_diag = _load_sources(
        files,
        sid,
        max_file_chars=req.max_file_chars,
        max_total_chars=req.max_total_chars,
    ) if req.include_sources else ([], [], {"total_chars_sent": 0})

    relationship_table = sg._read_relationship_pair_table(sid, active)  # type: ignore[attr-defined]
    memory_table = sg._read_character_memory_table(sid, active)  # type: ignore[attr-defined]
    inventory = _safe_json("state/inventory_state.json", sid, {})
    story = _safe_json("state/story_lines.json", sid, {})

    context_needs = _context_needs(player_input, current, active)
    packet = {
        "packet_version": "scene_packet_v1",
        "mode": req.mode,
        "session_id": sid,
        "current_frame": _current_frame(current, future, player_input),
        "player_input": {
            "raw": player_input,
            "speech": context_needs.get("player_speech"),
            "actions": context_needs.get("player_actions"),
            "technical_turn_rule": "If user asks for diagnostics/audit/debug, do not treat as gameplay and do not save as scene.",
        },
        "context_needs": context_needs,
        "selection": {
            "full_character_ids": active,
            "reference_character_ids": _reference_ids(current, active),
            "must_load_now_paths": files,
            "old_required_file_tiers_for_diagnostics": tiers,
            "rule": "Railway selected sources for this turn. GPT should not fetch all project files manually.",
        },
        "knowledge": memory_table,
        "relationships": relationship_table,
        "story_context": sg._story_slice(story),  # type: ignore[attr-defined]
        "scene_history": _latest_scene_history(sid),
        "inventory": {
            "visible_inventory": _compact(current.get("visible_inventory"), 1000),
            "nearby_items": _compact(current.get("nearby_items"), 1000),
            "current_outfit": _compact(current.get("current_outfit"), 1000),
            "akira_inventory_state": _compact((inventory.get("akira") or {}) if isinstance(inventory, dict) else {}, 1000),
        },
        "output_template": sg._small_output_contract(),  # type: ignore[attr-defined]
        "save_contract": _save_contract(),
        "forbidden_context": [
            "Do not use state/knowledge_state.json as runtime knowledge source.",
            "Do not use state/relationships.json as runtime relationship source.",
            "Do not full-load scheduled/delayed characters before entrance/current_frame promotion.",
            "Do not reveal hidden lore as narrator fact, NPC fact, sensor result, or unexplained thought.",
            "Do not complete a movement chain after meaningful NPC interruption; stop at choice.",
        ],
        "loaded_sources": loaded,
    }
    diagnostics = {
        "repo_checked_runtime": "app/server.py imports context_transport_header_hotfix; scene packet patch attaches to same app.",
        "loaded_file_count": len(loaded),
        "missing_file_count": len(missing),
        "selected_path_count": len(files),
        "active_character_count": len(active),
        **source_diag,
    } if req.include_diagnostics else {}
    return ScenePacketResponse(
        session_id=sid,
        scene_packet=packet,
        loaded_files=[{k: v for k, v in item.items() if k != "content"} for item in loaded],
        missing_files=missing,
        diagnostics=diagnostics,
    )


app.version = "0.3.72-scene-packet-v1"
