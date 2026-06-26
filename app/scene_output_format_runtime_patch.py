"""
Scene output format runtime patch v25 restore-rich-scene.

Restores the selected old Academy visual-novel output format after speed mode.
Adds concise prose, player action boundary, immediate object continuity, visible-source handling,
canon identity boundary, witness/knowledge boundary and Academy social reaction reminders.
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
    strict = """
## Strict visible output format reminder

Use the old selected Academy scene style, not loose emoji-card style.

Required header:

🏛️ Академия Астрейн · 1198 г., 15 августа, пн
🕒 Позднее утро · 📍 Главный двор Академии
🌦️ Погода: ...
⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах

✦ ...
🧥 ...
◈ ...

━━━━━━━━━━━━━━━━━━━━

Dialogue:
**Имя/видимый дескриптор** — Реплика. (*короткая ремарка*)
Every spoken line in the scene body must start with a bold speaker label.
Bare scene-body dialogue like `— ...` without `**Говорящий**` is forbidden.
If Livia speaks, write `**Ливия** — ...`, never a naked line.

Immediate continuity:
- Read the latest visible scene facts before writing the next beat.
- Track where objects are and who holds them: ball, tray, cup, phone, documents, bag, door, chair, food.
- Bottom-block options are not facts until the player chooses them.
- If an object was moved/held in the latest visible beat, do not reset it to an old position unless someone visibly moves it.
- Do not resurrect old object positions from stale state, old setup, or old suggested options.

Unspoken Akira context:
- Akira's unspoken text is context for her tension, hesitation or intent, not a visible fact.
- Other characters and scene systems may react only to visible signs: pause, glance, guarded gesture, changed posture, silence, delayed answer or tension.
- Do not make the scene answer, solve, mirror or cancel an unspoken Akira worry unless there is a visible source in the scene.

Canon identity boundary:
- Random/unnamed/session NPCs and fixed canon characters are different layers.
- Do not rename an invented or unnamed NPC into an existing fixed character after that NPC has already been described.
- Do not attach a fixed character name to an NPC if appearance, role, course/year, energy, relationships, location, timing or behavior contradicts that character's card.
- A fixed named character may enter only if current roster, calendar/current day, scheduled/delayed state, explicit player action, or already played setup allows it.
- If unsure whether a person is a fixed character, keep them unnamed/background and do not use a canon name.

Visible name boundary:
- Engine-known id is not visible-known name.
- Do not reveal Haru/Raiden/Kir names before POV/Akira has a visible source.
- Use descriptors until named: `**Рыжий парень на корте**`; `**Очень высокий тёмноволосый курсант у края площадки**`.
- Never describe Raiden as white-haired/light-haired.

Witness and knowledge boundary:
- Characters know only what they saw, heard, were told, or can plausibly infer from visible signs.
- A delayed/absent/off-screen/not-yet-introduced character must not reference a previous scene as if they witnessed it.
- If a character arrives late, they know only what happened after arrival unless someone tells them on-screen or knowledge_state says they know.
- If they need to refer to someone from an unobserved scene, use uncertainty: "тот парень?", "тот рыжий?", "о ком вы?", "я что-то пропустил?".
- When the player brings in a delayed character, use their card from that point onward, but do not grant retroactive knowledge.

Scene prose:
- Write only what visibly happens now.
- Keep paragraphs concrete, but not empty.
- No long literary water, decorative philosophy, or bloated emotional explanation.
- Prefer action/reaction/dialogue over abstract atmosphere.
- Do not make a gameplay scene too short: give a living frame with movement, social pressure, Livia behavior if she is present, and at least one hook/consequence.
- A normal scene is not 2-3 tiny paragraphs unless the player explicitly asked for a short answer.

Player action boundary:
- The player's latest explicit action is the boundary of Akira's agency, not a reason to make the scene empty.
- Do not decide a new major choice for Akira beyond the last written action.
- Passage actions may reach the nearest meaningful beat: a reaction, obstacle, look, procedure, court pressure, Livia action, or hook.
- Do not complete implied next major location, full procedure, time skip, or plot beat unless written.

Academy social reactions:
- Students are status-conscious, strong, ambitious, jealous, curious, arrogant, competitive or reckless.
- Akira's sharp look must not make everyone silent, afraid, obedient or respectful.
- Use varied reactions: challenge, mockery, jealousy, curiosity, gossip, provocation, avoidance, indifference.
- Rumors/social media must be mixed and believable, not all kind or all hostile.
"""
    return str(base_digest).rstrip() + "\n\n" + strict.strip() + "\n"


def strict_output_format_contract() -> dict[str, Any]:
    return {
        "priority": "highest_for_scene_output",
        "selected_style": "academy_old_visual_novel_header_v2",
        "header_template": [
            "🏛️ Академия Астрейн · 1198 г., 15 августа, пн",
            "🕒 Позднее утро · 📍 Главный двор Академии",
            "🌦️ Погода: ...",
            "⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах",
            "",
            "✦ видимое состояние Акиры",
            "🧥 одежда/форма только из current_state",
            "◈ предметы при себе / рядом только из current_state / последнего видимого кадра",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ],
        "dialogue_format": "**Имя или видимый дескриптор** — Реплика. (*короткая ремарка*)",
        "bottom_blocks": [
            "━━━━━━━━━━━━━━━━━━━━",
            "✦ Что можно сделать",
            "Варианты ниже не считаются действием, пока игрок не выбрал.",
            "◈ ...",
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
            "Every spoken line in the scene body starts with a bold speaker name or visible descriptor; bare dash dialogue is forbidden.",
            "If Livia speaks in the body, the line starts with **Ливия** —.",
            "Use latest visible scene facts for immediate continuity before stale state or old suggested options.",
            "Bottom-block options are not facts until player chooses them.",
            "Track object holders and positions; do not teleport props.",
            "Akira unspoken text is context only, not a visible fact and not scene-system knowledge.",
            "Characters and scene systems may react only to visible signs, not to an unspoken Akira plan or worry.",
            "Do not make procedure, coincidence, NPC line or scene event conveniently answer Akira's unspoken context.",
            "Engine-known id is not visible-known name; do not reveal Haru/Raiden/Kir names before a visible source.",
            "Do not describe Raiden as white-haired/light-haired; he is dark-haired in Academy.",
            "Do not rename invented/unnamed NPCs into fixed canon characters after description.",
            "Do not attach a canon name to an NPC if card/calendar facts do not match.",
            "Delayed/absent/off-screen characters cannot know scenes they missed unless told or saved in knowledge_state.",
            "Write only what visibly happens now; no long literary water or decorative philosophy.",
            "The latest explicit player action is the hard scene boundary; do not move Akira beyond it.",
            "Do not complete implied next steps, new locations, procedures or time skips unless player wrote them.",
            "Academy students are not convenient fearful background; reactions must be varied and status-aware.",
            "Akira thoughts only in bottom block: Мысли Акиры.",
            "If output format, immediate continuity, visible-source rule, canon identity, witness boundary or action boundary is wrong, rewrite before sending.",
        ],
    }


rt.lean_recommended_files_for_context = recommended_files_with_scene_format
rt.build_scene_context_digest = build_scene_context_digest_with_style

base.recommended_files_for_context = recommended_files_with_scene_format
base.output_format_contract = strict_output_format_contract

ccp.recommended_files_for_context = recommended_files_with_scene_format

app.version = "0.3.65-rich-scene-dialogue-v4"
