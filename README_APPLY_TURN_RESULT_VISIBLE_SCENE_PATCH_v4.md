# Apply Turn Result Visible Scene Patch v4

## Goal

Fix the runtime failure where GPT correctly renders a scene in render-only mode, but after `apply-turn-result` returns a tool JSON/status it replaces the visible gameplay scene with a technical summary.

This patch changes structure, not character locks.

## Changes

### 1. `apply-turn-result` now accepts visible scene text

`app/compact_context_patch.py` replaces the original POST route:

`/api/v1/sessions/{session_id}/apply-turn-result`

with operationId:

`applyTurnResult`

The request now accepts:

```json
{
  "data": {},
  "dry_run": false,
  "visible_scene_text": "full gameplay scene",
  "render_packet": {}
}
```

The response returns:

```json
{
  "status": "applied",
  "changed_files": [],
  "visible_scene_text": "full gameplay scene",
  "final_scene_text": "full gameplay scene",
  "final_response_mode": "return_final_scene_text_verbatim",
  "final_response_rule": "In gameplay mode, return final_scene_text/visible_scene_text verbatim..."
}
```

### 2. Prompt builder now enforces the runtime order

`app/prompt_builder.py` now states:

1. gather runtime data;
2. assemble `visible_scene_text`;
3. assemble state changes separately;
4. call `applyTurnResult` with both state changes and `visible_scene_text`;
5. after tool response, return `final_scene_text/visible_scene_text` verbatim.

### 3. Existing visible-scene lock updated

`gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md` now describes the structural pipeline and the new apply-turn-result contract.

### 4. Gameplay response gate updated

`gpt/locks/gameplay_response_gate.md` now refers to `visible_scene_text` and requires the final response after apply-turn-result to be the scene text, not status/changed_files.

### 5. Required files cleanup preserved

`app/prompt_builder.py` remains excluded from required_files. It is backend code and should not be loaded as lore/context.

## Why this is needed

Backend does not render scenes. The original `apply-turn-result` only applied state changes and returned a service status. GPT sometimes summarized that tool result instead of outputting the already-rendered scene.

Now the scene text is carried through the persistence tool response, giving GPT the exact final text to return.

## Deployment note

After deploying:

1. Re-import `/openapi.json` in the Custom GPT Actions.
2. Make sure the action name/operationId is `applyTurnResult`.
3. Test with render+apply, not render-only.
