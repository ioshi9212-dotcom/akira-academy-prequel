# POV Switch Mode

Loads only when latest command contains `POV:` or `пов:`.

## Purpose

POV switch temporarily moves the scene focus from Akira to another named character.  
This is a normal prose scene from another character's camera, not a technical summary.

## Examples

```txt
не продолжай сцену, POV: Ливия
пов: Райден
POV: Хару
пов: Норт
продолжить POV: Ливия
```

## Rules

- Default gameplay POV is Akira.
- POV switch lasts one response unless next command keeps POV.
- Time continues normally.
- Akira may be absent, background, or present as NPC.
- Akira does not gain knowledge from another POV unless she saw/heard/was told.
- Relationships, knowledge, reputation, rumors, story_lines and calendar_runtime update normally for involved characters.
- Do not break the POV character's personality.

## Player input

While POV is active:
- text outside parentheses is the POV character's exact speech;
- text inside parentheses is POV character action/gesture/body state/intention;
- do not give that speech to Akira;
- possible lines go only in bottom block.

## Header

Add POV line after time/location:

```txt
🎥 POV: Ливия · Акира этого не видит напрямую
```

If Akira is present:

```txt
🎥 POV: Райден · Акира рядом, но фокус восприятия не её
```

## Bottom blocks

Use POV-specific blocks:

- ✦ Что можно сделать
- ✦ Что Ливия могла бы сказать / Что Райден мог бы сказать / ...
- ✦ Мысли Ливии / Мысли Райдена / ...

Do not write "Мысли Акиры" unless Akira is current POV.

## Tone

- Livia: fast, social, vivid, emotional, noisy surface with vulnerability.
- Raiden: short internal pressure, control, irritation, discipline, denial.
- Haru: movement, heat, performance, playful pressure, humor over discomfort.
- Kael North: observation, system logic, restraint, institutional pressure.
