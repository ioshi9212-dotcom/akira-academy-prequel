"""
Runtime header/footer hotfix v14.

Active import order:
1. calendar_context_runtime_patch, if present
2. lore_context_runtime_patch, if present
3. context_cleanup_runtime_patch

Server entry remains:
    app/server.py -> from app.context_transport_header_hotfix import app
"""

from __future__ import annotations

try:
    import app.calendar_context_runtime_patch as calendar_patch  # noqa: F401
except Exception:
    calendar_patch = None  # noqa: N816

try:
    import app.lore_context_runtime_patch as lore_patch  # noqa: F401
except Exception:
    lore_patch = None  # noqa: N816

import app.context_cleanup_runtime_patch as cleanup_patch  # noqa: F401

import app.context_transport_runtime_patch as rt
from app.context_cleanup_runtime_patch import app

app.version = "0.3.32-global-cleanup-header-v14"

SCENE_HEADER_FOOTER_LOCK = "gpt/locks/scene_header_footer_lock.md"
ACADEMY_START_CLEANUP_LOCK = "gpt/locks/academy_start_cleanup_lock.md"
CALENDAR_USAGE_LOCK = "gpt/locks/calendar_usage_lock.md"
LORE_USAGE_LOCK = "gpt/locks/lore_usage_lock.md"
CONTEXT_CLEANUP_LOCK = "gpt/locks/context_cleanup_lock.md"

for lock_path in [SCENE_HEADER_FOOTER_LOCK, ACADEMY_START_CLEANUP_LOCK, CALENDAR_USAGE_LOCK, LORE_USAGE_LOCK, CONTEXT_CLEANUP_LOCK]:
    if lock_path not in rt.MINIMAL_LOCK_FILES:
        rt.MINIMAL_LOCK_FILES.append(lock_path)

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
- If `uniform_worn=false`, do not write Academy uniform as worn clothing.
- If phone is inside baggage, do not write phone as carried/visible.

Required header example for 1198-08-15 start:

```txt
━━━━━━━━━━━━━━━━━━━━

🏛️ Академия Астрейн · 1198 г., 15 августа, пн  
🕒 позднее утро · 📍 Задний выход у корта  
🌦️ Погода: прохладно, влажный ветер  
⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах

✦ Спокойная · ссадина на щеке · волосы распущены  
🧥 Кроссовки · чёрные штаны карго · топ · бордовый худи  
◈ Багаж с личными вещами

━━━━━━━━━━━━━━━━━━━━
```

Fillers:
- line 1: `🏛️ Академия Астрейн · {year} г., {day_month}, {weekday}`
- line 2: `🕒 {time} · 📍 {location}`
- line 3: `🌦️ Погода: {short_weather}`
- line 4: `⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах`
- state: `✦ {emotional_state} · {physical_state} · {hair_state}`
- clothes: `🧥 {current_outfit}`
- carried: `◈ {visible_items}`

Required feel:
- Continue with living visual-novel prose after the header.
- Do not write the scene as a technical card/table/form.
- Do not over-explain technical state in visible prose.
- Do not answer with technical commentary after the scene.
- Keep the world moving: every scene needs a concrete hook, reaction, social pressure, small conflict, consequence, or transition.
- Use atmospheric details, but do not drown the player action.
- NPCs must act from loaded character files, relationship slice, calendar slice, lore slice and knowledge slice.
- Do not flatten characters into one trait.
"""
