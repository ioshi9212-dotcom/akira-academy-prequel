# World Integrity Control

This file is a compact continuity guard for normal gameplay and POV scenes.

## Purpose

Before rendering a scene, verify that the scene does not contradict the already played world.

Check:
- current date and time;
- current location;
- who is active, nearby, mentioned, scheduled or delayed;
- who has already met whom;
- who knows which name/fact;
- which calendar beat was already played;
- visible injuries/items/outfit/state;
- relationship memory;
- recent scene_history when available;
- story_lines turn counter and last audit note.

## Rules

- Do not treat a repeated meeting as a first meeting.
- If characters saw each other but did not exchange names, write: seen before, not formally introduced.
- If the exact name was not heard, do not let Akira or an NPC use it as known fact.
- If current_state says an item/clothing/injury exists, respect it until state changes.
- If current_state says an item is gone/used/empty, do not bring it back without a state reason.
- If calendar_runtime has a current beat, use it as a hook, not as a rigid script.
- If calendar_runtime is stale, do not force an old beat if the played scene already moved beyond it; save a correction through state.
- If scene_history contradicts current state, prefer played scene_history and write a soft correction through apply-turn-result.
- If story_lines contains an audit/compaction note, use it as memory of played facts.

## POV scenes

POV scenes obey the same integrity rules.

If controlled character is not Akira:
- header, thoughts and suggested lines belong to the POV character;
- relationship changes apply to the POV character and whoever is in the scene;
- Akira gains knowledge only if she has a real source;
- time still moves normally;
- consequences can affect Akira later.

## State write expectation

If a continuity correction is needed, save it in normal state files:
- state/current_state.json
- state/story_lines.json
- state/relationships.json
- state/knowledge_state.json
- state/reputation_state.json
- state/rumors_state.json
- state/calendar_runtime.json
- state/scene_history.json

Do not create one-off continuity files.
