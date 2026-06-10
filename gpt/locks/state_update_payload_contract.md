# Lock: обязательный payload записи состояния после сцены

Этот файл нужен не для стиля сцены, а для записи памяти.

Backend `apply-turn-result` НЕ анализирует текст сцены самостоятельно. Он сохраняет только те изменения, которые GPT явно передал в payload.

Если в сцене были отношения, интерес, ревность, отказ, конфликт, наблюдение, новое знание, слух, репутация, обещание, будущий крючок или движение сюжетной линии — перед `apply-turn-result` обязательно сформировать `data` с нужными секциями.

## Минимальный payload

```json
{
  "relationship_changes": [],
  "story_lines_changes": {},
  "knowledge_changes": {},
  "current_state_changes": {}
}
```

Не отправлять пустой payload, если сцена что-то изменила.

## relationship_changes

Формат пары: `akira__raiden`, `livia__raiden`, `akira__haru`, `kir__akira`.

Alias-safe: backend сведёт `raiden_sterling` к `raiden`, `haru_foster` к `haru`, `livia_cross` к `livia`, если старая пара уже есть.

Пример:

```json
{
  "relationship_changes": [
    {
      "pair": "akira__raiden",
      "tension_delta": 3,
      "curiosity_delta": 2,
      "jealousy_delta": 1,
      "status": "первое заметное напряжение; не осознанное знакомство, а телесная тяга/раздражение",
      "notes": ["Райден заметил, что Акира скрывает уровень силы; Акира раздражена тем, что он смотрит слишком точно."],
      "memory": ["Первый взгляд/столкновение дал телесный след: ток, пустота, тяга и раздражение; персонажи не знают причину."],
      "open_threads": ["Райден будет искать недостатки Акиры и пытаться вывести её из скрытого минимума."],
      "last_interaction": "1198-08-15 registration/social route"
    }
  ]
}
```

## story_lines_changes

События и линии должны иметь абсолютную дату.

Пример:

```json
{
  "story_lines_changes": {
    "active_lines": {
      "akira_raiden_hidden_pull": {
        "status": "active_hidden_background",
        "date_started": "1198-08-15",
        "characters": ["akira", "raiden"],
        "summary": "Неосознанная тяга/боль/пустота между Акирой и Райденом начала проявляться как раздражение и внимание.",
        "next_beats": ["Райден цепляет скрытность Акиры", "Акира злится на его точность"]
      },
      "haru_akira": {
        "status": "early_hook",
        "date_started": "1198-08-15",
        "characters": ["akira", "haru"],
        "summary": "Хару цепляет отсутствие обычной реакции Акиры; линия должна идти к отношениям через конфликт, баскетбол и последствия.",
        "next_beats": ["Хару пытается получить реакцию", "баскетбол как будущий язык давления"]
      }
    },
    "shared_events": [
      {
        "event_id": "1198_08_15_first_raiden_akira_tension",
        "date": "1198-08-15",
        "time": "late_morning",
        "location": "academy_route_or_registration",
        "participants": ["akira", "raiden"],
        "witnesses": ["livia", "haru"],
        "known_by": ["akira", "raiden", "livia", "haru"],
        "not_known_by": ["kiara", "kael_north"],
        "source_notes": {"visibility": "visible tension only; hidden bond unknown"},
        "summary": "Акира и Райден зацепили друг друга вниманием и раздражением; скрытая связь не раскрыта.",
        "line_refs": ["akira_raiden_hidden_pull"]
      }
    ]
  }
}
```

## knowledge_changes

Не добавлять знание персонажу без источника.

Пример:

```json
{
  "knowledge_changes": {
    "akira": {
      "knows_names": ["Райден", "Хару"],
      "does_not_know": ["фамилия Райдена", "причина реакции Райдена на белые волосы", "цикл", "гибридность Райдена"]
    },
    "raiden": {
      "observed": ["Акира скрывает полный уровень реакции/силы", "Акира реагирует на давление ядом, а не страхом"],
      "does_not_know": ["природа пространства Акиры", "скрытая связь цикла"]
    }
  }
}
```

## current_state_changes

После сцены обновлять active/nearby/speaking/looked_at/current_scene_goal/last_scene_anchor.

Пример:

```json
{
  "current_state_changes": {
    "active_characters": ["akira", "livia", "raiden", "haru"],
    "nearby_characters": ["kir"],
    "looked_at_character_ids": ["raiden", "haru"],
    "current_scene_goal": "finish registration route with first social tension active",
    "last_scene_anchor": "Райден заметил скрытность Акиры; Хару заинтересовался её отсутствием реакции; Ливия заметила обоих."
  }
}
```

## Запрет

Нельзя считать ход сохранённым, если:

- в сцене был отказ/ревность/интерес, но `relationship_changes` пустой;
- появилась новая линия, но `story_lines_changes` пустой;
- персонаж узнал имя/факт, но `knowledge_changes` пустой;
- changed_files после apply-turn-result не содержит нужные state-файлы.

Если changed_files пустой при значимой сцене — ход технически незавершён.
