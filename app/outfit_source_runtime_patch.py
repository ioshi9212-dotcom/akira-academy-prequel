from __future__ import annotations

from app.context_transport_runtime_patch import app
import app.context_transport_runtime_patch as rt

_ORIG_BUILD_DIGEST = getattr(rt, "build_scene_context_digest", None)


def build_scene_context_digest_with_outfit_state(session_id: str) -> str:
    text = _ORIG_BUILD_DIGEST(session_id) if callable(_ORIG_BUILD_DIGEST) else ""
    rule = """
## Outfit state rule
- Render clothing only from current_state, inventory_state, or latest visible scene.
- Do not use example clothing from prompt templates as actual clothing.
- If uniform_worn=false, keep Academy uniform out of the worn outfit line.
- If Academy uniform is worn and no variant is saved, use the standard: burgundy Academy blazer, black shirt, burgundy skirt.
- Optional variants require explicit player action or saved current_state.
"""
    return str(text).rstrip() + "\n\n" + rule.strip() + "\n"


rt.build_scene_context_digest = build_scene_context_digest_with_outfit_state
app.version = "0.3.58-outfit-state-rule-v1"
