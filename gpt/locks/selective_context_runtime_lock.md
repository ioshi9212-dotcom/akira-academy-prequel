# Lock: selective context runtime

Normal gameplay must use selective context, not full bundle.

## Default gameplay context
Load only:
- runtime/scene_context_digest.md;
- active/nearby/speaking/addressed/looked_at/mentioned/scheduled character files;
- minimal gameplay/output/state-write locks;
- scene-relevant relationship/story/knowledge slices from the digest.

Do not request every project file for normal gameplay.

## Full context mode
Full required-files bundle is allowed only for explicit technical diagnostics or when current_state has:
- context_mode: full / diagnostic / debug
- force_full_context: true
- debug_full_required_files: true

## Quality rule
Selective context is not permission to flatten characters.
If a character is active in the scene, their character.yaml must be loaded unless missing.
Relationships used in the scene must be from the relationship slice or exact state JSON.
