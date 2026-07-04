# Character memory state — Academy 1198

Runtime memory is split per character. Load `state/character_memory/<id>.json` only when that character is POV, physically present, speaking, directly addressed, observed, or required by current scene_goal/current_frame.

Static permanent knowledge is not solved in this patch; later it should move to `characters/<id>/knowledge.yaml`.

Do not load `state/legacy/knowledge_state_legacy_archive.json` in normal scene generation.
