# Akira Academy Prequel

## Assistant maintenance rules

This repository must stay clean and source-driven.

### Do not create rule-over-rule layers

Do not add new files or folders that act as runtime patches, locks, duplicated scene contracts, hidden override rules, or emergency prompt fixes.

Forbidden patterns:
- `gpt/locks/*`
- `gpt/director/*`
- `engine/*` as extra gameplay rules
- `app/*runtime_patch.py`
- `app/*hotfix.py` for scene behavior
- extra scene contracts that duplicate `rules/scene_core.md`
- state/update contract files that override normal assembly
- hidden fallback files used by GPT instead of the scene packet

If a rule is weak, edit the existing canonical file instead of adding a new override.

### Canonical places for behavior

- Scene/gameplay rules: `rules/scene_core.md`
- Prompt/chunk protocol: `app/prompt_builder.py`
- Packet assembly and scope: `app/assembler.py`
- API endpoints and state writes: `app/main.py`
- Calendar beats: `calendar/days/*.yaml`
- Location facts and route boundaries: `locations/*.yaml`
- Character voice/facts: `characters/*/main.yaml`
- Session state templates: `state/*.json`

### Calendar rules

Calendar files should describe beat order, active characters, route constraints, and required/forbidden facts.

Do not put ready-to-copy dialogue, prose examples, UI examples, or bottom-panel choices in calendar files.

Avoid keys like:
- `possible_tone`
- `footer_example`
- `player_choice`
- `sample_dialogue`
- `example`
- `good`
- `bad`

If a beat needs player agency, describe the pressure structurally, not as finished options.

### Prompt and chunks

Gameplay must not rely on a truncated preview alone.

The play flow is:
1. `buildScenePacket`
2. load all `required_files` through chunks
3. render only after required chunks are loaded

If a character is full-loaded, their `display.unknown_name`, appearance anchor, speech profile, and forbidden facts must reach the renderer.

### State writes

Do not infer state transitions from rendered prose.

`applyTurnResult` should save only structured, meaningful changes:
- location/beat changes
- character memory
- relationship pair changes
- body/energy/inventory consequences
- rumors/reputation
- open threads
- future hooks

Never save bottom UI options as completed actions.

### Descriptor safety

If POV does not know a name, use only:
- `display.unknown_name` from the full character card
- a descriptor provided by `scene_packet`
- a neutral descriptor based on visible facts

Do not invent hair color, age, status, rank, relationship, or role.

### Maintenance principle

Do not patch symptoms with more rules. Find the canonical source, remove the conflict, and keep the pipeline simple.
