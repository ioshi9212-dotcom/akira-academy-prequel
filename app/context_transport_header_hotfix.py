"""
Runtime header/footer hotfix v10.

Purpose:
- override the old visible header that showed `Рядом`;
- add short weather to the selected compact header;
- make the new scene_header_footer_lock part of required files;
- keep all v9 context transport behavior intact.

Install:
    app/server.py -> from app.context_transport_header_hotfix import app
"""

from __future__ import annotations

from typing import Any

import app.context_transport_runtime_patch as rt
from app.context_transport_runtime_patch import app
from app import compact as base
import app.compact_context_patch as ccp

app.version = "0.3.25-header-footer-hotfix-v10"

SCENE_HEADER_FOOTER_LOCK = "gpt/locks/scene_header_footer_lock.md"

# Ensure the new lock is loaded through required-files chunks.
if SCENE_HEADER_FOOTER_LOCK not in rt.MINIMAL_LOCK_FILES:
    rt.MINIMAL_LOCK_FILES.append(SCENE_HEADER_FOOTER_LOCK)

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — selected header/footer format

Use this instead of loading the full heavy scene_format.md in normal gameplay.

Visible scene format MUST use the selected compact header. This header is not a decorative form: state, clothes, carried items and weather must be reflected in the prose and object logic.

Scene header format:
- The scene must start exactly in this compact visual style.
- Do NOT show `Рядом`, `active`, `nearby`, observing characters, hidden NPCs, hidden lore, or future calendar events in the visible header.
- `active/nearby/observing/scheduled` may exist only in hidden engine state.
- Weather must be one short visible line.
- Location must be short and readable.
- Items must include only what Akira actually has on/with her in the current scene.

Required header example:

```txt
━━━━━━━━━━━━━━━━━━━━

🏛️ Академия Астрейн · 1198 г., 15 августа, пн  
🕒 15:30 · 📍 Главный двор Академии  
🌦️ Погода: прохладно, влажный ветер  
⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах

✦ Спокойная · ссадина на щеке · волосы распущены  
🧥 Бордовый пиджак Академии · чёрная рубашка · юбка-шорты · ботинки  
◈ Стакан с кофе · телефон · ключ-карта

━━━━━━━━━━━━━━━━━━━━
```

Fillers:
- line 1: `🏛️ Академия Астрейн · {year} г., {day_month}, {weekday}`
- line 2: `🕒 {time} · 📍 {location}`
- line 3: `🌦️ Погода: {short_weather}`
- line 4: `⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах`
- state: `✦ {emotional_state} · {physical_state} · {hair_state}`
- clothes: `🧥 {outfit}`
- carried: `◈ {carried_items}`

Required feel:
- Continue with living visual-novel prose after the header.
- Do not write the scene as a technical card/table/form.
- Do not over-explain technical state in visible prose.
- Do not answer with technical commentary after the scene.
- Keep the world moving: every scene needs a concrete hook, reaction, social pressure, small conflict, consequence, or transition.
- Use atmospheric details, but do not drown the player action.
- NPCs must act from loaded character files, relationship slice, calendar slice, and knowledge slice.
- Do not flatten characters into one trait: Livia is not only “loud”; Kir is not only “sarcastic”; Akira is not only “cold”.
- Use silence, glances, pauses, crowd pressure, and small physical reactions as scene tools.

Dialogue:
- Spoken line format: **Name/visible descriptor** — speech. (*short italic remark if needed*)
- Descriptions are separate italic paragraphs.
- Avoid long action text inside dialogue parentheses.
- Akira does not speak unless the player wrote her direct speech outside parentheses.
- Akira’s internal thoughts belong in the bottom “Мысли Акиры” block only.

Bottom block format:

```txt
━━━━━━━━━━━━━━━━━━━━

✦ Что можно сделать  
*Варианты ниже не считаются действием, пока игрок не выбрал.*

◈ ...
◈ ...
◈ ...

✦ Что Акира могла бы сказать

— “...”
— “...”
— “...”

✦ Мысли Акиры

— ...
— ...

━━━━━━━━━━━━━━━━━━━━
```

Bottom block quality:
- `Что можно сделать` actions must move the scene: change Akira's position, open contact, check a meaningful object/rule/route, choose tone, or move toward the next scene node.
- Do not write empty options like `осмотреться`, `подождать`, `пойти дальше`, `ответить`.
- `Что Акира могла бы сказать` lines must have weight, differ in tone/meaning, and sound like Akira.
- `Мысли Акиры` must be short reflections of Akira's voice, not author summary, not hidden lore, not a decision for the player.
- If there is no good thought, omit the thoughts section rather than writing filler.

Pacing:
- If the player asks to go/wait/eat/sleep, compress unimportant transit and land on the next meaningful beat.
- Do not ask for permission to continue when the player already gave an action.
- If a procedure is active (registration/scanner/check), do not auto-complete it unless the player action clearly does that.
"""


def medium_output_format_contract_hotfix() -> dict[str, Any]:
    try:
        original = rt._ORIGINAL_CCP_OUTPUT_FORMAT_CONTRACT()
    except Exception:
        try:
            original = rt._ORIGINAL_BASE_OUTPUT_FORMAT_CONTRACT()
        except Exception:
            original = {}
    if not isinstance(original, dict):
        original = {}

    rules = list(original.get("rules", []) or [])
    required_rules = [
        "Scene MUST start with the selected compact header with separator lines; do not use the old markdown visual-novel header.",
        "Visible header format: academy/date line, time/location line, short weather line, active-state rule line, Akira state, clothes, carried items.",
        "Do NOT show `Рядом`, active, nearby, hidden observers, hidden NPCs, hidden lore, or future calendar events in the visible header.",
        "Weather in the header must be short: one line after time/location.",
        "State/clothes/items/weather in header are not decoration; they must influence prose, actions, and object logic.",
        "Bottom block format: ✦ Что можно сделать / ✦ Что Акира могла бы сказать / ✦ Мысли Акиры, framed by separator lines.",
        "Action options must move the scene, not be empty filler.",
        "Akira possible lines must have weight, differ in tone/meaning, and sound like Akira.",
        "Akira thoughts must reflect Akira's voice; omit the thoughts section if there is no good thought.",
        "Do not output technical commentary after a gameplay scene.",
    ]
    for rule in reversed(required_rules):
        if rule not in rules:
            rules.insert(0, rule)

    original["rules"] = rules
    original["scene_header_template"] = {
        "required": True,
        "style": "selected_compact_header_with_weather",
        "example": [
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "🏛️ Академия Астрейн · 1198 г., 15 августа, пн  ",
            "🕒 15:30 · 📍 Главный двор Академии  ",
            "🌦️ Погода: прохладно, влажный ветер  ",
            "⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах",
            "",
            "✦ Спокойная · ссадина на щеке · волосы распущены  ",
            "🧥 Бордовый пиджак Академии · чёрная рубашка · юбка-шорты · ботинки  ",
            "◈ Стакан с кофе · телефон · ключ-карта",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ],
        "forbidden": [
            "old header starting with ### 🗓️",
            "visible `Рядом` line",
            "visible active/nearby/scheduled/observing lists",
            "plain raw field list without selected symbols",
            "large questionnaire-like header",
            "technical session/status/API text in gameplay",
        ],
    }
    original["bottom_blocks_template"] = {
        "required": True,
        "style": "selected_compact_bottom_options",
        "headers": [
            "✦ Что можно сделать",
            "✦ Что Акира могла бы сказать",
            "✦ Мысли Акиры",
        ],
        "quality_rules": [
            "actions move plot/contact/route/tone",
            "possible Akira lines have weight and character",
            "thoughts are Akira's short internal reflection, not author summary",
            "omit weak empty thought block",
        ],
    }
    return original


# Patch output contracts used by turn-contract endpoints.
rt.medium_output_format_contract = medium_output_format_contract_hotfix
base.output_format_contract = medium_output_format_contract_hotfix
ccp.output_format_contract = medium_output_format_contract_hotfix
