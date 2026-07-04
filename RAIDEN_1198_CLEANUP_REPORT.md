# RAIDEN 1198 cleanup report

Cleaned `characters/raiden/` into 3 active files:

- `main.yaml` — анкета, внешность, энергия, базовые связи.
- `character.yaml` — характер, речь, поведение, отношения, запреты.
- `past.yaml` — прошлое, hidden lore, знания на старте, future locks.

Removed/merged:

- `behavior.yaml` merged into `character.yaml`.

Notes:

- Fixed broken YAML structure from old `character.yaml` around `academy_context.important_nearby.rule`.
- Preserved key rules: Райден не знает hidden lore; связь с Акирой не готовая любовь; взрослый Райден 1206 не переносится в Академию 1198.
