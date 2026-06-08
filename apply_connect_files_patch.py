from pathlib import Path

path = Path("app/compact.py")
text = path.read_text(encoding="utf-8")

def must_replace(old: str, new: str, label: str):
    global text
    if old not in text:
        raise SystemExit(f"PATCH FAILED: {label}")
    text = text.replace(old, new, 1)

must_replace(
"""DEFAULT_STATE_FILES = [
    "state/story_lines.json",
    "state/knowledge_state.json",
    "state/relationships.json",
    "state/scene_history.json",
    "state/reputation_state.json",
    "state/rumors_state.json",
]
""",
"""DEFAULT_STATE_FILES = [
    "state/story_lines.json",
    "state/knowledge_state.json",
    "state/relationships.json",
    "state/scene_history.json",
    "state/reputation_state.json",
    "state/rumors_state.json",
    "state/open_threads.json",
    "state/shared_incidents.json",
    "state/gossip_state.json",
    "state/rating_state.json",
    "state/director_short_plan.json",
]

NEW_CHARACTER_FOLDERS = {
    "akira": "akira", "char_akira": "akira",
    "livia": "livia", "livia_cross": "livia", "char_livia": "livia",
    "kir": "kir", "kir_knox": "kir", "char_kir": "kir",
    "haru": "haru", "haru_foster": "haru", "char_haru": "haru",
    "raiden": "raiden", "raiden_sterling": "raiden", "char_raiden": "raiden",
    "kiara": "kiara", "kiara_volt": "kiara", "char_kiara": "kiara",
    "kael": "kael_north", "kael_north": "kael_north", "char_kael_north": "kael_north",
}

CANON_LORE_FILES = [
    "canon/lore/index.yaml",
    "canon/lore/world.yaml",
    "canon/lore/academy.yaml",
    "canon/lore/energy.yaml",
    "canon/lore/social.yaml",
    "canon/lore/factions.yaml",
    "canon/lore/start_1198.yaml",
]

DIRECTOR_RULE_FILES = [
    "gpt/director/scene_must_move_rules.md",
    "gpt/director/routine_compression_rules.md",
    "gpt/director/ambient_story_systems.md",
    "gpt/director/director_short_plan_rules.md",
    "gpt/director/hidden_dream_rules.md",
    "gpt/locks/play_mode_silence_lock.md",
]
""",
"DEFAULT_STATE_FILES block"
)

must_replace(
"""def character_file(character_id: str) -> str:
    return MAIN_CHARACTER_FILES.get(character_id, f"characters/npc/{character_id}.md")
""",
"""def character_files_for(character_id: str) -> list[str]:
    files: list[str] = []
    folder = NEW_CHARACTER_FOLDERS.get(character_id)
    if folder:
        for rel in (
            f"characters/{folder}/main.yaml",
            f"characters/{folder}/character.yaml",
            f"characters/{folder}/past.yaml",
        ):
            if repo_file_exists(rel):
                files.append(rel)
    legacy = MAIN_CHARACTER_FILES.get(character_id)
    if legacy and repo_file_exists(legacy):
        files.append(legacy)
    elif not files:
        npc = f"characters/npc/{character_id}.md"
        if repo_file_exists(npc):
            files.append(npc)
    return unique(files)

def character_file(character_id: str) -> str:
    files = character_files_for(character_id)
    return files[0] if files else MAIN_CHARACTER_FILES.get(character_id, f"characters/npc/{character_id}.md")
""",
"character_file"
)

must_replace(
"""    speaking = list(current.get("speaking_character_ids", []) or [])
    observing = list(current.get("observing_character_ids", []) or [])
    addressed = list(current.get("addressed_character_ids", []) or [])
    looked_at = list(current.get("looked_at_character_ids", []) or [])
""",
"""    speaking = list(current.get("speaking_character_ids", []) or [])
    observing = list(current.get("observing_character_ids", []) or [])
    addressed = list(current.get("addressed_character_ids", []) or [])
    looked_at = list(current.get("looked_at_character_ids", []) or [])
    scheduled = list(current.get("scheduled_character_ids", []) or current.get("scheduled_characters", []) or [])
    mentioned = list(current.get("mentioned_character_ids", []) or current.get("mentioned_characters", []) or [])
    delayed = list(current.get("delayed_character_ids", []) or current.get("delayed_characters", []) or [])
""",
"active_scene_characters lists"
)

must_replace(
"""    return unique(["akira"] + active + nearby + speaking + observing + addressed + looked_at + triggered)
""",
"""    return unique(["akira"] + active + nearby + speaking + observing + addressed + looked_at + scheduled + mentioned + delayed + triggered)
""",
"active_scene_characters return"
)

must_replace(
"""    scene_chars = active_scene_characters(current, future)
    character_files = [character_file(cid) for cid in scene_chars]
""",
"""    scene_chars = active_scene_characters(current, future)
    character_files: list[str] = []
    for cid in scene_chars:
        character_files.extend(character_files_for(cid))
""",
"recommended character files"
)

must_replace(
"""        + CORE_LOCK_FILES
        + character_files
""",
"""        + CORE_LOCK_FILES
        + CANON_LORE_FILES
        + DIRECTOR_RULE_FILES
        + character_files
""",
"recommended lore/director include"
)

path.write_text(text, encoding="utf-8")
print("OK: app/compact.py patched for clean character/lore/director files.")
