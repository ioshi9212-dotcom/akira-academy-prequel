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
    output_format_contract: dict[str, Any] = Field(default_factory=dict)
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
    "canon/novella_goal.md",
    "canon/character_story_roles.md",
    "canon/source_usage_rules.md",
    "canon/character_depth_and_rotation.md",
    "canon/relationship_memory_rules.md",
    "state/memory_update_rules.md",
]


OUTPUT_FORMAT_CONTRACT = {
    "priority": "highest_for_scene_output",
    "description": "Use this format even if old chat context used another style.",
    "scene_header_required": True,
    "dialogue_format": "**Имя** — Реплика. (*короткая ремарка: тон, взгляд, пауза, жест*)",
    "description_format": "*Описание действия, окружения или атмосферы отдельной строкой курсивом.*",
    "rules": [
        "Every spoken line must start with bold speaker name.",
        "After speaker name use long dash.",
        "Dialogue text is plain, not italic and not bold.",
        "Optional short stage note goes after dialogue in italic parentheses.",
        "Stage note must be short: tone, look, pause, gesture, tiny movement.",
        "Do not put long actions in parentheses.",
        "Do not put character thoughts in parentheses.",
        "Descriptions and atmosphere go in separate italic paragraphs.",
        "No direct Akira thoughts inside the scene text.",
        "Akira thoughts only in the bottom block named 'Мысли Акиры'.",
    ],
    "ending_block": [
        "━━━━━━━━━━━━━━━━━━━━",
        "Что можно сделать:",
        "1.",
        "2.",
        "3.",
        "",
        "Что Акира могла бы сказать:",
        "— “...”",
        "— “...”",
        "",
        "Мысли Акиры:",
        "— ...",
        "— ...",
        "━━━━━━━━━━━━━━━━━━━━",
    ],
    "example": [
        "*Ветер протягивает по главному двору запах мокрого бетона и металла. Несколько студентов задерживают взгляд на белых волосах Акиры.*",
        "**Ливия** — Только не говори, что ты опять хочешь кофе без сахара. (*закатывает глаза, но улыбается*)",
        "**Хару** — О, новенькие. И сразу такие серьёзные? (*смотрит на Акиру с открытым интересом*)",
        "**Райден** — Не стой на проходе. (*лениво, не поднимая голоса*)",
    ],
    "self_check": "If the output is not in this format, rewrite it before sending.",
}


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
