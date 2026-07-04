# Academy repo bugfix patch

Scope: fixed all diagnostic items except `state/knowledge_state.json`.

## Changed

1. Scheduled/delayed/mentioned characters no longer full-load as scene characters.
   - Patched `app/compact_context_patch.py`.
   - Patched `app/context_transport_runtime_patch.py`.
   - Patched `app/response_size_guard_runtime_patch.py`.

2. Removed hardcoded first-day full-load of `livia_cross`, `haru_foster`, `raiden_sterling`, `kir`.
   - `1198-08-15` now starts with Akira + Livia; Haru/Raiden/Kir load only when promoted to active/nearby/etc.

3. Fixed broken `app/main.py`.
   - It is now a safe compatibility shim importing `app.server:app`.

4. Removed active hidden-bond relationship data.
   - `state/relationships.json`: removed `hidden_bond`.
   - Replaced it with playable visible tension/interest/irritation only.
   - `characters/raiden/past.yaml`: removed explicit reincarnation/hidden-bond block.

5. Added state split aid without changing knowledge.
   - Added `state/start_state_template.json`.
   - Added `state/STATE_SPLIT_README.md`.
   - `state/knowledge_state.json` unchanged by hash.

6. Old schedule source wording cleaned where active.
   - Calendar module remains the source: runtime + index + current day file.
   - The `academy_schedule` response key may remain as a compatibility alias, but it returns active calendar snapshot, not old `state/academy_schedule.json`.

## Intentionally not changed

- `state/knowledge_state.json` — left untouched for later cleanup.
- 1206 v2/v3 rule migration — to be done as a second ZIP.

## File list

Changed files:
- `app/compact.py`
- `app/compact_context_patch.py`
- `app/context_cleanup_runtime_patch.py`
- `app/context_transport_runtime_patch.py`
- `app/lore_context_runtime_patch.py`
- `app/main.py`
- `app/response_size_guard_runtime_patch.py`
- `app/runtime_speed_patch.py`
- `canon_lore/core/world_background.yaml`
- `characters/akira/character.yaml`
- `characters/akira/main.yaml`
- `characters/akira/past.yaml`
- `characters/haru/past.yaml`
- `characters/kiara/past.yaml`
- `characters/kir/character.yaml`
- `characters/kir/past.yaml`
- `characters/livia/past.yaml`
- `characters/raiden/character.yaml`
- `characters/raiden/past.yaml`
- `gpt/locks/lore_usage_lock.md`
- `gpt/locks/runtime_scene_rules_digest.md`
- `state/future_locks_progress.json`
- `state/relationships.json`
- `state/story_lines_extensions.md`

Added files:
- `BUGFIX_PATCH_REPORT.md`
- `state/STATE_SPLIT_README.md`
- `state/start_state_template.json`

Removed files:
- none
