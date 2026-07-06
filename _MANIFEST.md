# Akira Academy Clean Addons

Пакет добавляет только навигационный слой и минимальное ядро сборки. Карточки персонажей не изменяются.

## Добавляемые части

- `characters/index.yaml` — точный ID-index персонажей для Railway.
- `locations/index.yaml` + `locations/*.yaml` — разрезанный файл локаций, чтобы не грузить всю Академию.
- `state/index.yaml` — индекс state-файлов и триггеров загрузки.
- `state/room_assignments.yaml` — фикс комнаты 214 как факта, а не lock-а.
- `assembly/scene_assembly_chain.yaml` — последовательность сборки scene_packet.
- `rules/scene_core.md` — единственный компактный файл правил сцены.

## Главное правило

Никаких новых `gpt/locks`, runtime-rules, digest-rules, patch-rules и правил поверх правил. Если правило слабое — переписать существующее место, а не добавлять костыль.

## Не включено

- Нет изменений карточек персонажей.
- Нет app/engine/runtime-кода.
- Нет старых глобальных `knowledge_state.json` / `relationships.json`.
- Нет hidden-lore always-load.
