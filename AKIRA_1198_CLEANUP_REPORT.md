# Akira Academy 1198 cleanup

Changed folder: characters/akira/

Kept active files:
- main.yaml — анкета
- character.yaml — характер/поведение/правила сцен
- past.yaml — прошлое/знания/скрытые факты

Removed from active Akira folder:
- behavior.yaml — merged into character.yaml
- character_append.yaml — archived duplicate, removed

Validation:
- main.yaml parses as valid YAML
- character.yaml parses as valid YAML
- past.yaml parses as valid YAML

Notes:
- Main/character had broken YAML indentation and glued strings; fixed.
- Repeated blocks were merged.
- Literary phrasing reduced.
- Hidden lore kept locked behind scene-based reveal rules.
