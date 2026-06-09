# Academy Prequel Required Files Chunk + Player Anchor v2

Purpose:
- reduce required-files chunk default size to prevent ResponseTooLargeError in Custom GPT Actions;
- force `gpt/locks/player_input_anchor_lock.md` into required_files;
- include `state/current_state.json` in required_files for tests and fallback grounding;
- include `app/prompt_builder.py` in required_files as fallback visibility for the render brief rules;
- set short, stable operation_id values for Custom GPT Actions:
  - `getSessionTurnContract`
  - `getRequiredFilesManifest`
  - `getRequiredFilesChunk`
  - `getRequiredFilesBundle`

Changed files:
- `app/compact_context_patch.py`
- `app/prompt_builder.py`
- `gpt/scene_format.md`
- `gpt/locks/gameplay_response_gate.md`
- `gpt/locks/player_input_anchor_lock.md`

Important default changes:
```py
DEFAULT_CHUNK_CHARS = 12000
DEFAULT_CHUNK_ITEMS = 1
```

Expected test after deploy + Actions schema refresh:
- manifest works;
- chunks_total becomes larger than before;
- chunk 0 should not hit ResponseTooLargeError;
- `gpt/locks/player_input_anchor_lock.md` appears in loaded_files.path;
- `state/current_state.json` appears in loaded_files.path;
- `app/prompt_builder.py` appears in loaded_files.path;
- prompt_preview should be available through `getSessionTurnContract` after the Actions schema refresh.

After deployment:
1. open Custom GPT Actions;
2. reimport schema from `/openapi.json`;
3. save GPT;
4. start a new chat and run the technical test again.
