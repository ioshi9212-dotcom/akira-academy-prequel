# Disabled redundant lock

This file is intentionally inactive in the cleanup branch.

Scene density and bottom-choice rules were folded into `gpt/locks/runtime_scene_rules_digest.md` in a compact form.

Keeping this file as a full required lock made the scene too dry and checklist-like, so `response_size_guard_runtime_patch.py` filters it out of required_files.
