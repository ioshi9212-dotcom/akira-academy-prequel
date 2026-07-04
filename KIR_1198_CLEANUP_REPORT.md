# KIR 1198 CLEANUP REPORT

Cleaned `characters/kir/` to exactly three active YAML files:

- `main.yaml` — анкета, внешность, энергия, ссылки.
- `character.yaml` — характер, речь, поведение, отношения, запреты.
- `past.yaml` — прошлое, стартовые знания, hidden lore границы.

Removed/merged old extra files:

- `behavior.yaml` -> merged into `character.yaml`
- `character_append.yaml` -> merged into `character.yaml` / `past.yaml`

Validation: all three Kir YAML files parse successfully.
