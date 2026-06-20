# Lock: current outfit versus received uniform

This lock fixes a recurring state bug: the engine sometimes treats issued Academy uniform as currently worn clothing, or treats optional uniform replacements as default clothing.

## Rule

Received uniform is not the same as worn uniform.

Girls' standard Academy uniform:
- burgundy Academy blazer or jacket with emblem;
- black shirt;
- burgundy skirt.

Optional replacements are allowed only when explicitly saved in current_state, inventory_state, or visible scene state.

Use separate state concepts:

```json
{
  "current_outfit": "what Akira is actually wearing right now",
  "received_uniform": ["burgundy academy blazer", "black shirt", "burgundy skirt"],
  "uniform_worn": false,
  "carried_items": ["phone", "bag", "received uniform if carried"]
}
```

## Writing visible_inventory

Do not write an optional replacement as Akira's default uniform unless saved state explicitly says she wears that replacement.

When the Academy uniform is only issued, write this:

```json
"текущая одежда: обычная спортивная одежда"
"полученная форма Академии: бордовый пиджак, чёрная рубашка и бордовая юбка, ещё не надета"
```

When the Academy uniform is actually worn and no replacement is saved, write this:

```json
"форма Академии: бордовый пиджак, чёрная рубашка, бордовая юбка"
```

## Apply-turn-result requirement

When clothes or uniform status changes, current_state_changes must include explicit fields:

```json
{
  "current_state_changes": {
    "current_outfit": "...",
    "received_uniform": ["..."],
    "uniform_worn": false,
    "visible_inventory": ["..."]
  }
}
```

## Gameplay rendering

The header and prose must use current_outfit for what is on the body.

The received_uniform may appear as an object, carried item, folded clothing, package, bag content, or nearby item, but not as worn clothing unless uniform_worn is true.

If uniform_worn is true and current_outfit does not specify a replacement, render the standard girls' uniform: burgundy blazer or jacket, black shirt, burgundy skirt.

## Player control

Do not change Akira into the uniform unless:
- the player says she changes clothes;
- the scene explicitly applies a uniform change;
- saved current_state says uniform_worn is true.

Do not choose optional uniform replacements for Akira unless the player or current_state explicitly chose them.
