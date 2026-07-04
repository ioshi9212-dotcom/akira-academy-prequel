# State knowledge split report — Academy 1198

## Done

- Replaced global runtime `state/knowledge_state.json` with a safe migration stub.
- Archived original global knowledge file at `state/legacy/knowledge_state_legacy_archive.json`.
- Created per-character runtime memory files in `state/character_memory/`.
- Split global relationships into per-pair files in `state/relationship_pairs/`.
- Archived original global relationships at `state/legacy/relationships_legacy_archive.json`.
- Moved Kai/Asher heavy school material into trigger-only `state/knowledge_threads/kai_asher_school_thread.json`.
- Moved hidden/author-only leftovers into `state/knowledge_threads/hidden_author_only_archive.json`.
- Patched runtime required-files logic to include only selected `character_memory` and relevant `relationship_pairs`.
- Permanent `characters/<id>/knowledge.yaml` files were not created/edited in this patch.

## Character memory files (13)

- `state/character_memory/akira.json`
- `state/character_memory/asher_lane.json`
- `state/character_memory/haru.json`
- `state/character_memory/jun_carter.json`
- `state/character_memory/kael_north.json`
- `state/character_memory/kai_renwick.json`
- `state/character_memory/kiara.json`
- `state/character_memory/kir.json`
- `state/character_memory/livia.json`
- `state/character_memory/marten_weiss.json`
- `state/character_memory/raiden.json`
- `state/character_memory/ray_carter.json`
- `state/character_memory/samuel_sterling.json`

## Relationship pair files (18)

- `state/relationship_pairs/akira__asher_lane.json`
- `state/relationship_pairs/akira__haru.json`
- `state/relationship_pairs/akira__kai_renwick.json`
- `state/relationship_pairs/akira__kir.json`
- `state/relationship_pairs/akira__livia.json`
- `state/relationship_pairs/akira__raiden.json`
- `state/relationship_pairs/asher_lane__kai_renwick.json`
- `state/relationship_pairs/haru__asher_lane.json`
- `state/relationship_pairs/haru__kai_renwick.json`
- `state/relationship_pairs/livia__asher_lane.json`
- `state/relationship_pairs/livia__haru.json`
- `state/relationship_pairs/livia__kai_renwick.json`
- `state/relationship_pairs/livia__kir.json`
- `state/relationship_pairs/livia__raiden.json`
- `state/relationship_pairs/raiden__asher_lane.json`
- `state/relationship_pairs/raiden__haru.json`
- `state/relationship_pairs/raiden__kai_renwick.json`
- `state/relationship_pairs/raiden__samuel_sterling.json`

## Runtime rule

Normal scenes must not load a single global knowledge file. Load only:

1. POV character memory;
2. physically present/active character memories;
3. speaking/addressed/observed character memories;
4. relationship pair files where both sides are scene-relevant;
5. trigger-only knowledge threads only when current_frame/scene_goal explicitly requires them.
