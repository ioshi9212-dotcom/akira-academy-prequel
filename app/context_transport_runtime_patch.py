"""
Runtime patch v9: medium-quality selective context + visual header format + schedule-aware digest.

Goals:
- keep gameplay context selective, not full bundle;
- stop stale active_characters from sticking forever;
- expose repairSceneRoster endpoint;
- reduce chunk calls without triggering ResponseTooLargeError.

Install:
    app/server.py -> from app.context_transport_runtime_patch import app
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

# Keep compatibility with previous patch chain.
# state_write_runtime_patch may import compact_context_patch internally.
try:
    import app.state_write_runtime_patch as state_write_patch  # type: ignore
except Exception:
    state_write_patch = None  # noqa: N816

try:
    import app.selective_context_patch as previous_selective  # type: ignore
except Exception:
    previous_selective = None  # noqa: N816

from app import compact as base
import app.compact_context_patch as ccp

app = base.app
app.version = "0.3.24-context-format-v9"

RUNTIME_DIGEST_FILE = "runtime/scene_context_digest.md"
_ORIGINAL_BASE_OUTPUT_FORMAT_CONTRACT = base.output_format_contract
_ORIGINAL_CCP_OUTPUT_FORMAT_CONTRACT = ccp.output_format_contract

MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest

Use this instead of loading the full heavy scene_format.md in normal gameplay.

Visible scene format MUST be aesthetic markdown, not a plain technical list.

Scene header format:
- The scene must start with a compact emoji + markdown header.
- Do NOT write raw field list like: "Дата:", "Погода:", "Акира:", "Рядом:" as plain lines.
- Use a visual-novel header like this:

### 🗓️ 1198-08-15 · позднее утро
**📍 Академия Астрейн, главный двор — линия регистрации у западной арки**

🌦️ *Ясно после ночного дождя; мокрые плиты двора светятся на солнце.*
👤 **Акира:** *внешне спокойна; белые волосы распущены; на щеке пластырь Ливии.*
🎒 **Рядом:** *дорожная сумка / багаж Акиры.*

Then continue with living prose.

Required feel:
- Scene should read like visual-novel prose, not like a form/card/table.
- Header must have emojis and bold markdown markers for place/Akira/nearby info.
- Header should be compact and atmospheric, not a questionnaire.
- Do not over-explain technical state in the visible scene.
- Do not answer with technical commentary after the scene.
- Keep the world moving: every scene needs a concrete hook, reaction, social pressure, small conflict, or transition.
- Use atmospheric details, but do not drown the player action.
- NPCs should act from loaded character files, relationship slice, calendar slice, and knowledge slice.
- Do not flatten characters into one trait: Livia is not only “loud”; Kir is not only “sarcastic”; Akira is not only “cold”.
- Use silence, glances, pauses, crowd pressure, and small physical reactions as scene tools.
- Bottom blocks are allowed, but should be compact and organic, not a heavy RPG menu.

Dialogue:
- Spoken line format: **Name/visible descriptor** — speech. (*short italic remark if needed*)
- Descriptions are separate italic paragraphs.
- Avoid long action text inside dialogue parentheses.
- Akira does not speak unless the player wrote her direct speech outside parentheses.
- Akira’s internal thoughts belong in the bottom “Мысли Акиры” block only.

Bottom blocks format:
### 🎯 Что можно сделать
— ...

### 💬 Что Акира могла бы сказать
— ...

### 🧠 Мысли Акиры
...

Pacing:
- If the player asks to go/wait/eat/sleep, compress unimportant transit and land on the next meaningful beat.
- Do not ask for permission to continue when the player already gave an action.
- If a procedure is active (registration/scanner/check), do not auto-complete it unless the player action clearly does that.
"""

MEDIUM_ENGINE_DIGEST = """
## Medium engine behavior digest

Normal gameplay must balance speed and quality.
- Required files are selective, but the scene should still feel complete.
- Always check the Calendar slice / Schedule appearance rules before introducing Haru, Raiden, Kiara, Kael, or other non-roster characters.
- Calendar entries are opportunities and constraints, not automatic active roster.
- Use runtime digest for state/canon/rules and full character files for present characters.
- If a character is not in roster/nearby/mentioned/scheduled and not due by calendar, do not write them into the scene.
- If current roster is stale, use repairSceneRoster instead of loading extra characters.
- State update after scene must be explicit: backend does not infer from prose.
- If relationships, knowledge, story lines, current location, roster, inventory, calendar beat, or obligations changed, send explicit apply-turn-result payload.
"""

MEDIUM_SOURCE_USAGE_DIGEST = """
## Medium source usage digest

Priority order:
1. Player input for Akira's direct speech/action.
2. Current state and scene roster.
3. Character files for present characters.
4. Relationship slice for pairs in scene.
5. Knowledge slice for who knows what.
6. Story_lines slice for dated events, obligations, and next hooks.
7. Rule digest / locks.

Do not invent hidden knowledge for NPCs.
If source is missing, write suspicion, question, wrong assumption, silence, or visible reaction instead of factual certainty.
"""

MEDIUM_RELATIONSHIP_DIGEST = """
## Medium relationship memory digest

Relationships are behavioral memory, not just scores.
Use relationship slice to decide:
- who stands closer or farther;
- who covers tension with jokes;
- who watches too carefully;
- who tests boundaries;
- who becomes jealous, protective, wary, curious, or annoyed.

Only use relationship pairs where both characters are in current scene focus unless a third character is explicitly mentioned or scheduled.
If the scene changes a relationship, save it through relationship_changes.
"""


def medium_output_format_contract() -> dict[str, Any]:
    try:
        original = _ORIGINAL_CCP_OUTPUT_FORMAT_CONTRACT()
    except Exception:
        try:
            original = _ORIGINAL_BASE_OUTPUT_FORMAT_CONTRACT()
        except Exception:
            original = {}
    if not isinstance(original, dict):
        original = {}

    rules = list(original.get("rules", []) or [])
    required_rules = [
        "Scene MUST start with compact emoji markdown header, not a plain field list.",
        "Header format: ### 🗓️ date · time, then **📍 place**, 🌦️ weather, 👤 **Акира:**, 🎒 **Рядом:** when relevant.",
        "Bottom blocks should use markdown headers with emojis: ### 🎯 Что можно сделать / ### 💬 Что Акира могла бы сказать / ### 🧠 Мысли Акиры.",
        "Do not output technical commentary after a gameplay scene.",
        "Use visual-novel prose after the header; do not write the scene as a card/table/form.",
    ]
    for rule in reversed(required_rules):
        if rule not in rules:
            rules.insert(0, rule)

    original["rules"] = rules
    original["scene_header_template"] = {
        "required": True,
        "style": "emoji_markdown_visual_novel",
        "example": [
            "### 🗓️ 1198-08-15 · позднее утро",
            "**📍 Академия Астрейн, главный двор — линия регистрации у западной арки**",
            "🌦️ *Ясно после ночного дождя; мокрые плиты двора светятся на солнце.*",
            "👤 **Акира:** *внешне спокойна; белые волосы распущены; на щеке пластырь Ливии.*",
            "🎒 **Рядом:** *дорожная сумка / багаж Акиры.*",
        ],
        "forbidden": [
            "plain raw field list without emojis",
            "large questionnaire-like header",
            "technical session/status/API text in gameplay",
        ],
    }
    original["bottom_blocks_template"] = {
        "required": True,
        "headers": [
            "### 🎯 Что можно сделать",
            "### 💬 Что Акира могла бы сказать",
            "### 🧠 Мысли Акиры",
        ],
    }
    return original


MINIMAL_LOCK_FILES = [
    "gpt/locks/gameplay_response_gate.md",
    "gpt/locks/player_input_anchor_lock.md",
    "gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md",
    "gpt/locks/dialogue_format_strict_lock.md",
    "gpt/locks/no_empty_scenes_lock.md",
    "gpt/locks/state_update_payload_contract.md",
    "gpt/locks/selective_context_runtime_lock.md",
]

ROSTER_FIELDS = [
    "active_characters",
    "nearby_characters",
    "speaking_character_ids",
    "observing_character_ids",
    "addressed_character_ids",
    "looked_at_character_ids",
    "mentioned_character_ids",
    "scheduled_character_ids",
    "delayed_character_ids",
]

CHARACTER_FIELDS = [
    "active_characters",
    "nearby_characters",
    "speaking_character_ids",
    "observing_character_ids",
    "addressed_character_ids",
    "looked_at_character_ids",
    "mentioned_character_ids",
    "scheduled_character_ids",
    "delayed_character_ids",
]

SCENE_GROUP_IDS = {
    "block_b_dorm_staff",
    "new_students_block_b",
    "students",
    "staff",
    "crowd",
    "academy_staff",
}

ID_ALIASES = {
    "char_akira": "akira",
    "livia_cross": "livia",
    "char_livia": "livia",
    "kir_knox": "kir",
    "char_kir": "kir",
    "raiden_sterling": "raiden",
    "char_raiden": "raiden",
    "haru_foster": "haru",
    "char_haru": "haru",
    "kiara_volt": "kiara",
    "char_kiara": "kiara",
    "kael": "kael_north",
    "north": "kael_north",
    "char_kael_north": "kael_north",
}


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value).strip() if value else ""
        if item and item not in result:
            result.append(item)
    return result


def canonical_id(value: Any) -> str:
    raw = str(value or "").strip()
    return ID_ALIASES.get(raw, raw)


def known_character_folder(cid: str) -> str | None:
    canon = canonical_id(cid)
    folders = getattr(ccp, "NEW_CHARACTER_FOLDERS", {}) or {}
    if canon in folders:
        return folders[canon]
    if cid in folders:
        return folders[cid]
    return None


def is_known_character_id(cid: str) -> bool:
    return bool(known_character_folder(cid))


def scene_character_ids(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    current = current or {}
    ids: list[str] = ["akira"]

    for field in CHARACTER_FIELDS:
        for value in current.get(field, []) or []:
            cid = canonical_id(value)
            if cid not in SCENE_GROUP_IDS and is_known_character_id(cid):
                ids.append(cid)

    # Future locks are allowed only when already due/active/triggered, not merely scheduled far ahead.
    future = future or {}
    for lock in (future.get("locks") or {}).values():
        if not isinstance(lock, dict):
            continue
        if lock.get("status") not in {"due", "active", "triggered"}:
            continue
        for value in lock.get("participants", []) or []:
            cid = canonical_id(value)
            if cid not in SCENE_GROUP_IDS and is_known_character_id(cid):
                ids.append(cid)

    return _unique(ids)


def character_files_for_context(cid: str, *, include_past: bool = True) -> list[str]:
    folder = known_character_folder(cid)
    if not folder:
        return []
    candidates = [
        f"characters/{folder}/character.yaml",
    ]
    if include_past:
        candidates.append(f"characters/{folder}/past.yaml")
    # main.yaml is small/optional; include after character/past only when it exists and does not bloat.
    candidates.append(f"characters/{folder}/main.yaml")
    return [p for p in candidates if base.repo_file_exists(p)]


def lean_recommended_files_for_context(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    current = current or {}
    future = future or {}

    chars = scene_character_ids(current, future)
    files: list[str] = []

    # The digest contains compacted current_state, relationships, story_lines, knowledge and short rule digest.
    files.append(RUNTIME_DIGEST_FILE)

    # Keep only small critical locks as full files.
    for path in MINIMAL_LOCK_FILES:
        if base.repo_file_exists(path):
            files.append(path)

    # Small id index helps with unknown names.
    if base.repo_file_exists("characters/character_id_index.md"):
        files.append("characters/character_id_index.md")

    # Full active character slices. This is what preserves scene quality.
    for cid in chars:
        files.extend(character_files_for_context(cid, include_past=True))

    # Hard cap on required file count as a safety valve, but do not drop active character.yaml.
    return _unique(files)


def same_pair(pair_id: str, focus: set[str]) -> bool:
    parts = {canonical_id(part) for part in str(pair_id).split("__") if part}
    return bool(parts and parts <= focus)


def compact_relationships_scene_pairs_only(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = {canonical_id(x) for x in (focus_ids or ["akira"])}
    pairs = state.get("pairs")
    if not isinstance(pairs, dict):
        return state
    filtered = {pair: data for pair, data in pairs.items() if same_pair(str(pair), focus)}
    return {
        "pairs": filtered,
        "_context_filter": {
            "mode": "scene_pairs_only",
            "focus_character_ids": sorted(focus),
            "visible_pairs": len(filtered),
            "total_pairs": len(pairs),
        },
    }


def compact_knowledge_scene_only(state: Any, focus_ids: list[str]) -> Any:
    if not isinstance(state, dict):
        return state
    focus = {canonical_id(x) for x in (focus_ids or ["akira"])}
    filtered = {}
    for key, value in state.items():
        if canonical_id(key) in focus:
            filtered[key] = value
    return {
        **filtered,
        "_context_filter": {
            "mode": "scene_character_knowledge_only",
            "focus_character_ids": sorted(focus),
            "visible_characters": len(filtered),
            "total_characters": len(state),
        },
    }


def compact_story_lines_scene_only(state: Any, focus_ids: list[str], max_events: int = 20) -> Any:
    if not isinstance(state, dict):
        return state
    focus = {canonical_id(x) for x in (focus_ids or ["akira"])}
    lines = state.get("lines")
    visible_lines = {}
    if isinstance(lines, dict):
        for line_id, line in lines.items():
            if not isinstance(line, dict):
                continue
            ids = {canonical_id(x) for x in (line.get("character_ids", []) or [])}
            ids |= {canonical_id(x) for x in (line.get("related_ids", []) or [])}
            if ids & focus or line_id in {"academy_arrival", "akira_livia_friendship"}:
                visible_lines[line_id] = line

    shared_events = state.get("shared_events", [])
    if isinstance(shared_events, list):
        shared_events = shared_events[-max_events:]
    else:
        shared_events = []

    return {
        "schema": state.get("schema"),
        "turn_counter": state.get("turn_counter", {}),
        "calendar_policy": state.get("calendar_policy", {}),
        "daily_timeline": base.compact_if_large(state.get("daily_timeline", {}), 1800),
        "shared_events_recent": shared_events,
        "lines": visible_lines,
        "_context_filter": {
            "mode": "scene_story_lines_only",
            "focus_character_ids": sorted(focus),
            "visible_lines": list(visible_lines.keys()),
            "total_lines": len(lines) if isinstance(lines, dict) else 0,
        },
    }


def _json_block(title: str, value: Any, max_chars: int = 4500) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        text = str(value)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...<truncated>"
    return f"\n## {title}\n```json\n{text}\n```\n"


def _date_in_range(current_date: str, key: str) -> bool:
    if "_to_" not in key:
        return key == current_date
    start, end = key.split("_to_", 1)
    return start <= current_date <= end


def build_calendar_slice(current: dict[str, Any], academy_schedule: Any) -> dict[str, Any]:
    current_date = str(current.get("current_date") or "")
    current_time = str(current.get("current_time") or "")

    result: dict[str, Any] = {
        "current_date": current_date,
        "current_time": current_time,
        "matched_periods": {},
        "default_day": {},
        "freedom_rules": [],
        "schedule_appearance_rules": {},
        "calendar_check_rule": [
            "Before introducing Haru/Raiden/Kiara/Kael, check this slice.",
            "If character is only calendar-possible, foreshadow or background them; do not force direct meeting.",
            "If character is active/nearby/mentioned/scheduled in current_state, character files may load and direct scene use is allowed.",
        ],
    }

    if not isinstance(academy_schedule, dict):
        return result

    start_period = academy_schedule.get("start_period", {})
    if isinstance(start_period, dict):
        for key, value in start_period.items():
            if _date_in_range(current_date, str(key)):
                result["matched_periods"][key] = value

    result["default_day"] = academy_schedule.get("default_day", {}) if isinstance(academy_schedule.get("default_day"), dict) else {}
    freedom_rules = academy_schedule.get("freedom_rules", [])
    result["freedom_rules"] = freedom_rules if isinstance(freedom_rules, list) else []

    appearance_rules = academy_schedule.get("character_appearance_rules", {})
    if isinstance(appearance_rules, dict):
        result["schedule_appearance_rules"] = appearance_rules

    return result


def build_scene_context_digest(session_id: str) -> str:
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    chars = scene_character_ids(current, future)

    relationships = compact_relationships_scene_pairs_only(
        base.read_json("state/relationships.json", session_id, default={}) or {},
        chars,
    )
    story_lines = compact_story_lines_scene_only(
        base.read_json("state/story_lines.json", session_id, default={}) or {},
        chars,
    )
    knowledge = compact_knowledge_scene_only(
        base.read_json("state/knowledge_state.json", session_id, default={}) or {},
        chars,
    )
    inventory = base.compact_if_large(base.read_json("state/inventory_state.json", session_id, default={}) or {}, 2200)
    academy_schedule_full = base.read_json("state/academy_schedule.json", session_id, default={}) or {}
    academy_schedule = build_calendar_slice(current, academy_schedule_full)

    rule_digest = {
        "output": [
            "Gameplay only: no API/status/debug summary in final answer.",
            "Scene must start with compact emoji markdown header.",
            "Header example: ### 🗓️ date · time / **📍 place** / 🌦️ weather / 👤 **Акира:** / 🎒 **Рядом:**.",
            "Scene should read like visual-novel prose, not a technical card.",
            "Never use a plain raw field-list header without emojis.",
            "Dialogue format: **Name/descriptor** — speech. (*short italic remark*)",
            "Descriptions are separate italic paragraphs.",
            "Akira thoughts only in bottom block, not inside the scene body.",
            "Bottom blocks use emoji markdown headers.",
            "No empty scene: add hook/reaction/conflict/consequence or time skip.",
            "Do not answer with technical commentary after a gameplay scene.",
        ],
        "state_write": [
            "Backend does not infer state from prose.",
            "If relationships/story/knowledge/current_state change, send explicit state payload to apply-turn-result.",
            "Roster lists are replacement fields, not append-only fields.",
        ],
        "knowledge": [
            "NPC factual claims require known source; otherwise use question/suspicion/wrong assumption/silence.",
        ],
        "relationships": [
            "Use only relationships between scene characters unless another character is explicitly mentioned or scheduled.",
            "Relationships are behavioral memory, not only scores.",
        ],
    }

    text = "# Runtime scene context digest\n"
    text += "This digest replaces heavy global prompt/canon/state files for normal gameplay. Use exact character files also loaded in required_files.\n"
    text += MEDIUM_STYLE_FORMAT_DIGEST + "\n"
    text += MEDIUM_ENGINE_DIGEST + "\n"
    text += MEDIUM_SOURCE_USAGE_DIGEST + "\n"
    text += MEDIUM_RELATIONSHIP_DIGEST + "\n"
    text += _json_block("Rule digest", rule_digest, 4200)
    text += _json_block("Scene character ids", chars, 1200)
    text += _json_block("Current state", current, 4600)
    text += _json_block("Relationship slice", relationships, 5600)
    text += _json_block("Story lines slice", story_lines, 7600)
    text += _json_block("Knowledge slice", knowledge, 5200)
    text += _json_block("Inventory slice", inventory, 2200)
    text += _json_block("Calendar slice", academy_schedule, 5200)
    text += "\n## State update reminder\nIf scene changes roster, use current_state_changes with roster fields as full replacement lists.\n"
    return text


# Save the original reader before monkey-patching ccp._read_required_file_for_bundle.
# Without this, non-runtime required files recurse back into read_required_file_for_bundle.
_ORIGINAL_READ_REQUIRED_FILE_FOR_BUNDLE = ccp._read_required_file_for_bundle


def read_required_file_for_bundle(path: str, session_id: str) -> tuple[str | None, str | None]:
    safe_path = str(path).strip()
    if not safe_path:
        return None, None
    if safe_path == RUNTIME_DIGEST_FILE:
        return build_scene_context_digest(session_id), "runtime"
    return _ORIGINAL_READ_REQUIRED_FILE_FOR_BUNDLE(safe_path, session_id)


def split_text_safe(content: str, part_chars: int) -> list[str]:
    # Keep file pieces reasonably small; response JSON overhead matters.
    part_chars = max(7000, min(int(part_chars or 11000), 11000))
    if not content:
        return [""]
    return [content[i:i + part_chars] for i in range(0, len(content), part_chars)]


def required_file_parts_safe(
    session_id: str,
    *,
    file_part_chars: int = 11000,
) -> tuple[list[str], list[Any], list[Any], list[str]]:
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    required_files = lean_recommended_files_for_context(current, future)

    loaded_parts: list[Any] = []
    manifest: list[Any] = []
    missing_files: list[str] = []

    for file_path in required_files:
        content, source = read_required_file_for_bundle(file_path, session_id)
        if content is None:
            missing_files.append(file_path)
            manifest.append(ccp.RequiredFileManifestItem(path=file_path, exists=False, source="missing"))
            continue

        pieces = split_text_safe(content, file_part_chars)
        manifest.append(
            ccp.RequiredFileManifestItem(
                path=file_path,
                exists=True,
                source=source or "project",
                size_chars=len(content),
                parts_total=len(pieces),
            )
        )
        for index, piece in enumerate(pieces):
            loaded_parts.append(
                ccp.RequiredFileBundleItem(
                    path=file_path,
                    content=piece,
                    part_index=index,
                    parts_total=len(pieces),
                    content_chars=len(piece),
                )
            )

    return required_files, loaded_parts, manifest, missing_files


def chunk_loaded_parts_safe(
    loaded_parts: list[Any],
    *,
    max_chars: int = 30000,
    max_items: int = 3,
) -> list[list[Any]]:
    # Ignore dangerous caller values that can trigger ResponseTooLargeError.
    max_chars = max(16000, min(int(max_chars or 30000), 32000))
    max_items = max(1, min(int(max_items or 3), 3))

    chunks: list[list[Any]] = []
    current: list[Any] = []
    current_chars = 0

    for part in loaded_parts:
        part_chars = len(getattr(part, "content", "") or "")
        if current and (len(current) >= max_items or current_chars + part_chars > max_chars):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(part)
        current_chars += part_chars

    if current:
        chunks.append(current)
    return chunks


def required_files_chunk_response_safe(
    session_id: str,
    *,
    chunk_index: int = 0,
    max_chars: int = 30000,
    max_items: int = 3,
):
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)

    required_files, loaded_parts, _manifest, missing_files = required_file_parts_safe(sid)
    chunks = chunk_loaded_parts_safe(loaded_parts, max_chars=max_chars, max_items=max_items)
    chunks_total = len(chunks)

    safe_chunk_index = max(0, min(int(chunk_index or 0), max(chunks_total - 1, 0))) if chunks_total else 0
    selected = chunks[safe_chunk_index] if chunks_total else []
    has_more = bool(chunks_total and safe_chunk_index < chunks_total - 1)
    next_chunk_index = safe_chunk_index + 1 if has_more else None

    return ccp.RequiredFilesChunkResponse(
        session_id=sid,
        required_files=required_files,
        chunk_index=safe_chunk_index,
        chunks_total=chunks_total,
        has_more=has_more,
        next_chunk_index=next_chunk_index,
        loaded_files=selected,
        missing_files=missing_files,
        loaded_count=len({part.path for part in loaded_parts}),
        missing_count=len(missing_files),
        total_loaded_parts=len(loaded_parts),
    )


def deep_merge_roster_replace(dst: Any, src: Any) -> Any:
    if not isinstance(src, dict):
        return dst
    if not isinstance(dst, dict):
        dst = {}

    for key, value in src.items():
        if key in ROSTER_FIELDS and isinstance(value, list):
            dst[key] = _unique([str(v) for v in value if v is not None])
        elif isinstance(value, dict):
            dst[key] = deep_merge_roster_replace(dst.get(key, {}), value)
        elif isinstance(value, list):
            existing = dst.get(key, [])
            if not isinstance(existing, list):
                existing = []
            for item in value:
                if item not in existing:
                    existing.append(item)
            dst[key] = existing
        else:
            dst[key] = value
    return dst


class RepairSceneRosterRequest(BaseModel):
    active_character_ids: list[str] = Field(default_factory=lambda: ["akira", "livia"])
    nearby_character_ids: list[str] = Field(default_factory=list)
    speaking_character_ids: list[str] = Field(default_factory=list)
    observing_character_ids: list[str] = Field(default_factory=list)
    addressed_character_ids: list[str] = Field(default_factory=list)
    looked_at_character_ids: list[str] = Field(default_factory=list)
    mentioned_character_ids: list[str] = Field(default_factory=list)
    scheduled_character_ids: list[str] = Field(default_factory=list)
    delayed_character_ids: list[str] = Field(default_factory=list)


def _remove_routes(path: str, methods: set[str] | None = None, operation_id: str | None = None) -> None:
    keep = []
    for route in app.router.routes:
        route_path = getattr(route, "path", None)
        route_methods = set(getattr(route, "methods", set()) or set())
        route_operation_id = getattr(route, "operation_id", None)
        match_path = route_path == path
        match_methods = methods is None or bool(route_methods & methods)
        match_operation = operation_id is None or route_operation_id == operation_id
        if match_path and match_methods and match_operation:
            continue
        keep.append(route)
    app.router.routes = keep


# Patch module globals used by compact_context_patch endpoints.
base.active_scene_characters = scene_character_ids
base.recommended_files_for_context = lean_recommended_files_for_context
base.compact_relationships = compact_relationships_scene_pairs_only
base.compact_knowledge = compact_knowledge_scene_only
base.compact_story_lines = compact_story_lines_scene_only
base.deep_merge = deep_merge_roster_replace
base.output_format_contract = medium_output_format_contract

ccp.output_format_contract = medium_output_format_contract
ccp.active_scene_characters = scene_character_ids
ccp.recommended_files_for_context = lean_recommended_files_for_context
ccp._read_required_file_for_bundle = read_required_file_for_bundle
ccp._split_text = split_text_safe
ccp._required_file_parts = required_file_parts_safe
ccp._chunk_loaded_parts = chunk_loaded_parts_safe
ccp._required_files_chunk_response = required_files_chunk_response_safe


# Re-register chunk endpoints with safe defaults and safe clamping.
_remove_routes("/api/v1/sessions/{session_id}/required-files-chunk", {"GET"}, "getRequiredFilesChunk")
_remove_routes("/api/v1/sessions/{session_id}/required-files-bundle", {"GET"}, "getRequiredFilesBundle")


@app.get("/api/v1/sessions/{session_id}/required-files-chunk", response_model=ccp.RequiredFilesChunkResponse, operation_id="getRequiredFilesChunk")
def get_required_files_chunk_safe(
    session_id: str,
    chunk_index: int = 0,
    max_chars: int = 30000,
    max_items: int = 3,
):
    return required_files_chunk_response_safe(
        session_id,
        chunk_index=chunk_index,
        max_chars=max_chars,
        max_items=max_items,
    )


@app.get("/api/v1/sessions/{session_id}/required-files-bundle", response_model=ccp.RequiredFilesChunkResponse, operation_id="getRequiredFilesBundle")
def get_required_files_bundle_safe(
    session_id: str,
    chunk_index: int = 0,
    max_chars: int = 30000,
    max_items: int = 3,
):
    return required_files_chunk_response_safe(
        session_id,
        chunk_index=chunk_index,
        max_chars=max_chars,
        max_items=max_items,
    )


@app.post("/api/v1/sessions/{session_id}/repair/scene-roster", operation_id="repairSceneRoster")
def repair_scene_roster(session_id: str, request: RepairSceneRosterRequest = RepairSceneRosterRequest()):
    sid = base.safe_session_id(session_id)
    base.ensure_session(sid)

    current = base.read_json("state/current_state.json", sid, default={}) or {}
    current["active_characters"] = _unique([canonical_id(x) for x in request.active_character_ids])
    current["nearby_characters"] = _unique([str(x) for x in request.nearby_character_ids])
    current["speaking_character_ids"] = _unique([canonical_id(x) for x in request.speaking_character_ids])
    current["observing_character_ids"] = _unique([canonical_id(x) for x in request.observing_character_ids])
    current["addressed_character_ids"] = _unique([canonical_id(x) for x in request.addressed_character_ids])
    current["looked_at_character_ids"] = _unique([canonical_id(x) for x in request.looked_at_character_ids])
    current["mentioned_character_ids"] = _unique([canonical_id(x) for x in request.mentioned_character_ids])
    current["scheduled_character_ids"] = _unique([canonical_id(x) for x in request.scheduled_character_ids])
    current["delayed_character_ids"] = _unique([canonical_id(x) for x in request.delayed_character_ids])

    base.write_json("state/current_state.json", current, sid)
    return {
        "status": "repaired",
        "session_id": sid,
        "changed_files": ["state/current_state.json"],
        "active_characters": current["active_characters"],
        "nearby_characters": current["nearby_characters"],
    }


# Re-register health to expose version for diagnostics.
_remove_routes("/health", {"GET"})


@app.get("/health")
def health_with_version():
    base.seed()
    return {
        "status": "ok",
        "app": base.APP_NAME,
        "version": app.version,
        "data_dir": str(base.DATA),
        "volume_seeded": (base.DATA / ".seeded").exists(),
        "public_base_url": base.BASE_URL,
    }
