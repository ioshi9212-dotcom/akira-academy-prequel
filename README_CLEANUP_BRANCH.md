# Cleanup branch scope

This branch is intentionally separate from `main` so the scene runtime clean-up can be reviewed or discarded safely.

## Goal

Undo the harmful parts of recent patch layering without removing the useful mechanics.

## Kept

- `response_size_guard_runtime_patch.py` remains, but only as a compact transport layer.
- `TurnContractWithPromptPreview` OpenAPI schema remains for smoke tests.
- `state/akira_progress_state.json` remains for numeric physical/energy levels.
- `state/relationship_score_panel.json` remains for relationship score totals.
- Core scene style remains in `gpt/scene_format.md` and `gpt/locks/runtime_scene_rules_digest.md`.

## Disabled / removed from required_files

The extra style lock files should not be active scene inputs anymore:

- `gpt/locks/scene_density_choice_rules.md`
- `gpt/locks/progress_panel_rules.md`
- `gpt/locks/outfit_state_lock.md`

The branch filters them out in `response_size_guard_runtime_patch.py`.

## Why

Those extra locks duplicated rules already present in the main digest and made the model write dry checklist-style scenes, overuse italics, and confuse upper header state with bottom numeric levels.

## Correct final behavior

- Header `✦` = short visible/current Akira condition.
- Bottom `✦ Уровни` = numeric physical/energy totals.
- Bottom `✦ Отношения` = current total relationship scores.
- Action choices use direct actions, not `Акира может...`.
- Normal narration stays plain text; italics are only short stage remarks.
