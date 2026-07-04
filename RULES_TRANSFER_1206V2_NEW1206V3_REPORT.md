# Rules transfer report — 1206_v2 + new_1206_v3 → Academy 1198

## Scope

This patch transfers rule/guard ideas only. It does not port 1206 plot, 1206 characters, East Sector content, or knowledge_state cleanup.

## Sources inspected

- `ioshi9212-dotcom/1206_v2`
- `ioshi9212-dotcom/new_1206_v3`

## What was transferred

### From 1206_v2

- Calendar is world pressure, not Akira action script.
- Use only current day during normal play; future days only for timeskip/audit.
- Player controls Akira's intentional actions, speech, route and choices.
- NPCs act from goals but must use visible/heard/known facts, time, distance and risk.
- Conditional arrivals require trigger, route, time and entry point.
- Sleep/time skip should jump to meaningful beat, not micro-routine.
- Hidden lore visibility: narration and NPC dialogue must not explain hidden facts without source.

### From new_1206_v3

- Build `current_frame` first.
- Split `full_character_ids` vs `reference_character_ids`.
- Do not fallback-insert Akira.
- Do not promote scheduled/delayed characters to full cards before beat.
- Character behavior must come from full cards, not short summary.
- Past/hidden files require explicit trigger.
- Relationship context is scene-local, not all Akira pairs.
- Add visible knowledge boundaries and forbidden_context.
- Add state update validation rules for memory/relationships/current scene.
- Unknown names must use stable visible descriptors until scene source reveals the name.

## Files added

- `state/context_loading/character_selection_rules_1198.json`
- `state/context_loading/scene_context_builder_rules_1198.json`
- `state/context_loading/past_trigger_rules_1198.json`
- `state/context_loading/forbidden_fallback_rules_1198.json`
- `state/update_contracts/turn_update_pipeline_1198.json`
- `state/update_contracts/character_memory_patch_rules_1198.json`
- `state/update_contracts/relationship_pair_patch_rules_1198.json`
- `state/update_contracts/scene_state_patch_rules_1198.json`
- `gpt/scene_output_contract_1198.json`

## Files updated

- `engine/calendar_day_runtime_rules.md`
- `gpt/locks/runtime_scene_rules_digest.md`
- `gpt/locks/state_update_payload_contract.md`
- `gpt/locks/lore_usage_lock.md`
- `canon_lore/hidden/hidden_lore_policy.yaml`
- `app/response_size_guard_runtime_patch.py`

## Not touched

- `state/knowledge_state.json` intentionally not changed.
- Character cards not rewritten.
- Calendar day content not rewritten.
- No 1206 story/canon transplanted into Academy.

## Expected effect

- Start scenes should not load Haru/Raiden/Kir as full characters before their beat.
- NPCs should stop knowing names/roles/hidden facts without source.
- Hidden Akira/Raiden lore should remain tension/subtext, not explanation.
- Scheduled characters should remain pending/reference-only until physically present or activated by beat.
- State updates should become more source-based and less magical.
