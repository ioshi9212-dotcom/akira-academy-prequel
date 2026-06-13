"""
Runtime header/footer hotfix v13.

Purpose:
- keep compact header/footer behavior;
- optionally activate calendar module if present;
- activate canon_lore module;
- load scene_header_footer_lock, academy_start_cleanup_lock, calendar_usage_lock, lore_usage_lock.
"""

from __future__ import annotations

# Calendar module is optional here: it exists if the calendar patch was applied.
try:
    import app.calendar_context_runtime_patch as calendar_patch  # noqa: F401
except Exception:
    calendar_patch = None  # noqa: N816

# Lore module is the new active canon-lore source.
import app.lore_context_runtime_patch as lore_patch  # noqa: F401

import app.context_transport_runtime_patch as rt
from app.lore_context_runtime_patch import app

app.version = "0.3.30-lore-header-hotfix-v13"

SCENE_HEADER_FOOTER_LOCK = "gpt/locks/scene_header_footer_lock.md"
ACADEMY_START_CLEANUP_LOCK = "gpt/locks/academy_start_cleanup_lock.md"
CALENDAR_USAGE_LOCK = "gpt/locks/calendar_usage_lock.md"
LORE_USAGE_LOCK = "gpt/locks/lore_usage_lock.md"

for lock_path in [SCENE_HEADER_FOOTER_LOCK, ACADEMY_START_CLEANUP_LOCK, CALENDAR_USAGE_LOCK, LORE_USAGE_LOCK]:
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
