# Progress, relationship panel, scene density and choice block rules

This file defines the visible end-of-scene panel, relationship totals, dense scene prose, italic remarks and bottom choice formatting.

## Purpose

Akira must not be treated as automatically perfect. Training, conflict, fatigue, injuries, control and relationships must have visible state and saved consequences.

The panel shows current totals, not only the change from the last scene.

Scene prose must stay dense and playable: dialogue, short stage remarks, visible action, consequence. Do not drown the scene in decorative paragraphs.

## End-of-scene panel

After the usual blocks, add:

```txt
✦ Состояние

Физика: 42/100 · выносливость: 36/100 · усталость: 18/100
Энергия: доступ 12/100 · контроль 9/100 · риск: низкий

✦ Отношения

Ливия: +53 · старые подруги
Кир: +9 · осторожный интерес
Хару: +18 · явный интерес
Райден: -3 · холодная настороженность
```

Do not show `+1 this scene` as the main value. The visible number is always the current total score.

If a relationship changed during the scene, it may be shown as a total transition:

```txt
Кир: +9 → +11 · осторожный интерес
```

Do not show detailed trust/interest/tension values in the visible panel unless the user asks for debug.

## Akira progress state

Use `state/akira_progress_state.json` or session state equivalent.

Visible power must use only visible/current access, control, fatigue and injury state. Hidden potential is not current usable power.

Training can improve stats, but also adds cost:
- light training: small physical/control progress, small fatigue;
- hard training: higher progress, higher fatigue;
- overtraining: possible progress, but fatigue/injury/risk increase;
- rest/food/sleep: fatigue decreases, stamina recovers.

Do not increase stats just because Akira exists in the scene. Use evidence.

## Relationship total score

Detailed relationship fields remain internal: affection, trust, curiosity/interest, respect, warmth, attachment, tension, irritation, fear, resentment, suspicion.

The visible relationship panel shows one summed score per character.

Suggested score logic:

```txt
score =
  affection * 1.2
+ trust * 1.2
+ respect * 1.0
+ curiosity * 0.8
+ interest * 0.8
+ warmth * 1.2
+ attachment * 1.5
- tension * 0.8
- irritation * 0.7
- fear * 1.0
- resentment * 1.2
- suspicion * 1.0
- jealousy * 0.4
```

Round to integer and clamp to -100..100.

Interest/curiosity alone is not warmth. A character can be interested and still tense, wary or irritated.

Existing relationship fields are the source of truth. If `relationship_score_panel` is missing, zero, or stale, recalculate the visible total from `relationships.json`.

## Relationship labels

Use one short label next to the total.

General labels:
- -80..-60: враждебность
- -59..-35: сильное напряжение
- -34..-15: настороженность
- -14..+14: неясно
- +15..+34: интерес
- +35..+54: доверие
- +55..+74: близость
- +75..+100: сильная привязанность

Adapt labels to character personality when useful:
- Ливия: `старые подруги`, `тёплая близость`, `почти семья`;
- Кир: `осторожный интерес`, `доверяет неохотно`, `свой, но язвит`;
- Хару: `явный интерес`, `тянется ближе`, `сильная симпатия`;
- Райден: `холодная настороженность`, `молча наблюдает`, `держится рядом`.

## Scene density

Use dense interactive scene prose.

Preferred rhythm:
- dialogue line;
- short italic stage remark if needed;
- visible action or reaction;
- next dialogue line.

Every paragraph must do at least one job:
- move the scene;
- show a visible reaction;
- change position or object state;
- create conflict or pressure;
- reveal usable information;
- change relationship, knowledge, state, rumor or schedule.

Delete paragraphs that only repeat mood, decorate the prose, or say the same emotion in prettier words.

## Italic remarks

Use italics for stage remarks, visible action, body reaction, physical detail or brief atmospheric pressure.

Good:

```txt
**Хару** — Она меня похоронила красиво. Это не повод отдавать её толпе.

*Он гасит экран телефона большим пальцем и убирает его в карман куртки.*
```

Short remark can stay inside the dialogue line:

```txt
**Джун** — Акира. Назад. (*тихо, но резко*)
```

Do not use italics for long lyric inserts, repeated inner monologue, philosophy or decorative mood between every action.

## Action choices block

The block `✦ Что можно сделать` must contain direct actions only.

Do not start options with:
- `Акира может...`
- `Можно...`
- `Попробовать...`

Use direct action wording:

```txt
✦ Что можно сделать

◈ Взять обе ключ-карты и пройти с Ливией к комнате 214.
◈ Взять только свою ключ-карту, оставив вторую Ливии.
◈ Уточнить у старшей этажа про окно, датчики или вечернюю отметку.
◈ Забрать маршрут и пройти к лестнице, не задерживаясь в холле.
```

No ready spoken lines inside action options.

If an option contains a phrase Akira would say, move that phrase to `✦ Что Акира могла бы сказать`.

Bad action option:

```txt
◈ Предупредить девушку у автомата, что смотреть и трогать — разные виды смерти.
```

Correct split:

```txt
✦ Что можно сделать
◈ Остановиться у автомата и повернуться к девушке.

✦ Что Акира могла бы сказать
— “Смотреть и трогать — разные виды смерти.”
```

## Speech choices block

The block `✦ Что Акира могла бы сказать` must contain only direct short lines Akira could say.

No action summaries here.
No explanations of intent.
No `Акира может сказать...`.

Use:

```txt
— “Смотреть и трогать — разные виды смерти.”
— “Лив, забирай карту. Я не собираюсь воспитывать холл.”
```

## Bottom block anti-duplication

Do not duplicate the same choice as both an action and a speech line.

Action option = physical/strategic move.
Speech option = exact line.

If the choice is mostly a phrase, put it only in speech.
If the choice is mostly movement, put it only in action.

## State write rules

If the scene changes progress or relationships, save internal deltas with reasons, but visible panel still shows totals.

Example:

```json
{
  "akira_progress_state_changes": {
    "stamina": -3,
    "fatigue": 5,
    "combat_habit": 1,
    "reason": "short hard physical exchange"
  },
  "relationship_changes": {
    "akira__kir": {
      "curiosity": 2,
      "tension": 1,
      "reason": "he noticed Akira hiding a reaction but got no explanation"
    }
  },
  "relationship_score_panel_changes": {
    "akira__kir": {
      "score": 11,
      "label": "осторожный интерес"
    }
  }
}
```

Do not save every tiny glance. Save only meaningful changes.

## Final check before sending

Rewrite the scene or bottom blocks if:
- an action starts with `Акира может`;
- an action contains a finished witty threat or exact quote;
- a speech option describes an action instead of giving a line;
- all action options are just different ways to say a line;
- italic paragraphs are doing only decorative mood work;
- the scene contains too many empty atmospheric paragraphs;
- the visible relationship panel shows only scene delta instead of current total score.
