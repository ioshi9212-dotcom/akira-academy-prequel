# Akira Academy Prequel

Отдельный репозиторий памяти и правил для интерактивной предыстории Академии Астрейн.

Это НЕ основная новелла и НЕ тестовый генератор.

## Цель

Вести предысторию 1198–1206 так, чтобы она объясняла будущие отношения, травмы, сближения, отступления, ревность, репутацию, силу, скрытые конфликты и последствия.

Предыстория не должна ломать будущий канон. Она должна объяснять, почему в будущем персонажи стали такими.

## Старт

- Дата старта: 15 августа 1198.
- Место старта: подъезд к территории Академии; Рэй привозит Акиру и Ливию, затем они идут к заднему маршруту со стороны корта.
- Акира приходит с Ливией через менее людный вход по совету Рэя.
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

## Ключевые файлы

### Active lore

- `canon_lore/index.yaml` — active lore index.
- `canon_lore/core/world_background.yaml` — short world base.
- `canon_lore/academy/academy_background.yaml` — always-loaded Academy base: look, tone, uniform, tech level.
- `canon_lore/academy/academy_full.yaml` — Academy rules/systems when needed.
- `canon_lore/academy/academy_locations.yaml` — campus locations when needed.
- `canon_lore/hidden/hidden_lore_policy.yaml` — rule that prevents hidden-lore leaks.

Old `canon/` and long hidden lore are archive-only unless explicitly loaded.

### Characters

Clean YAML-папки — основной источник персонажей.

- `characters/character_id_index.md` — стабильные ID персонажей.
- `characters/akira/character.yaml` — Акира.
- `characters/akira/main.yaml` — краткая карточка Акиры, если используется.
- `characters/akira/past.yaml` — прошлое Акиры, если используется.
- `characters/livia/character.yaml` — Ливия.
- `characters/kir/character.yaml` — Кир.
- `characters/haru/character.yaml` или `characters/haru/main.yaml` — Хару.
- `characters/raiden/character.yaml` или `characters/raiden/main.yaml` — Райден.
- `characters/kiara/character.yaml` или `characters/kiara/main.yaml` — Киара.
- `characters/kael_north/character.yaml` или `characters/kael_north/main.yaml` — Кэйл Норт.

Старые `characters/main/*.md` — только fallback для legacy-ссылок, не основной источник.

### State

- `state/current_state.json` — текущая сцена.
- `state/relationship_pairs` — отношения.
- `state/reputation_state.json` — репутация.
- `state/power_state.json` — сила и публичные/скрытые уровни.
- `state/rumors_state.json` — слухи.
- `state/character_memory.json` — кто что знает.
- `state/inventory_state.json` — реальные предметы, одежда и скрытый карман пространства.
- `state/location_registry.md` — сыгранные/уточнённые локации, а не дубль всей карты.
- `state/future_locks_progress.json` — продвижение к будущему канону.
- `state/scene_history.json` — краткая история сцен.
- `calendar/calendar_index.yaml`, `calendar/story_spine_1198.yaml`, `calendar/days/{current_date}.yaml`, `engine/calendar_day_runtime_rules.md` — календарь, ритм Академии и крючки дня.
- `state/memory_update_rules.md` — правила обновления памяти.
- `state/inventory_rules.md` — правила предметов и кармана пространства.
- `state/story_lines.json` — сюжетные линии, события и открытые обязательства.

### GPT

- `gpt/engine_prompt.md` — главный промпт движка.
- `gpt/scene_format.md` — формат сцены.
- `gpt/locks/academy_start_cleanup_lock.md` — фикс стартовой локации, одежды и устаревших дублей.

### Templates

- `templates/npc_card_template.md` — шаблон NPC-карточки.

## Как должен работать будущий GPT

1. Читать текущий state.
2. Читать turn-contract / required files.
3. Читать clean YAML-карточки активных персонажей.
4. Читать нужный canon и hidden lore, но не раскрывать его персонажам автоматически.
5. Для любой сцены в академии читать `canon/academy_rules_index.md` и нужные тематические файлы правил.
6. Писать сцену в формате из `gpt/scene_format.md` / runtime digest.
7. Не тянуть время по минутам.
8. Держать Акиру под управлением игрока.
9. После сцены обновлять state-файлы: отношения, репутацию, знания, слухи, предметы, локации, историю сцены.

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
