from app.context_transport_header_hotfix import app

try:
    import app.local_lmstudio_runtime_patch as local_lmstudio_runtime_patch  # noqa: F401
except Exception:
    local_lmstudio_runtime_patch = None  # type: ignore[assignment]
