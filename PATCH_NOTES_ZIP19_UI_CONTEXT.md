# ZIP 19 UI/context cleanup

Changed files:

- `app/prompt_builder.py`
  - Increased `MAX_PROMPT_PREVIEW_CHARS` from 8000 to 9000.
  - Kept rules in logical processing order.
  - Strengthened Bottom UI contract: `◈` actions, `—` speech/thoughts, no speech verbs in actions, numeric levels, relationship format.

- `app/main.py`
  - Removed misleading comment saying chunks are only for technical/diagnostic mode.

- `openapi.yaml`
  - Marked required file manifest/chunk endpoints as gameplay context loading, not diagnostics-only.

- `calendar/days/1198-08-16.yaml`
  - Replaced `ответить на замечание` with `отреагировать на замечание`.

- `characters/kael_north/character.yaml`
- `characters/kael_north/character_append.yaml`
- `characters/kir/behavior.yaml`
- `characters/kir/character_append.yaml`
  - Removed `examples` blocks to avoid copyable phrasing in gameplay.

- `README.md`
  - Added maintenance rule: all rules are important, blocks follow logical order, do not move rules up as a priority hack.
  - Added Bottom UI validation reminder.

No delete-only files are required for this patch.
