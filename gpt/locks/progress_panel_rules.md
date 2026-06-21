# Disabled redundant lock

This file is intentionally inactive in the cleanup branch.

Progress and relationship score mechanics now live in:
- `state/akira_progress_state.json`
- `state/relationship_score_panel.json`
- compact fields inside `app/response_size_guard_runtime_patch.py`
- the main scene rules digest for visible block naming.

Keeping this file as a full required lock duplicated style rules and made scenes too mechanical, so `response_size_guard_runtime_patch.py` filters it out of required_files.
