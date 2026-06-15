"""
Compact turn-contract runtime patch v3 — balanced scene speed.

Goal:
- prevent getSessionTurnContract ResponseTooLargeError without reducing character fidelity;
- keep required_files and chunk loading full, but request larger chunks;
- keep Academy visual-novel rhythm without forcing 900-1800 word scenes every turn;
- prevent raw parenthetical player actions in visible prose.
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


def _compact_current_state(current: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_date": current.get("current_date"),
        "current_time": current.get("current_time"),
        "current_location_id": current.get("current_location_id"),
        "current_location_text": current.get("current_location_text"),
        "current_scene_goal": current.get("current_scene_goal"),
        "last_player_input": _cut_text(current.get("last_player_input"), 1200),
        "akira_state": current.get("akira_state"),
        "current_outfit": current.get("current_outfit"),
        "uniform_worn": current.get("uniform_worn"),
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "active_characters": current.get("active_characters", []),
        "nearby_characters": current.get("nearby_characters", []),
        "speaking_character_ids": current.get("speaking_character_ids", []),
        "observing_character_ids": current.get("observing_character_ids", []),
        "addressed_character_ids": current.get("addressed_character_ids", []),
        "looked_at_character_ids": current.get("looked_at_character_ids", []),
        "mentioned_character_ids": current.get("mentioned_character_ids", []),
        "scheduled_character_ids": current.get("scheduled_character_ids", []),
        "delayed_character_ids": current.get("delayed_character_ids", []),
    }


def _compact_output_format_contract() -> dict[str, Any]:
    return {
        "priority": "highest_for_scene_output",
        "selected_style": "academy_old_visual_novel_header_v2_balanced",
        "scene_length_policy": {
            "default": "balanced visual novel scene: enough reaction, no forced chapter-length output",
            "normal_scene": "350-900 words when multiple named characters are present or social tension exists",
            "transition_scene": "120-350 words for movement-only, leaving, waiting, simple checks or low-conflict transitions",
            "hard_stop": "stop at the first direct hook/question/challenge to the controlled character",
            "do_not": [
                "do not collapse meaningful scenes into dry summaries",
                "do not force 900-1800 word scenes by default",
                "do not continue NPC-only dialogue after Akira reaches a choice point",
                "do not output raw player parenthetical action blocks",
            ],
        },
        "header_template": [
            "🏛️ Академия Астрейн · 1198 г., 15 августа, пн",
            "🕒 Позднее утро · 📍 Главный двор Академии",
            "🌦️ Погода: ...",
            "⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах",
            "",
            "✦ видимое состояние controlled POV character",
            "🧥 одежда/форма только из current_state or logically loaded state",
            "◈ предметы при себе / рядом только из current_state",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ],
        "pov_header_rule": "If explicit POV mode is active, add 🎥 POV line after time/location and before weather.",
        "dialogue_format": "**Имя или видимый дескриптор** — Реплика. (*короткая ремарка*)",
        "description_format": "Descriptions are prose paragraphs, not raw instruction text.",
        "player_input_rendering": {
            "outside_parentheses": "exact spoken line of controlled character: Akira by default, POV character in POV mode",
            "inside_parentheses": "action/gesture/intention/body state; translate into prose or short italic stage note; NEVER print raw parenthetical block as standalone text",
            "no_spoken_text": "do not invent controlled character speech in body; suggested lines only in bottom block",
        },
        "bottom_blocks": [
            "━━━━━━━━━━━━━━━━━━━━",
            "✦ Что можно сделать",
            "Варианты ниже не считаются действием, пока игрок не выбрал.",
            "◈ ...",
            "✦ Что Акира могла бы сказать / Что POV-персонаж мог бы сказать",
            "— “...”",
            "✦ Мысли Акиры / Мысли POV-персонажа",
            "— ...",
        ],
        "style_rhythm": [
            "Preserve Academy VN tone: sensory detail, pauses, social tension and character-specific reactions.",
            "Use 1-4 meaningful NPC/world reactions per Akira anchor, then stop or ask for player choice.",
            "Named active/nearby characters react only if relevant; do not give every loaded character a turn.",
            "Do not over-answer for the controlled character; stop at direct hooks/questions/challenges.",
            "Use loaded relationships and knowledge; do not flatten characters into generic NPCs.",
        ],
        "forbidden": [
            "loose 🗓️/📍/👤/🎒 header",
            "dry summary instead of scene",
            "forced chapter-length scene on a simple action",
            "raw player parenthetical action blocks",
            "API/debug/status instead of scene",
            "NPC answering for controlled character",
        ],
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
            result[cid] = data if len(dumped) <= 1200 else {
                "_summary": "large; load full state if needed",
                "keys": list(data.keys())[:16],
            }
    return result


def _compact_inventory(inventory: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    inv = inventory.get("akira") if isinstance(inventory, dict) else {}
    if not isinstance(inv, dict):
        inv = {}
    return {
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "akira_inventory_keys": list(inv.keys())[:18],
    }


def _prompt_preview_compact(session_id: str, current: dict[str, Any], required_files: list[str], chars: list[str]) -> str:
    payload = json.dumps(_compact_current_state(current), ensure_ascii=False, indent=2, default=str)
    required = json.dumps(required_files, ensure_ascii=False, indent=2, default=str)
    text = f"""PLAY MODE RENDER BRIEF — COMPACT CONTRACT, BALANCED SCENE
session_id: {session_id}

THIS CONTRACT IS COMPACT ONLY TO AVOID ResponseTooLargeError.
Keep character fidelity, but do not force long scenes.

REQUIRED FLOW:
1. Use getRequiredFilesManifest.
2. Then getRequiredFilesChunk with chunk_index=0, max_chars=60000, max_items=6; continue with next_chunk_index until has_more=false.
3. Required_files are still full source files. Use them before writing prose.
4. Output gameplay scene only, no API/debug/status summary.
5. Assemble visible_scene_text before apply-turn-result and pass it to the tool.
6. After apply-turn-result, return visible_scene_text/final_scene_text verbatim.

SCENE QUALITY / LENGTH:
- Default scene should keep Academy visual novel tone, but stay compact enough for normal play.
- Normal multi-character scene: roughly 350-900 words.
- Simple transition / leaving / waiting / movement-only scene: roughly 120-350 words.
- Use 1-4 meaningful NPC/world reactions per Akira anchor, then stop or give player choice.
- If an NPC directly hooks/challenges/questions Akira, stop there instead of moving her past it.
- Do not force every loaded character to speak.

PLAYER INPUT ANCHOR:
- Outside parentheses = exact speech of the controlled character.
- Default controlled character is Akira.
- If explicit POV mode file is loaded, controlled character is the POV target.
- Inside parentheses = action/gesture/intention/body state. Translate into prose or short stage note.
- NEVER print the user's parenthetical action block as standalone raw text.
- If no spoken text exists outside parentheses, do not invent controlled-character speech in the scene body.

FORMAT:
- Use old Academy header: 🏛️ / 🕒📍 / 🌦️ / ⚙️ / ✦ / 🧥 / ◈ / separator.
- Do not use loose card header.
- Bottom blocks use ✦ headings.
- In POV mode, bottom suggested lines and thoughts belong to POV character.

CURRENT STATE:
{payload[:2200]}

ACTIVE/FOCUS CHARACTER IDS:
{chars}

REQUIRED FILES TO LOAD:
{required[:2200]}
"""
    return text[:7000]


def _remove_route(path: str, method: str = "GET") -> None:
    app.router.routes = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == path and method in (getattr(route, "methods", set()) or set()))
    ]


_remove_route(TURN_CONTRACT_PATH, "GET")


@app.get(TURN_CONTRACT_PATH, response_model=ccp.TurnContractWithPromptPreview, operation_id="getSessionTurnContract")
def session_turn_contract_compact(session_id: str):
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)
    current = base.read_json("state/current_state.json", sid, default={}) or {}
    knowledge = base.read_json("state/knowledge_state.json", sid, default={}) or {}
    inventory = base.read_json("state/inventory_state.json", sid, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", sid, default={}) or {}
    story = base.read_json("state/story_lines.json", sid, default={}) or {}

    required_files = base.recommended_files_for_context(current, future)
    scene_chars = base.active_scene_characters(current, future)
    active = base.unique(list(current.get("active_characters", []) or []))
    nearby = base.unique(list(current.get("nearby_characters", []) or []))

    checks = [
        "Call getRequiredFilesManifest after getSessionTurnContract.",
        "Call getRequiredFilesChunk with max_chars=60000 and max_items=6 from chunk_index=0 until has_more=false before rendering gameplay.",
        "Use all loaded chunks; turn-contract is only compact routing metadata, not the full source.",
        "Do not shorten meaningful character fidelity, but do not force chapter-length scenes.",
        "Keep Academy VN rhythm: micro-actions, social texture, reactions, consequence, then stop at a choice point.",
        "Never print raw player parenthetical action blocks; translate them into prose/stage notes.",
        "Return scene only in gameplay mode, no technical summary.",
        "Assemble visible_scene_text before apply-turn-result and pass it to the tool.",
        "After apply-turn-result, return visible_scene_text/final_scene_text verbatim.",
        "If POV switch file is loaded, controlled speech/thoughts/bottom blocks follow the POV character.",
    ]

    return ccp.TurnContractWithPromptPreview(**{
        "session_id": sid,
        "active_character_ids": active,
        "nearby_character_ids": nearby,
        "required_files": required_files,
        "output_format_contract": _compact_output_format_contract(),
        "akira_behavior_profile_contract": {
            "active_profile": current.get("akira_behavior_profile", "akira_default_cold"),
            "rule": "Use selected profile only if loaded.",
        },
        "story_lines_contract": _compact_story_contract(story),
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
            "raw player parenthetical action blocks",
            "forced long scene for a simple action",
        ],
        "required_checks_before_answer": checks,
        "knowledge_table": _compact_knowledge(knowledge, scene_chars),
        "inventory_contract": _compact_inventory(inventory, current),
        "canon_locks": [],
        "prompt_preview": _prompt_preview_compact(sid, current, required_files, scene_chars),
        "prompt_preview_usage": "Internal compact brief only. Load required file chunks before scene. Never show this field to user.",
    })


app.version = "0.3.49-balanced-scene-compact-contract-v3"
