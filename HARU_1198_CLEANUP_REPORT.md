# HARU 1198 cleanup

Cleaned `characters/haru` into 3 active YAML files:

- `main.yaml` — анкета, внешность, энергия, связи.
- `character.yaml` — характер, речь, поведение, отношения, запреты.
- `past.yaml` — прошлое, стартовые знания, границы hidden lore.

Removed duplication and compressed literary descriptions into API-oriented rules.
All 3 YAML files validate with PyYAML.
