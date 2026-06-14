"""
Runtime header/footer hotfix v16.

Active import order:
1. calendar_context_runtime_patch
2. lore_context_runtime_patch
3. context_cleanup_runtime_patch
4. runtime_speed_patch
5. scene_output_format_runtime_patch
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

try:
    import app.context_cleanup_runtime_patch as cleanup_patch  # noqa: F401
except Exception:
    cleanup_patch = None  # noqa: N816

import app.runtime_speed_patch as speed_patch  # noqa: F401

import app.context_transport_runtime_patch as rt
from app.runtime_speed_patch import app

rt.MINIMAL_LOCK_FILES = ["gpt/locks/runtime_scene_rules_digest.md"]

try:
    import app.scene_output_format_runtime_patch as scene_format_patch  # noqa: F401
except Exception:
    scene_format_patch = None  # noqa: N816

app.version = "0.3.36-scene-format-restore-v16"

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — strict Academy scene format

Use the selected old Academy visual-novel header/footer format.

Header:
🏛️ Академия Астрейн · 1198 г., 15 августа, пн
🕒 Позднее утро · 📍 Главный двор Академии
🌦️ Погода: ...
⚙️ Активное состояние сцены: учитывать в тексте, действиях и предметах

✦ ...
🧥 ...
◈ ...

━━━━━━━━━━━━━━━━━━━━

Rules:
- Do not use the loose header format "🗓️ date / 📍 location / 👤 Akira / 🎒 nearby".
- Dialogue line format: **Имя/видимый дескриптор** — Реплика. (*короткая ремарка*)
- Bottom blocks use ✦ headings, not 🎯/💬/🧠.
- Suggested Akira lines must be poisonous, dry, sharp and character-true.
"""
