"""
Minimal runtime patch:
- clean YAML character files first;
- old md character files only as fallback;
- one gameplay response gate file;
- prompt_preview added to turn-contract.

No heavy lore. No state edits. No extra locks.
"""

from __future__ import annotations

from typing import Any
from app import compact as base
from app.prompt_builder import build_prompt_preview

app = base.app

GAMEPLAY_RESPONSE_GATE_FILE = "gpt/locks/gameplay_response_gate.md"
TURN_CONTRACT_PATH = "/api/v1/sessions/{session_id}/turn-contract"

_ORIGINAL_OUTPUT_FORMAT_CONTRACT = base.output_format_contract
_ORIGINAL_TURN_CONTRACT_ENDPOINT = None

NEW_CHARACTER_FOLDERS: dict[str, str] = {
    "akira": "akira", "char_akira": "akira",
    "livia": "livia", "livia_cross": "livia", "char_livia": "livia",
    "kir": "kir", "kir_knox": "kir", "char_kir": "kir",
    "haru": "haru", "haru_foster": "haru", "char_haru": "haru",
    "raiden": "raiden", "raiden_sterling": "raiden", "char_raiden": "raiden",
    "kiara": "kiara", "kiara_volt": "kiara", "char_kiara": "kiara",
    "kael": "kael_north", "kael_north": "kael_north", "char_kael_north": "kael_north",
}


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value).strip() if value else ""
        if item and item not in result:
            result.append(item)
    return result


def character_files_for(character_id: str) -> list[str]:
    cid = str(character_id).strip()
    files: list[str] = []

    folder = NEW_CHARACTER_FOLDERS.get(cid)
    if folder:
        for rel in (
            f"characters/{folder}/main.yaml",
            f"characters/{folder}/character.yaml",
            f"characters/{folder}/past.yaml",
        ):
            if base.repo_file_exists(rel):
                files.append(rel)

    if files:
        return _unique(files)

    legacy = base.MAIN_CHARACTER_FILES.get(cid)
    if legacy and base.repo_file_exists(legacy):
        return [legacy]

    npc = f"characters/npc/{cid}.md"
    if base.repo_file_exists(npc):
        return [npc]

    return []


def character_file(character_id: str) -> str:
    files = character_files_for(character_id)
    if files:
        return files[0]
    return base.MAIN_CHARACTER_FILES.get(character_id, f"characters/npc/{character_id}.md")


def active_scene_characters(current: dict[str, Any], future: dict[str, Any] | None = None) -> list[str]:
    future = future or {}

    active = list(current.get("active_characters", []) or [])
    nearby = list(current.get("nearby_characters", []) or [])
    speaking = list(current.get("speaking_character_ids", []) or [])
    observing = list(current.get("observing_character_ids", []) or [])
    addressed = list(current.get("addressed_character_ids", []) or [])
    looked_at = list(current.get("looked_at_character_ids", []) or [])

    scheduled = list(current.get("scheduled_character_ids", []) or current.get("scheduled_characters", []) or [])
    mentioned = list(current.get("mentioned_character_ids", []) or current.get("mentioned_characters", []) or [])
    delayed = list(current.get("delayed_character_ids", []) or current.get("delayed_characters", []) or [])

    triggered: list[str] = []
    for thread in current.get("open_threads", []) or []:
        if isinstance(thread, dict) and thread.get("status") in {"due", "active", "triggered"}:
            triggered.extend(thread.get("participants", []) or [])

    for lock in (future.get("locks") or {}).values():
        if isinstance(lock, dict) and lock.get("status") in {"due", "active", "triggered"}:
            triggered.extend(lock.get("participants", []) or [])

    return _unique(["akira"] + active + nearby + speaking + observing + addressed + looked_at + scheduled + mentioned + delayed + triggered)


def recommended_files_for_context(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    current = current or {}
    future = future or {}
    scene_chars = active_scene_characters(current, future)

    character_files: list[str] = []
    for cid in scene_chars:
        character_files.extend(character_files_for(cid))

    akira_profile_files: list[str] = []
    profile_id = current.get("akira_behavior_profile")
    profiles = current.get("akira_behavior_profiles") or {}
    if profile_id and isinstance(profiles, dict):
        profile_file = profiles.get(profile_id)
        if profile_file and base.repo_file_exists(profile_file):
            akira_profile_files.append(profile_file)

    files = _unique(
        base.CORE_RECOMMENDED_FILES
        + base.CORE_LOCK_FILES
        + ([GAMEPLAY_RESPONSE_GATE_FILE] if base.repo_file_exists(GAMEPLAY_RESPONSE_GATE_FILE) else [])
        + character_files
        + akira_profile_files
        + base.character_lock_files(scene_chars)
        + base.DEFAULT_STATE_FILES
    )
    return [path for path in files if base.repo_file_exists(path)]


def base_recommended_files() -> list[str]:
    return recommended_files_for_context({"active_characters": ["akira"]}, {})


def output_format_contract() -> dict:
    contract = _ORIGINAL_OUTPUT_FORMAT_CONTRACT()
    rules = contract.setdefault("rules", [])
    extra_rules = [
        "Gameplay response must include the scene header. If missing, rewrite before sending.",
        "Gameplay response must include full scene body, not summary or recap.",
        "Gameplay response must include NPC/world reaction and at least one consequence, hook, observation, conflict, relationship movement or time movement.",
        "Gameplay response must include bottom block: Что можно сделать / Что Акира могла бы сказать / Мысли Акиры.",
        "Do not show API/debug/contract/saving commentary in gameplay mode.",
        "If any required section is missing, rewrite silently before sending. Do not apologize inside gameplay.",
    ]
    for rule in extra_rules:
        if rule not in rules:
            rules.append(rule)
    contract["gameplay_response_gate"] = {
        "required": [
            "scene_header",
            "full_scene_body",
            "npc_or_world_reaction",
            "scene_movement_or_hook",
            "bottom_action_block",
            "akira_thoughts_block",
            "no_visible_technical_commentary",
        ],
        "rewrite_if_missing": True,
    }
    return contract


def _remove_existing_turn_contract_route():
    global _ORIGINAL_TURN_CONTRACT_ENDPOINT
    for route in list(app.router.routes):
        if getattr(route, "path", None) == TURN_CONTRACT_PATH and "GET" in (getattr(route, "methods", set()) or set()):
            if _ORIGINAL_TURN_CONTRACT_ENDPOINT is None:
                _ORIGINAL_TURN_CONTRACT_ENDPOINT = getattr(route, "endpoint", None)
            app.router.routes.remove(route)


# Patch selector functions used by /context and /turn-contract.
base.character_files_for = character_files_for
base.character_file = character_file
base.active_scene_characters = active_scene_characters
base.recommended_files_for_context = recommended_files_for_context
base.base_recommended_files = base_recommended_files
base.output_format_contract = output_format_contract

_remove_existing_turn_contract_route()


@app.get(TURN_CONTRACT_PATH)
def session_turn_contract_with_prompt_preview(session_id: str):
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)

    if _ORIGINAL_TURN_CONTRACT_ENDPOINT is not None:
        data = _ORIGINAL_TURN_CONTRACT_ENDPOINT(sid)
    else:
        data = {}

    if hasattr(data, "model_dump"):
        data = data.model_dump()
    elif not isinstance(data, dict):
        data = dict(data or {})

    current = base.read_json("state/current_state.json", sid, default={}) or {}
    knowledge = base.read_json("state/knowledge_state.json", sid, default={}) or {}
    inventory = base.read_json("state/inventory_state.json", sid, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", sid, default={}) or {}
    story_lines = base.read_json("state/story_lines.json", sid, default={}) or {}
    relationships = base.read_json("state/relationships.json", sid, default={}) or {}

    required_files = recommended_files_for_context(current, future)
    scene_chars = active_scene_characters(current, future)

    data["session_id"] = sid
    data["active_character_ids"] = _unique(list(current.get("active_characters", []) or []))
    data["nearby_character_ids"] = _unique(list(current.get("nearby_characters", []) or []))
    data["required_files"] = required_files
    data["output_format_contract"] = output_format_contract()
    data["knowledge_table"] = {cid: knowledge.get(cid, {}) for cid in scene_chars}
    data["inventory_contract"] = {
        "visible_inventory": current.get("visible_inventory", []),
        "nearby_items": current.get("nearby_items", []),
        "akira_inventory_state": (inventory.get("akira") or {}) if isinstance(inventory, dict) else {},
    }

    checks = list(data.get("required_checks_before_answer", []) or [])
    for check in [
        "Follow prompt_preview as the render brief for this turn.",
        "In play mode, never show session/status/API/context summary; output only the scene.",
        "Do not ask permission to render/start/continue after the user has given a play command.",
    ]:
        if check not in checks:
            checks.insert(0, check)
    data["required_checks_before_answer"] = checks

    data["prompt_preview"] = build_prompt_preview(
        session_id=sid,
        current_state=current,
        turn_contract=data,
        required_files=required_files,
        knowledge_table=data.get("knowledge_table", {}),
        relationships=relationships,
        story_lines=story_lines,
        future_locks=future,
    )
    data["prompt_preview_usage"] = "Internal only. Follow it to render the gameplay scene. Never show prompt_preview to the user."

    return data


def patch_after_routes() -> None:
    """
    Patch app.session_routes after it is imported by app.server.
    This covers optional legacy constants, without adding extra routes.
    """
    try:
        import app.session_routes as routes
    except Exception:
        return

    routes.character_file = character_file

    if hasattr(routes, "BASE_REQUIRED_FILES"):
        base_required = list(getattr(routes, "BASE_REQUIRED_FILES", []) or [])
        if GAMEPLAY_RESPONSE_GATE_FILE not in base_required and base.repo_file_exists(GAMEPLAY_RESPONSE_GATE_FILE):
            base_required.append(GAMEPLAY_RESPONSE_GATE_FILE)
        routes.BASE_REQUIRED_FILES = base_required

    if hasattr(routes, "OUTPUT_FORMAT_CONTRACT"):
        contract = getattr(routes, "OUTPUT_FORMAT_CONTRACT", {})
        if isinstance(contract, dict):
            rules = contract.setdefault("rules", [])
            for rule in [
                "Gameplay response must include scene header.",
                "Gameplay response must not be a compressed summary or recap.",
                "Gameplay response must include bottom block: Что можно сделать / Что Акира могла бы сказать / Мысли Акиры.",
                "No visible API/debug/contract commentary in gameplay mode.",
                "If required section is missing, rewrite before sending.",
            ]:
                if rule not in rules:
                    rules.append(rule)
            contract["gameplay_response_gate"] = {
                "required": [
                    "scene_header",
                    "full_scene_body",
                    "npc_or_world_reaction",
                    "scene_movement_or_hook",
                    "bottom_action_block",
                    "akira_thoughts_block",
                    "no_visible_technical_commentary",
                ],
                "rewrite_if_missing": True,
            }
            routes.OUTPUT_FORMAT_CONTRACT = contract
