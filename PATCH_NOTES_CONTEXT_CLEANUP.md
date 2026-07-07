# Patch notes — context cleanup

## Main fixes

- Removed prose-based auto state progression from `app/main.py`.
- `applyTurnResult` now saves only explicit structured changes.
- Rebuilt `app/prompt_builder.py` around required-file chunk protocol.
- Added compact character anchors extracted from loaded full character cards.
- Rewrote `rules/scene_core.md` into one compact rule source without examples.
- Simplified `calendar/days/1198-08-15.yaml`:
  - no ready-made UI choices,
  - no `player_choice`,
  - no exact dialogue examples,
  - no medical hidden details in the start-day calendar,
  - only beat order, route rules, active characters, and boundaries.
- Renamed `player_choice_rule` in `calendar/days/1198-08-16.yaml` to `player_control_rule`.
- Removed `examples` blocks from main character speech profiles.
- Added route/procedure boundaries into relevant location files:
  - `locations/arrival_dropoff.yaml`
  - `locations/back_court_route.yaml`
  - `locations/basketball_court.yaml`
  - `locations/registration_area.yaml`
  - `locations/medblock.yaml`
- Fixed invalid YAML quoting in `openapi.yaml`.
- Removed obsolete rule-over-rule files from this zip tree and listed them in `DELETE_THESE_FILES.md`.

## Required runtime behavior

Gameplay rendering should follow:

1. `scene-packet`
2. `required-files-manifest`
3. `required-files-chunk` until `has_more=false`
4. render scene only after all required chunks are loaded
5. `applyTurnResult` with explicit structured state changes

Do not render scenes from `prompt_preview` alone.
