# Akira Academy Prequel

Отдельный репозиторий памяти, правил и runtime-контекста для интерактивной предыстории Академии Астрейн.

Это НЕ основная новелла и НЕ тестовый генератор.

## Цель

Вести предысторию 1198–1206 так, чтобы она объясняла будущие отношения, травмы, сближения, отступления, ревность, репутацию, силу, скрытые конфликты и последствия.

Предыстория не должна ломать будущий канон. Она должна объяснять, почему в будущем персонажи стали такими.

## Старт

- Дата старта: 15 августа 1198.
- Первый кадр: подъезд к территории Академии / место высадки перед входным маршрутом.
- Рэй привозит Акиру и Ливию, коротко реагирует на тяжёлую сумку, затем уезжает после handoff.
- Корт / мяч / Хару / Райден не должны появляться в первой строке старта. Они становятся актуальны только после входного маршрута и продвижения текущего кадра.
- Акира приходит с Ливией через менее людный маршрут по совету Рэя.
- Акире 17 лет.
- Райдену 17 до 31 августа, затем 18.
- Хару 18.
- 15–22 августа — неделя проверок.
- 23–30 августа — неделя отдыха и адаптации.
- 31 августа — появление Самуэля и день рождения Райдена.
- 1 сентября — начало обучения.

## Главные правила

- Имена в сцене пишутся русскими буквами.
- Технические ID пишутся латиницей в `lowercase_snake_case`.
- Имена персонажей должны звучать японско-европейски, не по-русски.
- Не использовать персонажей из старых сессий, тестовой новеллы или основной игры, если они не внесены в этот репозиторий.
- Hidden lore не раскрывается персонажам автоматически.
- Персонажи знают только то, что видели, слышали, узнали по должности, получили через рассказ или логично предположили.
- Академия не тюрьма: занятия обычно до 15:00, дальше свободное время, после 23:00 контроль общежития.
- Время не тянуть по минутам без причины.
- Акира автоматически замечает очевидные детали окружения.
- Предметы не появляются из воздуха.
- Если `buildScenePacket` не вернул `packet_status: ready`, сцену писать нельзя.

## Runtime-порядок для GPT / Actions

Нормальная сцена должна идти через такой порядок:

1. `health`
2. `createSession` при новом/сброшенном запуске
3. `getSessionContext`
4. `getSessionTurnContract`
5. `getRequiredFilesManifest`
6. `getRequiredFilesChunk` до конца, пока `has_more=false`
7. `buildScenePacket`
8. Только после этого писать сцену.
9. После сцены — `applyTurnResult` с meaningful changes.

`buildScenePacket` в v5 — это компактный render-packet. Он не должен повторно тащить полный лор, полные карточки и память: полный контент уже приходит через required file chunks.

## Формат шапки сцены

Сцена должна начинаться с `scene_packet.current_frame.rendered_header` дословно.

Запрещены старые loose-headers:

```txt
📅 Дата:
🎒 При себе:
1198-08-15 · late_morning
```

Если rendered_header недоступен из-за ошибки packet — не писать fallback-сцену.

## Правило ввода игрока

Текст вне скобок — точная реплика текущего POV.

Текст в скобках — действие, жест, мысль, телесная реакция, намерение, движение или пауза.

Порядок обязателен.

Пример:

```txt
Вы за кого переживаете? (поправить сумку на плече) За меня или академию?
```

Нужно читать как:

1. реплика: `Вы за кого переживаете?`
2. действие/пауза: `поправить сумку на плече`
3. реплика: `За меня или академию?`

Нельзя склеивать в одну реплику:

```txt
Вы за кого переживаете? За меня или академию?
```

Если скобка длинная, это длинная пауза: NPC или среда могут успеть отреагировать, но нельзя переставлять или стирать следующую реплику игрока.

## Отношения / нижний UI-блок

`✦ Отношения` — это UI-панель, а не авторский пересказ.

Правильный формат:

```txt
✦ Отношения
Акира ↔ Ливия: 53 · старые школьные подруги
```

Если отношений не меняли и блок не нужен — его можно опустить.

Если блок показан без изменений:

```txt
✦ Отношения
Без изменений.
```

Запрещено:

```txt
Акира ↔ Ливия: близость стабильна; Ливия заботится через шум и ворчание...
```

## Ключевые файлы

### API / runtime

- `app/server.py` — входная точка FastAPI.
- `app/context_transport_header_hotfix.py` — OpenAPI, version, подключение runtime patches.
- `app/response_size_guard_runtime_patch.py` — компактный context/turn-contract/manifest/chunks.
- `app/scene_packet_runtime_patch.py` — компактный scene packet, rendered_header, ordered player input segments, UI rules.
- `app/state_write_runtime_patch.py` — запись meaningful changes в per-character memory и relationship pairs.

### Active lore

- `canon_lore/index.yaml` — active lore index.
- `canon_lore/core/world_background.yaml` — short world base.
- `canon_lore/academy/academy_background.yaml` — Academy base: look, tone, uniform, tech level.
- `canon_lore/academy/academy_full.yaml` — Academy rules/systems when needed.
- `canon_lore/academy/academy_locations.yaml` — campus locations when needed.
- `canon_lore/hidden/hidden_lore_policy.yaml` — rule that prevents hidden-lore leaks.

Old `canon/` and long hidden lore are archive-only unless explicitly loaded.

### Characters

Clean YAML-папки — основной источник персонажей.

- `characters/character_id_index.md` — стабильные ID персонажей.
- `characters/akira/character.yaml` — Акира.
- `characters/akira/main.yaml` — краткая карточка Акиры, если используется.
- `characters/akira/past.yaml` — прошлое Акиры, только при trigger.
- `characters/livia/character.yaml` — Ливия.
- `characters/livia/main.yaml` — краткая карточка Ливии, если используется.
- `characters/kir/character.yaml` — Кир.
- `characters/haru/character.yaml` или `characters/haru/main.yaml` — Хару.
- `characters/raiden/character.yaml` или `characters/raiden/main.yaml` — Райден.
- `characters/kiara/character.yaml` или `characters/kiara/main.yaml` — Киара.
- `characters/kael_north/character.yaml` или `characters/kael_north/main.yaml` — Каэл Норт.

Старые `characters/main/*.md` — только fallback для legacy-ссылок, не основной источник.

### State

- `state/current_state.json` — текущая сцена.
- `state/character_memory/<id>.json` — runtime-память конкретного персонажа.
- `state/relationship_pairs/<a>__<b>.json` — отношения конкретной пары.
- `state/reputation_state.json` — репутация.
- `state/power_state.json` — сила и публичные/скрытые уровни, если используется.
- `state/rumors_state.json` — слухи.
- `state/inventory_state.json` — реальные предметы, одежда и скрытый карман пространства.
- `state/location_registry.md` — сыгранные/уточнённые локации, а не дубль всей карты.
- `state/future_locks_progress.json` — продвижение к будущему канону.
- `state/scene_history.json` — краткая история сцен.
- `state/story_lines.json` — сюжетные линии, события и открытые обязательства.
- `state/akira_progress_state.json` — видимые уровни/риски Акиры для UI.

Не использовать как runtime source:

- `state/character_memory.json` — устаревший путь, заменён на `state/character_memory/<id>.json`.
- `state/knowledge_state.json` — disabled legacy stub / reference-only.
- `state/relationships.json` — disabled legacy stub / reference-only.
- `state/legacy/*` — архив.

### Calendar

- `calendar/calendar_index.yaml` — reference/index.
- `calendar/story_spine_1198.yaml` — reference/story spine.
- `calendar/days/{current_date}.yaml` — активный день, грузится в required files.
- `engine/calendar_day_runtime_rules.md` — правила использования календаря, если нужно.

### GPT

- `gpt/engine_prompt.md` — главный промпт движка.
- `gpt/scene_format.md` — формат сцены.
- `gpt/scene_output_contract_1198.json` — жёсткий writer contract.
- `gpt/locks/runtime_scene_rules_digest.md` — компактные always-loaded правила.
- `gpt/locks/player_input_anchor_lock.md` — подробное правило чтения хода игрока.
- `gpt/locks/academy_start_cleanup_lock.md` — фикс стартовой локации, одежды и устаревших дублей.

### Templates

- `templates/npc_card_template.md` — шаблон NPC-карточки.

## Запреты

- Не делать Райдена холодным философом.
- Не делать Хару клоуном.
- Не делать Ливию пустой соперницей.
- Не делать Акиру пассивным призом или машиной убийства.
- Не раскрывать hidden lore без сцены.
- Не добавлять старых персонажей из других проектов.
- Не писать предметы, которых нет.
- Не менять ID персонажей после фиксации.
- Не считать выданную форму надетой без действия игрока или явного state.
- Не писать сцену из старого context fallback, если packet/chunks не загрузились.


### Footer / нижний интерфейс

Нижние блоки являются интерфейсом выбора, а не авторским комментарием.

- `✦ Что можно сделать` — ровно 3 действия, если блок показан.
- `✦ Что <POV> могла бы сказать` — ровно 3 реплики без имени и тире. Не писать `Акира — ...`.
- `✦ Мысли <POV>` — ровно 3 короткие мысли отдельными строками, не абзацем.
- `✦ Отношения` — компактная UI-панель по `scene_packet.ui_panels.relationships.items`, если items не пустой.
- Отношения нельзя писать авторским пересказом вроде «близость стабильна; Ливия заботится...».
