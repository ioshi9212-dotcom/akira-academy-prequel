# POV Switch Mode

Loads only when the latest player command contains `POV:` or `пов:`.

Purpose: temporarily shift the scene focus from Akira to another named character, while time continues normally.

Rules:
- Default gameplay focus is Akira unless POV mode is explicitly requested.
- In POV mode, the named character is the scene focus for this response.
- The character must stay faithful to their loaded character files.
- Akira may be absent, present in the background, or present as an NPC.
- Akira must not gain knowledge from this POV scene unless she actually saw, heard, was told, or otherwise had a clear source.
- Time, location, relationships, rumors, reputation, story lines and calendar state may change if the scene causes consequences.
- If the next player command does not request POV again, return to normal Akira focus.

Header addition:
`🎥 POV: Ливия · фокус сцены не Акира`

If Akira is not present, use:
`🎥 POV: Ливия · Акира этого не видит напрямую`

Bottom blocks should be for the current POV character:
- Что можно сделать
- Что POV-персонаж мог бы сказать
- Мысли POV-персонажа

Do not use POV mode as a technical summary. It must be a normal prose scene.
