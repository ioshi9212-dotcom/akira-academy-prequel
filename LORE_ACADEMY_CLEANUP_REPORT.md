# Lore + Academy Cleanup Report

## Scope

Cleaned active lore for Academy 1198. This pass focuses on `canon_lore/`, Academy base/rules/locations, hidden-lore loading limits, and the start state conflict caused by the new 15 August opening.

## Main changes

- Rebuilt `canon_lore/index.yaml` as compact active index.
- Rewrote `world_background.yaml` as short public base.
- Rewrote `academy_background.yaml` with:
  - Academy identity;
  - visual style;
  - uniform rules;
  - modern-realistic technology level;
  - explicit ban on super-scanners / total AI / hidden-lore machines.
- Rewrote `academy_full.yaml` as compact rules/systems file.
- Rewrote `academy_locations.yaml` as compact campus map.
- Rewrote compact `energy_system`, `echo`, `kairos`, `continents` files.
- Removed `canon_lore/hidden/raiden_akira_bond.yaml` from active package.
- Updated lore runtime patch so hidden relationship lore is no longer auto-loaded when Akira and Raiden are in one scene.
- Updated lore lock and runtime digest with modern-realistic Academy tech rule.
- Updated `state/current_state.json` to match the corrected 15 August start: Ray's car / arrival dropoff, not immediate court.
- Updated `state/location_registry.md` to use new active location ids.

## Active hidden policy now

Only `canon_lore/hidden/hidden_lore_policy.yaml` is always loaded. It prevents leaks. Long hidden truths should not be read in normal gameplay unless manually requested for development/debug.

## Technology tone

Academy technology should feel like current-world modern tech plus limited energy-safety tools:

- allowed: tablets, computers, cameras at key points, radios, key-cards, ordinary medical devices, pульсометры, timers, simple zone sensors;
- forbidden: body scan lines, instant organ scans, omniscient panels, total AI surveillance, devices that reveal hidden lore.

## Validation

YAML files parse correctly. Python files compile.
