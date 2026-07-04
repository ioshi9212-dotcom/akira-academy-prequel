# Academy Prequel — chain/style/POV audit + fixes

## Checked

- API startup / OpenAPI / createSession / context / turn-contract / manifest / chunks.
- Required-files chain consistency.
- Scene header and footer rules.
- POV switch rules.
- Player action boundary / movement-chain interruption rules.
- Livia behavior rules.
- State update target rules after `knowledge_state` split.
- JSON/YAML validity and Python compilation.

## Found

1. `createSession` without body returned 422, while GPT instructions say to call `createSession` without placeholder body.
2. `/context` still served an old bulky compact context route because the new route did not remove the old same-path route.
3. `turn-contract` listed 43 required files, but manifest/chunks loaded a smaller old list. That broke the promised chain.
4. Several output contracts still used hard-coded header examples: `15 августа / Главный двор`.
5. Some rules still assumed only Akira POV and always used `Что Акира могла бы сказать / Мысли Акиры`.
6. Movement-chain rules existed, but were not explicit enough about: “go to exit / shower / room” + NPC interruption.
7. Livia’s card still contained restrictive wording that pushed her toward asking permission or avoiding speaking “for Akira”.
8. After state split, apply-turn-result still wrote relationship changes into global `state/relationships.json` instead of pair files.
9. Relationship score computation looked for metrics at top-level, while new pair files store them under `surface_dynamic`.
10. Director/style rules allowed compact prose, but did not explicitly forbid 3–5-word paragraph ladders.

## Fixed

1. `createSession` now accepts an empty body.
2. `/context` now uses size-guard context.
3. Required-files manifest/chunks now use the same required-file list as `turn-contract`.
4. Header contracts use current-state placeholders, not hard-coded location/date.
5. Bottom blocks are POV-aware: Akira labels only when POV is Akira; otherwise current POV name.
6. Low-stakes automatic POV lines are allowed; meaningful choice lines require player input.
7. Movement-chain rule is explicit: if an NPC interrupts a planned route/action chain with a meaningful hook, stop before completing the chain.
8. Livia is autonomous: she can answer, enter first, drag, flirt, interrupt, make mistakes. She does not ask permission for every step.
9. State updates now target `state/character_memory/<id>.json` and `state/relationship_pairs/<a>__<b>.json`, not global `knowledge_state.json` / `relationships.json`.
10. Relationship score computation now reads `surface_dynamic` from pair files and supports new ids like `akira__livia`, `akira__raiden`.
11. Dense prose rule added: no режиссура ladder with one tiny fragment per paragraph; scenes should be compact, readable, lightly ironic when appropriate.

## Smoke test after fix

- JSON/YAML validation: OK.
- Python compile: OK.
- `/health`: OK, version `0.3.70-academy-chain-style-state-fix`.
- `POST /api/v1/sessions` with no body: OK.
- `/context`: returns `size_guard_compact_context`.
- `/turn-contract`: returns 43 required files.
- `/required-files-manifest`: returns the same 43 required files.
- All required files appear in chunks; missing files: 0.
- Start frame does not load global `state/knowledge_state.json` or global `state/relationships.json`.
- Start frame does not full-load Haru/Raiden/Kir.
- Test relationship update writes to `state/relationship_pairs/akira__livia.json`.
- Test memory update writes to `state/character_memory/livia.json`.
- Global `state/relationships.json` remains disabled legacy stub.

## Still intentionally not done

- Permanent `characters/<id>/knowledge.yaml` split is not done; user said to do it later.
- Old root cleanup reports remain in ZIP. They are not runtime-loaded, but can be removed in a later cosmetic cleanup.
- Some legacy helper functions remain for backward compatibility, but active routes now use split state / pair state.

## Changed files

- `app/compact.py`
- `app/context_transport_header_hotfix.py`
- `app/context_transport_runtime_patch.py`
- `app/prompt_builder.py`
- `app/response_size_guard_runtime_patch.py`
- `app/scene_output_format_runtime_patch.py`
- `app/state_write_runtime_patch.py`
- `characters/livia/character.yaml`
- `gpt/custom_gpt_instructions_ULTRA_COMPACT_COMPACT.md`
- `gpt/locks/player_input_anchor_lock.md`
- `gpt/locks/runtime_scene_rules_digest.md`
- `gpt/pov_switch_mode.md`
- `gpt/scene_format.md`
- `gpt/scene_output_contract_1198.json`
- `state/update_contracts/relationship_pair_patch_rules_1198.json`
- `state/update_contracts/turn_update_pipeline_1198.json`
- `ACADEMY_CHAIN_STYLE_AUDIT_FIX_REPORT.md`
