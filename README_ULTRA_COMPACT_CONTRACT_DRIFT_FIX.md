# Academy 1198 v3 — Ultra Compact Contract + Akira Drift Fix

## Что чинит

1. ResponseTooLargeError на длинной сессии.
2. Разрастание scene_contract после добавления energy/progress/prose слоёв.
3. Рассинхрон версии Акиры: compact says v2, старое character_status says v1.

## Что изменено

```text
app/main.py
engine/ultra_compact_contract_rules.md
gpt/custom_gpt_instructions_ULTRA_COMPACT_COMPACT.md
validation/ultra_compact_contract_checklist.md
```

Сохранены предыдущие фиксы:
- energy atmosphere;
- no micro-choice;
- factual prose;
- no-stub scene quality;
- Akira v1/v2;
- header split;
- session guard;
- save layer.

## Как работает

В play-mode API возвращает `scene_contract_v5_ultra_compact`.

Он сохраняет нужные поля:
- current_frame;
- character_slice;
- relationship_slice;
- knowledge_slice;
- character_memory_slice;
- event_engine_slice;
- energy_atmosphere_slice;
- tiny gate contracts.

Но режет всё лишнее:
- длинные contracts;
- полные state logs;
- длинные energy files;
- длинные runtime summaries;
- большие evidence/open_threads/events.

## После загрузки

1. Залить файлы в GitHub с сохранением папок.
2. Дождаться Railway Success.
3. Проверить:
   https://web-production-cd472.up.railway.app/health
4. Обновить Actions schema:
   https://web-production-cd472.up.railway.app/openapi-actions.json
5. Заменить Custom GPT Instructions на:
   `gpt/custom_gpt_instructions_ULTRA_COMPACT_COMPACT.md`
