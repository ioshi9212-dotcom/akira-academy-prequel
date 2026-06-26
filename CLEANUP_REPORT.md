# Akira Academy Prequel cleanup report

Generated from uploaded archive: `akira-academy-prequel-main (15).zip`.

## Goal

Reduce prompt/rule layering without removing gameplay mechanics.

## Main changes

- `gpt/scene_format.md` rewritten as the single visible scene format source.
- `gpt/locks/runtime_scene_rules_digest.md` kept as the single gameplay rules digest.
- `gpt/locks/npc_living_scene_rules.md` kept for invented/session NPC memory.
- `gpt/locks/state_update_payload_contract.md` kept because `app/state_write_runtime_patch.py` uses it.
- `app/scene_output_format_runtime_patch.py` reduced to a minimal non-invasive reminder.
- `app/response_size_guard_runtime_patch.py` changed to transport-only size guard with numeric levels and computed relationship panel in the compact contract.
- `app/context_transport_runtime_patch.py` cleaned of the old bad examples: no `юбка-шорты` hardcoded outfit, no dialogue quotes, no rule that all descriptions must be italic.
- `app/context_transport_header_hotfix.py` version marked as `0.3.63-clean-zip-v1`.

## Removed redundant lock files

- gpt/locks/academy_start_cleanup_lock.md
- gpt/locks/acquaintance_and_named_npc_state_lock.md
- gpt/locks/apply_state_after_turn_lock.md
- gpt/locks/calendar_usage_lock.md
- gpt/locks/character_presence_rotation_lock.md
- gpt/locks/context_cleanup_lock.md
- gpt/locks/context_recovery_lock.md
- gpt/locks/dialogue_format_strict_lock.md
- gpt/locks/gameplay_response_gate.md
- gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md
- gpt/locks/lore_usage_lock.md
- gpt/locks/no_empty_scenes_lock.md
- gpt/locks/outfit_state_lock.md
- gpt/locks/play_mode_silence_lock.md
- gpt/locks/player_input_anchor_lock.md
- gpt/locks/progress_panel_rules.md
- gpt/locks/scene_density_choice_rules.md
- gpt/locks/scene_header_footer_lock.md
- gpt/locks/selective_context_runtime_lock.md
- gpt/locks/story_lines_memory_lock.md

## Removed non-runtime clutter

- patch_notes
- patches
- README_ADD_FILES.md
- README_CHARACTER_CANON_INFO_PATCH_v1.md
- README_CLEAN_CONTEXT_PATCH_v1.md
- README_CONNECT_FILES_v1.md
- academy_schedule_august16_note.md
- gpt/scene_header_footer_format_patch_v1.md
- gpt/scene_header_variants.md
- validation/ultra_compact_contract_checklist.md
- app/outfit_source_runtime_patch.py

## Runtime rules after cleanup

Active rule sources should be:

- `runtime/scene_context_digest.md` (virtual generated digest)
- `gpt/scene_format.md`
- `gpt/locks/runtime_scene_rules_digest.md`
- `gpt/locks/npc_living_scene_rules.md`
- `gpt/locks/state_update_payload_contract.md`

Progress and relationships stay in state files:

- `state/akira_progress_state.json`
- `state/relationship_score_panel.json`
- `state/relationships.json`

## Expected scene behavior

- Header `✦` = short visible/current Akira condition.
- Bottom `✦ Уровни` = numeric physical/energy totals.
- Bottom `✦ Отношения` = current total relationship scores.
- Dialogue has no quotation marks.
- Background NPCs speak through visible stable descriptors.
- Action options are direct actions, not `Акира может...`.
- Outfit comes from `current_state` / `inventory_state` / latest visible scene.
