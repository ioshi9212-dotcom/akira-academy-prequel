# academy_prequel_visible_scene_before_state_patch_v3

Цель патча: закрыть две подтверждённые дыры, найденные техническим тестом в старом игровом чате.

## Что исправлено

1. Убран `app/prompt_builder.py` из `required_files`, чтобы manifest не давал ложный `missing_count=1`.
2. Добавлен lock `gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md`.
3. Усилен `player_input_anchor_lock`: если игрок не дал реплику вне скобок, ИИ не может писать новые строки `**Акира** — ...` в теле сцены.
4. Усилен `gameplay_response_gate`: state/apply-turn-result не заменяет видимую сцену.
5. Усилен `prompt_builder.py`: после tool call финальный ответ обязан быть сценой, а не status/summary.
6. Усилен `scene_format.md`: право голоса Акиры принадлежит игроку.

## Файлы

- `app/compact_context_patch.py`
- `app/prompt_builder.py`
- `gpt/scene_format.md`
- `gpt/locks/gameplay_response_gate.md`
- `gpt/locks/player_input_anchor_lock.md`
- `gpt/locks/gameplay_visible_scene_before_state_and_no_status_summary.md`

## Проверка после деплоя

Ожидаемо:

- `manifest.missing_count = 0`
- `app/prompt_builder.py` больше не в `missing_files`
- новый lock есть в `loaded_files.path`
- все chunks проходят без `ResponseTooLargeError`
- тест A–E должен вернуть `ДА` для всех пунктов.
