"""
Scene output format runtime patch v23 clean.

Keeps the Academy visual-novel header available without turning style into
several competing prompt locks. Detailed visible format lives in:
- gpt/scene_format.md
- gpt/locks/runtime_scene_rules_digest.md
"""

from __future__ import annotations

from typing import Any

import app.context_transport_runtime_patch as rt
from app.context_transport_runtime_patch import app
from app import compact as base
import app.compact_context_patch as ccp

SCENE_FORMAT_FILE = "gpt/scene_format.md"
RUNTIME_DIGEST_FILE = "runtime/scene_context_digest.md"
RUNTIME_RULES_FILE = "gpt/locks/runtime_scene_rules_digest.md"

_ORIG_RT_LEAN = getattr(rt, "lean_recommended_files_for_context", None)
_ORIG_BASE_RECOMMENDED = getattr(base, "recommended_files_for_context", None)
_ORIG_BUILD_DIGEST = getattr(rt, "build_scene_context_digest", None)


def _unique(paths: list[str]) -> list[str]:
    result: list[str] = []
    for path in paths:
        item = str(path or "").strip()
        if item and item not in result:
            result.append(item)
    return result


def _add_scene_format(paths: list[str]) -> list[str]:
    result: list[str] = []
    for path in paths:
        result.append(path)
        if path == RUNTIME_RULES_FILE and base.repo_file_exists(SCENE_FORMAT_FILE):
            result.append(SCENE_FORMAT_FILE)
    if SCENE_FORMAT_FILE not in result and base.repo_file_exists(SCENE_FORMAT_FILE):
        if RUNTIME_DIGEST_FILE in result:
            result.insert(result.index(RUNTIME_DIGEST_FILE) + 1, SCENE_FORMAT_FILE)
        else:
            result.insert(0, SCENE_FORMAT_FILE)
    return _unique(result)


def recommended_files_with_scene_format(current: dict[str, Any] | None = None, future: dict[str, Any] | None = None) -> list[str]:
    if callable(_ORIG_RT_LEAN):
        files = _ORIG_RT_LEAN(current, future)
    elif callable(_ORIG_BASE_RECOMMENDED):
        files = _ORIG_BASE_RECOMMENDED(current, future)
    else:
        files = []
    return _add_scene_format(list(files or []))


def build_scene_context_digest_with_style(session_id: str) -> str:
    base_digest = _ORIG_BUILD_DIGEST(session_id) if callable(_ORIG_BUILD_DIGEST) else ""
    reminder = """
## Scene output reminder

Use the Academy visual-novel format from gpt/scene_format.md.
Normal narration is plain text. Italics only for short stage remarks or physical details.
Dialogue format: **Name/visible descriptor** — text. (*short remark if needed*)
No quotation marks around dialogue or speech options.
Action options are direct actions, not `Акира может...`.
Header `✦` is short visible condition. Bottom `✦ Уровни` is numeric physical/energy totals.
"""
    return str(base_digest).rstrip() + "\n\n" + reminder.strip() + "\n"


def strict_output_format_contract() -> dict[str, Any]:
    return {
        "priority": "scene_output_format",
        "selected_style": "academy_old_visual_novel_header_v2",
        "header_template": [
            "🏛️ Академия Астрейн · 1198 г., 15 августа, пн",
            "🕒 Позднее утро · 📍 Главный двор Академии",
            "🌦️ Погода: ...",
            "⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах",
            "",
            "✦ short visible Akira condition",
            "🧥 current_outfit_from_state_only",
            "◈ visible carried/nearby items",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ],
        "dialogue_format": "**Имя или видимый дескриптор** — Реплика. (*короткая ремарка*)",
        "bottom_blocks": [
            "━━━━━━━━━━━━━━━━━━━━",
            "✦ Что можно сделать",
            "◈ direct action",
            "✦ Что Акира могла бы сказать",
            "— line without quotation marks",
            "✦ Мысли Акиры",
            "— thought",
            "✦ Уровни",
            "numeric physical/energy totals",
            "✦ Отношения",
            "current total scores",
        ],
        "rules": [
            "Final gameplay answer is the scene only.",
            "Use gpt/scene_format.md and runtime_scene_rules_digest.md for detailed style.",
            "Normal narration is plain text; italics only for short stage remarks.",
            "Action options are direct actions and do not start with 'Акира может'.",
            "Do not use quotation marks around dialogue or speech options.",
        ],
    }


rt.lean_recommended_files_for_context = recommended_files_with_scene_format
rt.build_scene_context_digest = build_scene_context_digest_with_style

base.recommended_files_for_context = recommended_files_with_scene_format
base.output_format_contract = strict_output_format_contract

ccp.recommended_files_for_context = recommended_files_with_scene_format

app.version = "0.3.63-clean-scene-format-v23"
