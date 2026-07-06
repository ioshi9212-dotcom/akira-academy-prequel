# Akira Academy Prequel patch v6

Что исправлено поверх v5:

1. Жёсткий footer-формат: 3 действия, 3 реплики, 3 мысли.
2. Варианты реплик больше не должны выводиться как `Акира — ...` / `Ливия — ...`; только текст реплики.
3. Мысли внизу — 3 короткие строки, не один длинный абзац.
4. `✦ Отношения` обязателен, если `scene_packet.ui_panels.relationships.items` не пустой.
5. Отношения рендерятся только UI-строкой `Пара: score · label`; prose-пересказ запрещён.
6. Добавлен `footer_contract` в `scene_packet.ui_panels.footer` и `output_contract.footer_contract`.
7. Версия runtime поднята до `0.3.77-scene-packet-footer-3x3x3-v6`.

Заменить файлы в репозитории теми же путями и деплойнуть Railway.
