# State split note

`state/current_state.json` remains the active seed for new sessions.
`state/start_state_template.json` is a clean copy of the intended 1198-08-15 start frame for audits/repairs.

Rules:
- Do not use scheduled/delayed ids as active scene participants.
- `scheduled_character_ids` and `delayed_character_ids` are calendar/reference hints only.
- Promote a character to `active_characters` / `nearby_characters` only when the current beat physically reaches them.
- `state/character_memory.json` is intentionally unchanged in this patch; it will be cleaned separately.
