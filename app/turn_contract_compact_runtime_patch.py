"""
Compact turn-contract runtime patch v1.

Goal: prevent getSessionTurnContract ResponseTooLargeError without reducing scene quality.
Required files and chunk loading remain unchanged; only the contract body is compacted.
"""

from __future__ import annotations

import json
from typing import Any

import app.compact_context_patch as ccp
from app.compact_context_patch import app
from app import compact as base

TURN_CONTRACT_PATH = ccp.TURN_CONTRACT_PATH


def _cut_text(value: Any, limit: int = 900) -> Any:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return value
    return text[:limit].rstrip() + "...<truncated>"


def _compact_list(values: Any, limit: int = 24) -> list[Any]:
    if not isinstance(values, list):
        return []
    return values[:limit]


def _compact_current_state(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_date": current.get("current_date"),
        "current_time": current.get("current_time"),
        "current_location_id": current.get("current_location_id"),
        "current_location_text": current.get("current_location_text"),
        "current_scene_goal": current.get("current_scene_goal"),
        "last_player_input": _cut_text(current.get("last_player_input"), 900),
        "akira_state": current.get("akira_state"),
        "current_outfit": current.get("current_outfit"),
        "uniform_worn": current.get("uniform_worn"),
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "active_characters": current.get("active_characters", []),
        "nearby_characters": current.get("nearby_characters", []),
        "mentioned_character_ids": current.get("mentioned_character_ids", []),
        "scheduled_character_ids": current.get("scheduled_character_ids", []),
        "delayed_character_ids": current.get("delayed_character_ids", []),
    }


def _compact_output_format_contract() -> dict[str, Any]:
    return {
        "priority": "highest_for_scene_output",
        "scene_header": "Use old Academy visual-novel header: 🏛️, 🕒/📍, 🌦️, ⚙️, ✦, 🧥, ◈, separator.",
        "dialogue_format": "**Имя или видимый дескриптор** — Реплика. (*короткая ремарка*)",
        "bottom_blocks": ["✦ Что можно сделать", "✦ Что Акира могла бы сказать", "✦ Мысли Акиры"],
        "forbidden": ["loose 🗓️/📍/👤/🎒 header", "API/debug/status instead of scene", "NPC answering for Akira"],
    }


def _compact_story_contract(story_lines: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(story_lines, dict):
        return {}
    return {
        "required_file": "state/story_lines.json",
        "schema": story_lines.get("schema"),
        "turn_counter": story_lines.get("turn_counter", {}),
        "calendar_policy": story_lines.get("calendar_policy", {}),
        "next_beats": story_lines.get("next_beats", {}),
        "rule": "Dated events/obligations/compaction state go to story_lines. Full file loads through chunks when required.",
    }


def _compact_knowledge(knowledge: dict[str, Any], chars: list[str]) -> dict[str, Any]:
    if not isinstance(knowledge, dict):
        return {}
    result: dict[str, Any] = {}
    for cid in chars:
        data = knowledge.get(cid)
        if isinstance(data, dict):
            dumped = json.dumps(data, ensure_ascii=False, default=str)
            if len(dumped) <= 1200:
                result[cid] = data
            else:
                result[cid] = {
                    "_summary": "knowledge_state for this character is large; load full file through required chunks / json if needed",
                    "keys": list(data.keys())[:20],
                }
    return result


def _compact_inventory(inventory: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    akira_inventory = inventory.get("akira") if isinstance(inventory, dict) else {}
    if not isinstance(akira_inventory, dict):
        akira_inventory = {}
    return {
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "akira_inventory_keys": list(akira_inventory.keys())[:24],
    }


def _prompt_preview_compact(session_id: str, current: dict[str, Any], required_files: list[str], chars: list[str]) -> str:
    compact_current = _compact_current_state(current)
    payload = json.dumps(compact_current, ensure_ascii=False, indent=2, default=str)
    required = json.dumps(required_files, ensure_ascii=False, indent=2, default=str)
    return f"""PLAY MODE RENDER BRIEF — COMPACT
session_id: {session_id}

1. Use getRequiredFilesManifest, then getRequiredFilesChunk chunk_index=0..until has_more=false.
2. Required_files is the source list; do not render from turn-contract alone.
3. Output gameplay scene only, no API/debug/status summary.
4. Everything outside parentheses in player input is Akira's exact speech unless explicit POV mode is loaded.
5. Everything inside parentheses is action/intention, not speech.
6. Stop at direct questions/challenges to the controlled POV character.
7. Use old Academy scene header and bottom ✦ blocks.
8. After scene, call apply-turn-result with visible_scene_text and explicit state changes.

CURRENT STATE:
{payload[:2200]}

ACTIVE/FOCUS CHARACTER IDS:
{chars}

REQUIRED FILES TO LOAD:
{required[:2600]}
"""[:6000]


def _remove_route(path: str, method: str = "GET") -> None:
    keep = []
    for route in app.router.routes:
        if getattr(route, "path", None) == path and method in (getattr(route, "methods", set()) or set()):
            continue
        keep.append(route)
    app.router.routes = keep


_remove_route(TURN_CONTRACT_PATH, "GET")


@app.get(TURN_CONTRACT_PATH, response_model=ccp.TurnContractWithPromptPreview, operation_id="getSessionTurnContract")
def session_turn_contract_compact(session_id: str) -> ccp.TurnContractWithPromptPreview:
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)

    current = base.read_json("state/current_state.json", sid, default={}) or {}
    knowledge = base.read_json("state/knowledge_state.json", sid, default={}) or {}
    inventory = base.read_json("state/inventory_state.json", sid, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", sid, default={}) or {}
    story_lines = base.read_json("state/story_lines.json", sid, default={}) or {}

    required_files = base.recommended_files_for_context(current, future)
    scene_chars = base.active_scene_characters(current, future)
    active = base.unique(list(current.get("active_characters", []) or []))
    nearby = base.unique(list(current.get("nearby_characters", []) or []))

    checks = [
        "Call getRequiredFilesManifest after getSessionTurnContract.",
        "Call getRequiredFilesChunk from chunk_index=0 until has_more=false before rendering gameplay.",
        "Use all loaded chunks; turn-contract is only compact routing metadata.",
        "Return scene only in gameplay mode, no technical summary.",
        "Assemble visible_scene_text before apply-turn-result and pass it to the tool.",
        "After apply-turn-result, return visible_scene_text/final_scene_text verbatim.",
        "Do not count technical/debug/audit/rule-edit/API-check turns as game turns.",
    ]

    data = {
        "session_id": sid,
        "active_character_ids": active,
        "nearby_character_ids": nearby,
        "required_files": required_files,
        "output_format_contract": _compact_output_format_contract(),
        "akira_behavior_profile_contract": {
            "active_profile": current.get("akira_behavior_profile", "akira_default_cold"),
            "rule": "Use selected profile only if profile files are loaded in required chunks.",
        },
        "story_lines_contract": _compact_story_contract(story_lines),
        "allowed_new_facts_this_turn": [
            "neutral sensory details",
            "minor gestures/pauses/tone",
            "small social reactions from present characters",
            "scene consequences derived from loaded context",
        ],
        "forbidden_new_facts_this_turn": [
            "hidden lore as NPC knowledge without source",
            "new items without state update",
            "NPC answering for controlled character",
            "old loose header format",
            "technical summary instead of scene",
        ],
        "required_checks_before_answer": checks,
        "knowledge_table": _compact_knowledge(knowledge, scene_chars),
        "inventory_contract": _compact_inventory(inventory, current),
        "canon_locks": [],
        "prompt_preview": _prompt_preview_compact(sid, current, required_files, scene_chars),
        "prompt_preview_usage": "Internal compact brief only. Load required file chunks before scene. Never show this field to user.",
    }
    return ccp.TurnContractWithPromptPreview(**data)


app.version = "0.3.46-compact-turn-contract-v1"
