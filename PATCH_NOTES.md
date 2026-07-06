# Akira Academy Prequel — patch v5

## Что исправлено

1. `buildScenePacket` больше не должен падать от `ResponseTooLargeError` на обычном ходе.
   - Packet стал slim.
   - Полные карточки/память/лор не дублируются внутри scene_packet.
   - Полный контент по-прежнему должен грузиться через `getRequiredFilesManifest` + `getRequiredFilesChunk`.

2. Исправлен порядок хода игрока.
   - Добавлено `scene_packet.player_input.segments`.
   - Реплика / скобка / реплика больше не склеиваются.
   - Скобки считаются действием/мыслью/паузой.

3. Исправлен блок отношений.
   - `✦ Отношения` теперь описан как UI-панель.
   - Запрещён prose-пересказ вида: `близость стабильна; Ливия заботится...`.
   - Правильный формат: `Акира ↔ Ливия: 53 · старые школьные подруги` или `Без изменений.`

4. README обновлён.
   - Убран устаревший `state/character_memory.json` как runtime source.
   - Уточнено, что `state/knowledge_state.json` и `state/relationships.json` — legacy/reference-only.
   - Уточнён порядок Actions.
   - Уточнён старт: первый кадр у места высадки, корт позже.

5. Runtime digest обновлён.
   - Убран намёк на old header.
   - Добавлены правила `rendered_header`, ordered segments и relationship UI.

## Файлы в архиве

Заменить в репозитории:

- `app/scene_packet_runtime_patch.py`
- `app/context_transport_header_hotfix.py`
- `gpt/scene_output_contract_1198.json`
- `gpt/locks/runtime_scene_rules_digest.md`
- `gpt/locks/player_input_anchor_lock.md`
- `README.md`

Дополнительно:

- `TEST_AFTER_PATCH.md` — тесты для чата после деплоя.
- `PATCH_NOTES.md` — эта заметка.

## После замены

1. Закоммитить файлы.
2. Деплойнуть Railway / перезапустить runtime.
3. Проверить `/health`: version должна быть `0.3.76-scene-packet-slim-ordered-input-v5`.
4. Прогнать тесты из `TEST_AFTER_PATCH.md`.
