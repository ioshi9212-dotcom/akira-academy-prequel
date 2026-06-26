# Academy restore patch v6 — based on the zip that worked

Source baseline: uploaded `akira-academy-prequel-main (15)(3).zip`, because this archive behaved correctly on start and did not dress Akira in the Academy uniform.

## Principle

This patch does NOT continue the v5 recovery line. It restores the runtime/style files from the working archive and only applies the small fixes we actually need:

1. remove the misleading uniform example from header examples;
2. restore `outfit_state_lock.md` as an active required rule through the old response-size guard;
3. keep rich old visual-novel scene format and old scene output runtime;
4. add the non-Akira POV fix: Akira is an active NPC in Haru/Livia/Raiden POV;
5. add loaded-id vs visible-name rule without changing character cards.

## Why the working zip did not put the uniform on Akira

The working zip still had a bad sample in two format examples, but it also loaded stronger state/outfit controls:

- `state/current_state.json`: `current_outfit = кроссовки, чёрные штаны карго, топ, бордовый худи`, `uniform_worn = false`;
- `state/inventory_state.json`: confirms the same;
- `gpt/locks/outfit_state_lock.md`: explicitly says received uniform is not worn uniform;
- `app/response_size_guard_runtime_patch.py`: included `gpt/locks/outfit_state_lock.md` in `BASE_RULE_FILES`.

v5 disabled or weakened that exact protection path. v6 restores it.

## Files included

- `app/context_transport_runtime_patch.py`
- `app/scene_output_format_runtime_patch.py`
- `app/response_size_guard_runtime_patch.py`
- `app/prompt_builder.py`
- `app/pov_switch_runtime_patch.py`
- `gpt/scene_format.md`
- `gpt/locks/runtime_scene_rules_digest.md`
- `gpt/locks/outfit_state_lock.md`
- `gpt/pov_switch_mode.md`

## Grep verification inside v6 patch

Forbidden header facts removed from patched format/runtime examples:

- `Бордовый пиджак Академии` — absent in patched `gpt/scene_format.md` and `app/context_transport_runtime_patch.py` examples;
- `юбка-шорты` — absent in patched `gpt/scene_format.md` and `app/context_transport_runtime_patch.py` examples;
- `высокие ботинки` — absent in patched `gpt/scene_format.md` and `app/context_transport_runtime_patch.py` examples;
- `Дорожная сумка с личными вещами` — absent in patched `gpt/scene_format.md` and `app/context_transport_runtime_patch.py` examples.

Note: `outfit_state_lock.md` still describes Academy uniform as lore/rules. That is intentional. The lock is there to prevent treating received uniform as worn clothing.
