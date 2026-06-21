# Scene density and choice block rules

This file fixes scene rhythm, italic remarks and bottom action choices.

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
**Haru** — She buried me beautifully. Not a reason to hand her to the crowd.

*He turns the phone screen off and slips it into his jacket pocket.*
```

Short remark can stay inside the dialogue line:

```txt
**Jun** — Akira. Back. (*quiet, but sharp*)
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

## Final check before sending

Rewrite the bottom blocks if:
- an action starts with `Акира может`;
- an action contains a finished witty threat or exact quote;
- a speech option describes an action instead of giving a line;
- all action options are just different ways to say a line;
- italic paragraphs are doing only decorative mood work.
