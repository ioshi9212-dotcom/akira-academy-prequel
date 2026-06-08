from app.compact_context_patch import app, patch_after_routes
import app.session_routes  # noqa: F401

patch_after_routes()
