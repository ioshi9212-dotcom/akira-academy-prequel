# Lore Usage Lock — Academy 1198

Use `canon_lore/` as the active lore source.

Old `canon/` files may exist as archive, but they do not override `canon_lore/` unless explicitly loaded.

## Required behavior

- Always keep `canon_lore/core/world_background.yaml` as short world background.
- Always keep `canon_lore/academy/academy_background.yaml` as Academy background.
- Always keep `canon_lore/hidden/hidden_lore_policy.yaml` as a leak-prevention rule.
- Load `canon_lore/academy/academy_full.yaml` for Academy rules, uniform, checks, discipline, ratings, training, medblock, staff, technology limits.
- Load `canon_lore/academy/academy_locations.yaml` for campus look, routes and places.
- Load world files only by topic: energy, Echo, Kairos, continents/sectors.
- Character behavior still comes from character cards first.
- Hidden lore is author/engine knowledge, not automatic NPC knowledge.

## Hidden lore limit

Do not auto-load long hidden relationship files only because two characters are in the same scene.
Use character cards, current_state and knowledge_state for what characters can feel, know or suspect.

## Academy technology tone

Academy technology is modern-realistic:
- ordinary devices, tablets, cameras, radios, key-cards, medical tools;
- limited energy/safety sensors in relevant zones;
- people do the actual observation and judgement.

Do not write super-scanners, total AI surveillance, holographic sci-fi, instant organ scans, or devices that reveal hidden lore.

## V2/V3 visibility transfer

- Narration may describe only what POV perceives or what the scene established.
- NPC dialogue may reveal facts only if the NPC knows them and has a reason to say them.
- Calendar/canon/relationship metadata are engine facts, not character knowledge.
- Hidden relationship tension may appear as pause, irritation, attention, body reaction, or unexplained discomfort, but must not be explained as bond/reincarnation/past love.
- If source is absent, write suspicion/question/mistake, not fact.

