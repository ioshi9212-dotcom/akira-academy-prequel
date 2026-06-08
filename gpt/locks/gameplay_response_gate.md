# Gameplay Response Gate

Hard gate for every gameplay response.

Do not send a gameplay response unless it includes:

1. Scene header:
   - date
   - time
   - location
   - weather / atmosphere if available
   - Akira state
   - visible inventory / nearby items if relevant

2. Full scene body:
   - not a summary
   - not a recap
   - not a compressed explanation
   - includes environment, NPC/world reaction, dialogue or visible social movement

3. Character fidelity:
   - characters must act strictly according to loaded character files
   - check current relationship state before emotional reactions
   - check knowledge_state before factual claims
   - do not smooth characters into generic friendly NPCs
   - do not make characters obey, forgive, flirt, explain, soften, cooperate or reveal facts if their profile/current state does not support it
   - if a line or reaction contradicts a character card, relationship state or knowledge source, rewrite before sending

4. Scene movement:
   Every scene must move at least one layer:
   - plot
   - relationship
   - knowledge
   - conflict
   - reputation
   - rating
   - body state
   - energy state
   - rumor
   - schedule
   - open thread
   - future hook

5. NPC / relationship check:
   Before writing NPC lines or reactions:
   - check active/nearby characters
   - check relationship state
   - check knowledge_state
   - do not give NPC facts without source
   - do not treat hidden lore as NPC knowledge

6. Bottom block:
   Every gameplay response must include:
   - Что можно сделать:
   - Что Акира могла бы сказать:
   - Мысли Акиры:

7. No visible technical layer:
   Forbidden in gameplay response:
   - "Принял"
   - "Понял"
   - "Сейчас загружаю"
   - "Контракт собран"
   - "Сохраняю state"
   - "Ставлю счёт"
   - "Фиксирую ставку"
   - any API/debug/contract commentary
   - any spoiler of director logic before the scene

8. Save requirement:
   After a meaningful scene, prepare/apply turn result for:
   - current_state if location/time/status changed
   - relationships if interaction changed attitude
   - knowledge_state if someone saw/heard/learned something
   - story_lines/open threads if promise, bet, obligation or future hook appeared
   - reputation/rumors if public reaction happened

9. Rewrite rule:
   If any required section is missing, rewrite before sending.
   Do not apologize inside gameplay.
   Do not explain the mistake.
   Output only the corrected full scene.
