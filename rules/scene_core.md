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
- Reference-only characters may appear only as distant background, sound, silhouette, scheduled name, or route hook. Do not give them personality analysis, skill analysis, inner state, new choices, or meaningful reaction.

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

## Bottom UI

- Bottom UI is part of the gameplay format, not prose.
- Use no more than 3 bottom blocks total.
- Inside any bottom block, use no more than 3 bullet lines/items.
- If a block has no useful changed/active information, omit the block.
- Do not output long suggestion menus. Three options maximum.

### Allowed bottom block order

1. `✦ Что можно сделать`
2. `✦ Уровни`
3. `✦ Отношения`

Do not add extra bottom blocks such as `Что Акира могла бы сказать`, `Состояние`, `Инвентарь`, `Позиция`, `Варианты реплик`, unless the user explicitly asks in technical mode.

### `✦ Что можно сделать`

- Use only when the scene ends on a real choice point.
- Maximum 3 options.
- Options must be actions, not suggested exact dialogue.
- Do not lead the player into one preferred tone.

Correct example:

```text
✦ Что можно сделать
— Ответить Рэю и отпустить его.
— Пойти к заднему входу через спортплощадки.
— Остановиться и осмотреть площадку.
```

### `✦ Уровни`

- Use only active numeric or compact state lines that matter now.
- Maximum 3 lines.
- Do not write vague prose like `социальное внимание: умеренное` unless the state source gives that value or the scene visibly changed it.
- Preferred format: `Название: значение/100 · короткая метка` or `Название: короткое состояние`, only if loaded/current state supports it.
- For start/court scenes, allowed level subjects are: `Сумка`, `Внимание`, `Энергия`, `Усталость`, `Риск`, `Позиция`.
- Do not invent unrelated levels.

Correct examples:

```text
✦ Уровни
Сумка: тяжёлая · нагрузка на плечо
Внимание: растёт · спортплощадка заметила новеньких
Позиция: задний вход · путь через корт
```

```text
✦ Уровни
Энергия: спокойно · без всплесков
Сумка: тяжёлая · заметно по движению
Позиция: у корта · до регистрации нужно пройти дальше
```

### `✦ Отношения`

- Relationships must use numeric values from loaded `state/relationship_pairs/*.json` only.
- Never write `без изменений` in the relationships block if an exact relationship pair file is loaded.
- If an exact pair file is loaded, output up to 3 numeric metrics from `surface_dynamic`.
- For the pair line, use the pair label from `surface_dynamic.label` if helpful, but keep it short.
- Preferred metrics in order: `affection`, `trust`, `tension`. If a scene specifically changed another loaded metric, one of the three may be replaced by `jealousy`, `respect`, `curiosity`, or `resentment`.
- Maximum 3 lines total inside the block.

Correct example from `state/relationship_pairs/akira__livia.json`:

```text
✦ Отношения
Акира ↔ Ливия: привязанность 18 · доверие 14 · напряжение 0
```

Alternative if exactly one metric visibly changed:

```text
✦ Отношения
Акира ↔ Ливия: привязанность 18 · доверие 14 · напряжение 1
```

Forbidden:

```text
✦ Отношения
Акира ↔ Ливия: без изменений.
```

Forbidden:

```text
✦ Отношения
Без изменений.
```

If no relationship pair file is loaded, omit `✦ Отношения` entirely.
