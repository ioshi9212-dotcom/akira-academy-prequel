# Тесты после patch v5

## 1. Технический smoke-test

```txt
Технический тест. Не продолжай сцену и не пиши художественный ход.

Проверь работу репозитория akira-academy-prequel через Actions.

Сделай:
1. health
2. createSession с reset=true
3. getSessionContext
4. getSessionTurnContract
5. getRequiredFilesManifest
6. getRequiredFilesChunk до конца, пока has_more=false
7. buildScenePacket с include_diagnostics=true, include_source_index=true, include_sources=false

Ответь только техническим отчётом:

- runtime version
- session_id
- current_date
- current_time
- current_location_id
- current_location_text
- active_character_ids
- nearby_character_ids
- scheduled_character_ids
- delayed_character_ids
- required_files
- missing_files
- chunks_total
- packet_status
- packet_version
- rendered_header полностью
- approx_scene_packet_chars
- player_input.segments
- ui_panels.relationships
- forbidden_context
- есть ли в loaded/selected путях старые state/knowledge_state.json или state/relationships.json как runtime source

Сцену не писать.
```

Ожидаемо:

- `runtime version`: `0.3.76-scene-packet-slim-ordered-input-v5`
- `packet_status`: `ready`
- `packet_version`: `scene_packet_v5_slim_rendered_header_ordered_input`
- `rendered_header` доступен
- старые `state/knowledge_state.json` и `state/relationships.json` не используются как runtime source

## 2. Тест порядка реплика / скобка / реплика

```txt
Технический тест. Не пиши сцену.

Создай session reset=true и вызови buildScenePacket для player_input:

Вы за кого переживаете? (поправить сумку на плече, посмотреть сначала на Рэя, потом на Ливию) За меня или академию?

Покажи только:
- packet_status
- packet_version
- rendered_header
- player_input.raw
- player_input.speech
- player_input.actions
- player_input.segments
- scene_packet.output_contract.player_input_order_rules
- diagnostics.approx_scene_packet_chars

Важно: нужно проверить, что порядок сохранился как:
1 speech: Вы за кого переживаете?
2 parenthetical/action/pause: поправить сумку...
3 speech: За меня или академию?
```

Ожидаемо в `player_input.segments`:

```json
[
  {"order": 1, "type": "speech", "text": "Вы за кого переживаете?"},
  {"order": 2, "type": "parenthetical", "text": "поправить сумку на плече, посмотреть сначала на Рэя, потом на Ливию", "pause": "medium"},
  {"order": 3, "type": "speech", "text": "За меня или академию?"}
]
```

## 3. Тест блока отношений

```txt
Технический тест. Не пиши сцену.

Вызови buildScenePacket после загрузки required chunks.
Покажи только:
- packet_status
- ui_panels.relationships
- output_contract.relationship_panel_rules

Проверь, что формат отношений не prose-summary, а UI-панель.
```

Ожидаемо:

```txt
Акира ↔ Ливия: 53 · старые школьные подруги
```

или близкая компактная строка с числом и label.

Запрещённый результат:

```txt
Акира ↔ Ливия: близость стабильна; Ливия заботится через шум и ворчание...
```
