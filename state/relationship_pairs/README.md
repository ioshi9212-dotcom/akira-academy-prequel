# Relationship pair state — Academy 1198

Relationships are split into pair files: `state/relationship_pairs/<a>__<b>.json`.

Load a pair only if both characters are active/present, one directly interacts with or talks about the other with scene relevance, or scene_goal/current_frame requires that pair.

Do not load global `state/relationships.json` in normal scene generation. It is now a migration stub; the original is archived under `state/legacy/relationships_legacy_archive.json`.
