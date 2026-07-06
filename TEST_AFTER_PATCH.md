# Тест после patch v6

## 1. Проверка packet

Технический тест. Не пиши сцену.

Сделай:
1. health
2. createSession reset=true
3. buildScenePacket с include_diagnostics=true, include_source_index=false, include_sources=false

Покажи:
- runtime version
- packet_status
- packet_version
- approx_scene_packet_chars
- player_input.segments, если есть ввод
- output_contract.footer_contract
- ui_panels.relationships.items
- render_guard forbidden_context

Ожидаемо:
- version: `0.3.77-scene-packet-footer-3x3x3-v6`
- packet_status: `ready`
- relationship items не пустой на старте Акира/Ливия
- footer_contract содержит exact_count_if_shown = 3

## 2. Проверка игрового footer

Игровой ход:

Вы за кого переживаете? (поправить ремень сумки на плече) За меня или академию?

Ожидаемо внизу:

- `✦ Что можно сделать` — ровно 3 строки.
- `✦ Что Акира могла бы сказать` — ровно 3 строки, без `Акира —`.
- `✦ Мысли Акиры` — ровно 3 короткие строки, не абзац.
- `✦ Отношения` есть, если ui_panels.relationships.items не пустой.
- Отношения выглядят примерно так: `Акира ↔ Ливия: 48 · старые школьные подруги`.
