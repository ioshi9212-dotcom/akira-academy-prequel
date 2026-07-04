# LIVIA 1198 CLEANUP REPORT

Done:
- `characters/livia/main.yaml` rewritten as compact questionnaire/main card.
- `characters/livia/character.yaml` rewritten as dry behavior/personality/relationship rules.
- `characters/livia/past.yaml` rewritten as dry past/start knowledge/hidden-lore boundaries.
- `characters/livia/behavior.yaml` removed and merged into `character.yaml`.
- Broken YAML fragments in the old `character.yaml` and `behavior.yaml` removed.
- All three active Livia YAML files validate with `yaml.safe_load`.

Active files in `characters/livia/`:
- `main.yaml`
- `character.yaml`
- `past.yaml`
