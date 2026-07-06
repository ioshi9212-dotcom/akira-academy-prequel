# Runtime Scene Rules Digest — Academy 1198 compact v7

This file is the compact always-loaded rule pack for normal gameplay. It replaces the old stack of heavy locks in `required_files`.

## Required loading tiers

- Use `getSessionTurnContract` first.
- `required_files` / manifest / chunks contain only `must_load_now`.
- Load every required chunk before writing gameplay.
- `buildScenePacket` gives the current rendered header, ordered player input segments, compact UI panel rules and render guards.
- `load_if_needed_files` are fetched only by explicit trigger: past, hidden-lore audit, style audit, secondary relationship, full calendar audit.
- `reference_only_files` are not gameplay context.
- If `scene_packet.packet_status` is not `ready`, do not write a gameplay scene.

## Source priority

1. Latest direct user instruction.
2. Latest visible scene facts / scene_history.
3. API current_frame/current_state for the current session.
4. Current game-date calendar file: `calendar/days/<current_date>.yaml`.
5. Required files loaded for this turn.
6. Character cards + character_memory for full scene characters.
7. Scene relationship_pairs.
8. Compact canon/lore policy.
9. Chat memory only as latest player input, not truth source.

## Current game-date calendar rule

- The calendar file for `current_date` is the authority for today's beats, procedures, room/dorm assignment source, schedule pressure, character entrances and event order.
- Do not use future day files unless the scene time-skips to that date or the user asks for calendar diagnostics.
- Do not invent exact room, floor, group, course, schedule, procedure result, route or staff decision if it is not in current_state, current_frame, current calendar day or a loaded source.
- If a generated scene contradicts current_state/current-day calendar, treat the contradiction as unconfirmed scene drift and correct by the nearest natural in-story clarification.
- `day_beats` are constraints and hooks, not fixed prose. They guide what can happen now and what is still pending.

## Full character loading and presence

A character must be treated as full and have their card/memory available when any of these is true:

- they are the POV;
- they are physically present, nearby, entering, leaving, speaking, observing, addressed, looked at, followed, blocked by, or directly interacted with;
- the current calendar beat activates them now;
- they remained visibly in the latest played scene and no state/scene fact says they left;
- the scene will give them a meaningful line, choice pressure, physical action, relationship shift, knowledge update, or consequence.

Scheduled/delayed/reference characters stay reference only until their beat is reached or they enter the visible scene. A character being important later is not enough to full-load them now.

If a named character is not full-loaded, do not give them new meaningful dialogue/action. Use background presence, a visible descriptor, or wait until the state/calendar promotes them.

After a scene where a character enters, leaves, speaks, witnesses something or remains nearby, `applyTurnResult` must update current_state/scene_history/character_memory enough for the next turn to select them correctly.

## POV and player agency

- Default POV is Akira, but any contract/user-selected POV is valid.
- Text outside parentheses is exact POV speech.
- Text inside parentheses is POV action/intention/body state/thought/movement/pause.
- Do not choose major POV decisions: consent/refusal, trust, route, attack, reveal, access, public stance.
- Low-stakes automatic POV lines are allowed when they do not decide anything important.
- If an NPC meaningfully challenges/questions/provokes POV, stop at a choice point.
- In non-Akira POV, Akira is an NPC if present: she can act and speak, but her hidden thoughts stay hidden.

## Player input segment order — hard rule

- Use `scene_packet.player_input.segments` when present.
- Render the segments in exact original order.
- A speech segment stays POV speech.
- A parenthetical segment stays action/thought/body beat/pause, not dialogue.
- Never merge two speech segments across a parenthetical.
- Never move a later speech segment before an earlier parenthetical.
- Parentheticals create a pause:
  - short pause: gesture/body beat, usually no big interruption;
  - medium pause: NPC/environment may react briefly;
  - long pause: NPC may speak or act if natural, but must not steal player choice.

Example:

```txt
Вы за кого переживаете? (поправить сумку на плече) За меня или академию?
```

must render as:

1. POV speech: `Вы за кого переживаете?`
2. POV action/pause: `поправить сумку на плече`
3. POV speech: `За меня или академию?`

Not as one merged line.

## Movement chains and interruption

- A chain like “say X (go to the exit)” means intent/progress, not guaranteed completion.
- If an NPC line, obstacle, question, risk, new information or social pressure appears on the way, stop before completing the chain.
- Do not assume POV stayed silent and continued after a meaningful hook.
- If nothing meaningful happens, compress routine movement to the nearest meaningful beat.
- This applies to exits, showers, corridors, stairs, rooms, registration, training, meals and time skips.

## Scene style

- Gameplay answer is scene only: no API/debug/status text.
- Use `scene_packet.current_frame.rendered_header` exactly as the first visible block.
- Do not use old loose headers such as `📅 Дата:` or `🎒 При себе:`.
- Dialogue: `**Name/descriptor** — line.` No quotation marks.
- If POV does not know a name, use visible descriptor until introduction/source.
- Write dense readable paragraphs. Do not split narration into 3–5 word fragments.
- Light dry irony/sarcasm is allowed only when tied to visible action.
- Scene must move at least one layer: plot, relationship, knowledge, conflict, reputation, state, energy, schedule, thread or hook.
- Do not play empty routine step by step; compress to meaningful beat.

## Bottom UI blocks — hard 3/3/3 rule

- Bottom blocks are interface support, not author commentary.
- Use labels from `scene_packet.current_frame.bottom_block_labels` if present.
- If shown, `✦ Что можно сделать` has exactly 3 action options. No more than 3.
- If shown, `✦ Что <POV> могла бы сказать` has exactly 3 speech options. No more than 3.
- Speech options are written without speaker prefix: no `Акира —`, no `Ливия —`, no quotes. Only the candidate line.
- Speech options must match current POV voice. For Akira: short, dry, sharp/poisonous, controlled; not cute, not theatrical, not explanatory.
- If shown, `✦ Мысли <POV>` has exactly 3 short one-line thoughts. Not one paragraph.
- Each thought should be under ~140 characters and belong only to current POV.
- `✦ Уровни` shows compact current visible numbers only when body/risk/resource/position changed or numbers are useful now.
- `✦ Отношения` is a compact UI panel only.
- If `scene_packet.ui_panels.relationships.items` is not empty, render `✦ Отношения` every scene.
- Relationship line format: `{Пара}: {score} · {label}`. Prefer each item's `render_line`.
- Render at most 3 relationship lines.
- Do not use `Без изменений.` when relationship items exist.
- Forbidden relationship prose: “близость стабильна; Ливия заботится через шум...” or any similar narrative summary.

## NPC and knowledge boundary

- NPCs know only what they saw, heard, were told, read, can access, or plausibly infer from visible signs.
- Delayed/absent characters do not know previous scene events unless told on-screen or stored in character_memory.
- Suspicion is not fact. Let NPCs ask, misread, test, lie, avoid, or infer wrongly.
- Fixed canon characters may enter only if current roster, current-day calendar, state, explicit player action, or already played setup allows it.
- Do not rename an invented/background NPC into a fixed character after the fact.

## Relationships and state

- Use only selected `state/relationship_pairs/<a>__<b>.json` for current scene relationships.
- Do not load all pairs connected to Akira.
- Relationship panel shows compact visible total/label; before introductions use descriptors, not formal “bond”.
- State updates go to `state/character_memory/<id>.json` and `state/relationship_pairs/<a>__<b>.json`, not global stubs.
- Save only meaningful changes: knowledge, promises, threats, conflicts, important lines, relation shifts, state/body/inventory, consequences, hooks.
- Do not save routine movement, glances, ordinary banter without new meaning.

## Hidden lore and energy

- Hidden lore is never narrator fact, random NPC speech, scanner result, lecture, or unearned thought.
- It may surface only as hint, symbol, dream fragment, body reaction, strange feeling, or earned reveal.
- Energy is physical/social/body pressure, not universal solution or decorative repeated effect.
