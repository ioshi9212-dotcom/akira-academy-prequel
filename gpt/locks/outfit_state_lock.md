# Disabled redundant lock

This file is intentionally inactive in the cleanup branch.

Outfit source rules now live in the main scene rules digest and current_state/inventory_state.

Keeping this as a separate required lock duplicated prompt pressure and contributed to style drift, so `response_size_guard_runtime_patch.py` filters it out of required_files.
