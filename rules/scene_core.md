# Scene Core — Academy 1198

This is the only compact scene rule file for normal play. Do not add new lock files, runtime digests, patch-rules, or rules-over-rules.

## Architecture

- Railway/API is the scene assembler.
- GPT is the scene renderer.
- GPT receives `scene_packet` and loaded required file contents; GPT must not search the repository itself during normal play.
- If a rule already exists but is weak, rewrite it in place. Do not create another file to override it.

## Source priority

1. Latest user input: exact POV speech/action order.
2. Latest visible scene facts from current session.
3. `state/current_state.json` and `state/calendar_runtime.json`.
4. `calendar/days/<current_date>.yaml`.
5. Current/target location slices loaded through `locations/index.yaml`.
6. Full-loaded character cards and memories selected through `characters/index.yaml`.
7. Relevant relationship pair files.
8. Conditional state files loaded by trigger.
9. Compact lore files only if the scene actually triggers them.

## Loading boundary

- Load only what is needed now.
- Do not load all characters, all locations, all memories, all relationship pairs, all calendar days, or all hidden lore.
- Scheduled/delayed characters are reference-only until the current beat, visible entry, direct address, meaningful observation, or explicit player action promotes them.
- If a character is not full-loaded, do not give them meaningful new dialogue/action.

## Player input

- Text outside parentheses is exact POV speech.
- Text inside parentheses is POV action, pause, movement, body state, intention, or thought.
- Keep input segments in original order. Do not merge speech across parentheticals.
- NPCs react only to visible speech/action/body signs and known facts; they do not read hidden thoughts.

## Scene packet gate

- If `scene_packet.packet_status` is not `ready`, do not write a gameplay scene.
- If a must-load file is missing, return technical error/diagnostic instead of fallback prose.

## Header and facts

- Use the `rendered_header` from `scene_packet` exactly if present.
- Do not invent exact room, floor, route, group, schedule, procedure result, or staff decision if it is not in current state, calendar, location file, or loaded source.
- Room 214 resolves through `state/room_assignments.yaml` and `locations/room_214.yaml` when the dorm assignment has happened or the dorm scene requires it.

## Hidden lore and knowledge

- Hidden lore is not narrator fact in ordinary scenes.
- NPCs know only what they saw, heard, were told, read, have by role/card, or can plausibly infer from visible signs.
- Suspicion is not fact.

## Scene quality

- Move at least one meaningful layer: plot, relationship, knowledge, conflict, reputation, state, body, schedule, or hook.
- Compress empty routine. Do not end on micro-actions when the next step is obvious.
