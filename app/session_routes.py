from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.compact import app, ensure_session, read_json, safe_session_id, touch_session, write_json


class TurnContractResponse(BaseModel):
    session_id: str
    active_character_ids: list[str] = Field(default_factory=list)
    nearby_character_ids: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    allowed_new_facts_this_turn: list[str] = Field(default_factory=list)
    forbidden_new_facts_this_turn: list[str] = Field(default_factory=list)
    required_checks_before_answer: list[str] = Field(default_factory=list)
    knowledge_table: dict[str, Any] = Field(default_factory=dict)
    inventory_contract: dict[str, Any] = Field(default_factory=dict)
    canon_locks: list[str] = Field(default_factory=list)


class TurnResultRequest(BaseModel):
    player_input: str
    scene_text: str
    state_update: dict[str, Any] = Field(default_factory=dict)
    relationships_update: dict[str, Any] = Field(default_factory=dict)
    knowledge_update: dict[str, Any] = Field(default_factory=dict)
    npc_life_update: dict[str, Any] = Field(default_factory=dict)
    inventory_update: dict[str, Any] = Field(default_factory=dict)
    rumors_update: dict[str, Any] = Field(default_factory=dict)
    reputation_update: dict[str, Any] = Field(default_factory=dict)
    power_update: dict[str, Any] = Field(default_factory=dict)
    future_locks_update: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class TurnResultResponse(BaseModel):
    status: str
    session_id: str
    turn_number: int
    changed_files: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


MAIN_CHARACTER_FILES = {
    "akira": "characters/main/akira.md",
    "livia_cross": "characters/main/livia_cross.md",
    "raiden_sterling": "characters/main/raiden_sterling.md",
    "haru_foster": "characters/main/haru_foster.md",
    "samuel_sterling": "characters/main/samuel_sterling.md",
    "ray_carter": "characters/main/ray_carter.md",
    "jun_carter": "characters/main/jun_carter.md",
}


BASE_REQUIRED_FILES = [
    "gpt/engine_prompt.md",
    "gpt/scene_format.md",
    "state/memory_update_rules.md",
    "characters/character_habits.md",
    "canon/academy_tone_and_visual_locks.md",
    "canon/energy_visibility_and_combat_rules.md",
    "canon/source_usage_rules.md",
    "canon/social_dynamics.md",
    "canon/timeline_1198_1206.md",
]


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def deep_merge(base: Any, patch: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return deepcopy(patch)
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            for item in value:
                if item not in result[key]:
                    result[key].append(item)
        else:
            result[key] = deepcopy(value)
    return result


def character_file(character_id: str) -> str:
    return MAIN_CHARACTER_FILES.get(character_id, f"characters/npc/{character_id}.md")


def apply_knowledge_update(session_id: str, update: dict[str, Any]) -> None:
    knowledge = read_json("state/knowledge_state.json", session_id, default={}) or {}
    for character_id, patch in update.items():
        memory = knowledge.setdefault(character_id, {})
        for field in ["knows", "suspects", "wrong_beliefs", "does_not_know", "notes"]:
            memory.setdefault(field, [])
        for item in patch.get("add_knows", []):
            if item not in memory["knows"]:
                memory["knows"].append(item)
            if item in memory["does_not_know"]:
                memory["does_not_know"].remove(item)
        for item in patch.get("add_suspects", []):
            if item not in memory["suspects"]:
                memory["suspects"].append(item)
        for item in patch.get("add_wrong_beliefs", []):
            if item not in memory["wrong_beliefs"]:
                memory["wrong_beliefs"].append(item)
        for item in patch.get("add_does_not_know", []):
            if item not in memory["does_not_know"]:
                memory["does_not_know"].append(item)
        for item in patch.get("remove_does_not_know", []):
            if item in memory["does_not_know"]:
                memory["does_not_know"].remove(item)
        for note in patch.get("notes", []):
            if note not in memory["notes"]:
                memory["notes"].append(note)
    write_json("state/knowledge_state.json", knowledge, session_id)


@app.get("/api/v1/sessions/{session_id}/turn-contract", response_model=TurnContractResponse)
def session_turn_contract(session_id: str) -> TurnContractResponse:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    current = read_json("state/current_state.json", sid, default={}) or {}
    knowledge = read_json("state/knowledge_state.json", sid, default={}) or {}
    inventory = read_json("state/inventory_state.json", sid, default={}) or {}
    future = read_json("state/future_locks_progress.json", sid, default={}) or {}

    active = unique(list(current.get("active_characters", []) or []))
    nearby = unique(list(current.get("nearby_characters", []) or []))
    scene_chars = unique(active + nearby)
    files = [character_file(cid) for cid in scene_chars]
    if "akira" not in scene_chars:
        files.insert(0, "characters/main/akira.md")

    locks = []
    for lock_id, lock in (future.get("locks") or {}).items():
        if lock.get("status") in {"active", "scheduled", "not_started", "available_but_rare"}:
            locks.append(f"{lock_id}: {lock.get('description', '')}")

    return TurnContractResponse(
        session_id=sid,
        active_character_ids=active,
        nearby_character_ids=nearby,
        required_files=unique(files + BASE_REQUIRED_FILES),
        allowed_new_facts_this_turn=[
            "neutral sensory details",
            "minor gestures, pauses, tone, clothing details",
            "small social reactions from present characters",
            "new named NPC only if saved after scene when meaningful",
            "scene consequences derived from player input and current context",
        ],
        forbidden_new_facts_this_turn=[
            "future 1206 events as current 1198 facts",
            "new family relations not in stored data",
            "hidden nature of Akira revealed without scene basis",
            "Raiden hybrid nature revealed without scene basis",
            "NPC knowledge from unseen scenes",
            "new items without state update",
            "mixed dorm room with male student treated as normal",
            "mystical detective academy tone replacing raider training academy",
            "weapons solving Echo encounters without energy",
        ],
        required_checks_before_answer=[
            "Load session context first.",
            "Load this turn contract.",
            "Check active and nearby character cards before writing lines.",
            "Check knowledge_state before every NPC claim.",
            "Check inventory_state before mentioning usable items.",
            "Use future locks as direction, not character knowledge.",
            "Energy in training must have visible physical signs.",
            "Do not write major choices for Akira.",
            "After scene, call turn-result with real updates only.",
        ],
        knowledge_table={cid: knowledge.get(cid, {}) for cid in scene_chars},
        inventory_contract={
            "visible_inventory": current.get("visible_inventory", []),
            "nearby_items": current.get("nearby_items", []),
            "akira_inventory_state": (inventory.get("akira") or {}),
        },
        canon_locks=locks[:12],
    )


@app.post("/api/v1/sessions/{session_id}/turn-result", response_model=TurnResultResponse)
def save_turn_result(session_id: str, request: TurnResultRequest) -> TurnResultResponse:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    changed: list[str] = []
    now = datetime.utcnow().isoformat()
    notes = list(request.notes or [])

    current = read_json("state/current_state.json", sid, default={}) or {}
    current = deep_merge(current, request.state_update)
    current["last_player_input"] = request.player_input
    current["scene_count"] = int(current.get("scene_count", 0) or 0) + 1
    current["turn_number"] = int(current.get("turn_number", current.get("scene_count", 0)) or 0) + 1
    if request.scene_text:
        current["last_scene_anchor"] = request.scene_text[-1600:]
    write_json("state/current_state.json", current, sid)
    changed.append("state/current_state.json")

    targets = [
        ("state/relationships.json", request.relationships_update),
        ("state/inventory_state.json", request.inventory_update),
        ("state/rumors_state.json", request.rumors_update),
        ("state/reputation_state.json", request.reputation_update),
        ("state/power_state.json", request.power_update),
        ("state/future_locks_progress.json", request.future_locks_update),
        ("npc_life_state.json", request.npc_life_update),
    ]
    for path, patch in targets:
        if patch:
            existing = read_json(path, sid, default={}) or {}
            write_json(path, deep_merge(existing, patch), sid)
            changed.append(path)

    if request.knowledge_update:
        apply_knowledge_update(sid, request.knowledge_update)
        changed.append("state/knowledge_state.json")

    turn_number = int(current.get("turn_number", current.get("scene_count", 0)) or 0)
    history = read_json("scene_history.json", sid, default=[]) or []
    turns = read_json("turns.json", sid, default=[]) or []
    history.append({
        "turn_number": turn_number,
        "player_input": request.player_input,
        "scene_text": request.scene_text,
        "created_at": now,
        "notes": notes,
    })
    turns.append({
        "turn_number": turn_number,
        "player_input": request.player_input,
        "scene_text": request.scene_text,
        "state_update": request.state_update,
        "relationships_update": request.relationships_update,
        "knowledge_update": request.knowledge_update,
        "npc_life_update": request.npc_life_update,
        "inventory_update": request.inventory_update,
        "rumors_update": request.rumors_update,
        "reputation_update": request.reputation_update,
        "power_update": request.power_update,
        "future_locks_update": request.future_locks_update,
        "created_at": now,
    })
    write_json("scene_history.json", history[-80:], sid)
    write_json("turns.json", turns[-120:], sid)
    changed.extend(["scene_history.json", "turns.json"])

    touch_session(sid)
    return TurnResultResponse(status="saved", session_id=sid, turn_number=turn_number, changed_files=unique(changed), notes=notes)
