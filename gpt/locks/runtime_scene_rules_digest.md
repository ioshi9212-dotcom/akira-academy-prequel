# Runtime Scene Rules Digest — Academy 1198 compact

This file is the compact always-loaded rule pack. It replaces the old stack of heavy locks for normal gameplay.

## Required loading tiers
- Use `getSessionTurnContract` first.
- `required_files` / manifest / chunks contain only `must_load_now`.
- Load every required chunk before writing gameplay.
- `load_if_needed_files` are fetched only by explicit trigger: past, hidden-lore audit, style audit, secondary relationship, full calendar audit.
- `reference_only_files` are not gameplay context. Scheduled/delayed characters stay reference until current_frame promotes them.

## Source priority
1. Latest direct user instruction.
2. Latest visible scene facts / scene_history.
3. API current_frame/current_state.
4. Required files loaded for this turn.
5. Active character cards + character_memory.
6. Scene relationship_pairs.
7. Current day calendar.
8. Compact canon/lore policy.
9. Chat memory only as latest player input, not truth source.

## POV and player agency
- Default POV is Akira, but any contract/user-selected POV is valid.
- Text outside parentheses is exact POV speech. Text inside parentheses is POV action/intention/body state.
- Do not choose major POV decisions: consent/refusal, trust, route, attack, reveal, access, public stance.
- Low-stakes automatic POV lines are allowed when they do not decide anything important.
- If an NPC meaningfully challenges/questions/provokes POV, stop at a choice point.
- In non-Akira POV, Akira is an NPC if present: she can act and speak, but her hidden thoughts stay hidden.

## Movement chains and interruption
- A chain like “say X (go to the exit)” means intent/progress, not guaranteed completion.
- If an NPC line, obstacle, question, risk, new information or social pressure appears on the way, stop before completing the chain.
- Do not assume POV stayed silent and continued after a meaningful hook.
- If nothing meaningful happens, compress routine movement to the nearest meaningful beat.
- This applies to exits, showers, corridors, stairs, rooms, registration, training, meals and time skips.

## Scene style
- Gameplay answer is scene only: no API/debug/status text.
- Use the Academy visual-novel header from current state, not hardcoded date/place.
- Dialogue: `**Name/descriptor** — line.` No quotation marks.
- If POV does not know a name, use visible descriptor until introduction/source.
- Write dense readable paragraphs. Do not split narration into 3–5 word fragments.
- Light dry irony/sarcasm is allowed only when tied to visible action.
- Scene must move at least one layer: plot, relationship, knowledge, conflict, reputation, state, energy, schedule, thread or hook.
- Do not play empty routine step by step; compress to meaningful beat.

## NPC and knowledge boundary
- NPCs know only what they saw, heard, were told, read, can access, or plausibly infer from visible signs.
- Delayed/absent characters do not know previous scene events unless told on-screen or stored in character_memory.
- Suspicion is not fact. Let NPCs ask, misread, test, lie, avoid, or infer wrongly.
- Fixed canon characters may enter only from roster/current location/calendar due state/prior setup/player action.
- Do not rename an invented/background NPC into a fixed character after the fact.

## Relationships and state
- Use only selected `state/relationship_pairs/<a>__<b>.json` for current scene relationships.
- Do not load all pairs connected to Akira.
- Relationship panel shows soft visible total/label; before introductions use descriptors, not formal “bond”.
- State updates go to `state/character_memory/<id>.json` and `state/relationship_pairs/<a>__<b>.json`, not global stubs.
- Save only meaningful changes: knowledge, promises, threats, conflicts, important lines, relation shifts, state/body/inventory, consequences, hooks.
- Do not save routine movement, glances, ordinary banter without new meaning.

## Hidden lore and energy
- Hidden lore is never narrator fact, random NPC speech, scanner result, lecture, or unearned thought.
- It may surface only as hint, symbol, dream fragment, body reaction, strange feeling, or earned reveal.
- Energy is physical/social/body pressure, not universal solution or decorative repeated effect.
