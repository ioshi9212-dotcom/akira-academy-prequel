# Progress and relationship score panel rules

This file defines the visible end-of-scene panel for Akira's current state and relationship totals.

## Purpose

Akira must not be treated as automatically perfect. Training, conflict, fatigue, injuries, control and relationships must have visible state and saved consequences.

The panel shows current totals, not only the change from the last scene.

## End-of-scene panel

After the usual blocks, add:

```txt
✦ Состояние

Физика: 42/100 · выносливость: 36/100 · усталость: 18/100
Энергия: доступ 12/100 · контроль 9/100 · риск: низкий

✦ Отношения

Ливия: +24 · тёплый контакт
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

Suggested fields:

```json
{
  "physical_power": 40,
  "stamina": 35,
  "agility": 55,
  "combat_habit": 70,
  "fatigue": 15,
  "injury_level": 0,
  "energy_access": 10,
  "energy_control": 8,
  "energy_capacity_visible": 15,
  "energy_risk": "low",
  "hidden_energy_potential": "very_high_hidden_do_not_show_as_current_power"
}
```

Visible power must use only visible/current access, control, fatigue and injury state. Hidden potential is not current usable power.

## Training and cost

Training can improve stats, but also adds cost.

Examples:
- light training: small physical/control progress, small fatigue;
- hard training: higher progress, higher fatigue;
- overtraining: possible progress, but fatigue/injury/risk increase;
- rest/food/sleep: fatigue decreases, stamina recovers.

Do not increase stats just because Akira exists in the scene. Use evidence.

## Relationship total score

Detailed relationship fields remain internal: trust, interest, respect, warmth, attachment, tension, irritation, fear, resentment, suspicion.

The visible relationship panel shows one summed score per character.

Suggested score logic:

```txt
score =
  trust * 1.2
+ respect * 1.0
+ interest * 0.8
+ warmth * 1.2
+ attachment * 1.5
- tension * 0.8
- irritation * 0.7
- fear * 1.0
- resentment * 1.2
- suspicion * 1.0
```

Round to integer and clamp to -100..100.

Interest alone is not warmth. A character can be interested and still tense, wary or irritated.

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
- reserved character: `осторожный интерес`, `молча наблюдает`, `доверяет неохотно`;
- warm character: `тёплый контакт`, `явно тянется`, `защищает без просьбы`;
- cold character: `холодная настороженность`, `держит дистанцию`, `молча держится рядом`.

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
      "interest": 2,
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
