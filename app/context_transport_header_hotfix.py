"""Runtime header/footer hotfix v19.

Keeps runtime simple, but serves a minimal GPT-compatible OpenAPI schema.
The gameplay API routes stay unchanged; only /openapi.json is simplified for
Custom GPT Actions import.
"""
from __future__ import annotations

try:
    import app.calendar_context_runtime_patch as calendar_patch  # noqa: F401
except Exception:
    calendar_patch = None
try:
    import app.lore_context_runtime_patch as lore_patch  # noqa: F401
except Exception:
    lore_patch = None
try:
    import app.context_cleanup_runtime_patch as cleanup_patch  # noqa: F401
except Exception:
    cleanup_patch = None

import app.runtime_speed_patch as speed_patch  # noqa: F401
import app.context_transport_runtime_patch as rt
from app.runtime_speed_patch import app
from app import compact as base

rt.MINIMAL_LOCK_FILES = ["gpt/locks/runtime_scene_rules_digest.md"]

try:
    import app.scene_output_format_runtime_patch as scene_format_patch  # noqa: F401
except Exception:
    scene_format_patch = None

app.version = "0.3.42-gpt-compatible-openapi-minimal"

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — strict Academy scene format
Use old Academy header/footer. Energy should be visually/physically felt when relevant: cold, heat, sound, vibration, pressure, metal tremor, trajectory shift. Personal energy is in character cards, not in separate per-type files.
"""


def _object_schema() -> dict:
    return {"type": "object", "additionalProperties": True}


def _response(description: str = "Successful Response") -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": _object_schema(),
            }
        },
    }


def _session_path_param() -> dict:
    return {
        "name": "session_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string"},
    }


def _minimal_gpt_openapi() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Akira Academy Prequel Actions",
            "version": app.version,
        },
        "servers": [{"url": base.BASE_URL}],
        "paths": {
            "/health": {
                "get": {
                    "operationId": "health",
                    "summary": "Check API health and runtime version",
                    "responses": {"200": _response("API health status")},
                }
            },
            "/api/v1/sessions": {
                "post": {
                    "operationId": "createSession",
                    "summary": "Create a new gameplay session",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "session_id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "reset": {"type": "boolean"},
                                    },
                                    "additionalProperties": False,
                                }
                            }
                        },
                    },
                    "responses": {"200": _response("Created session")},
                }
            },
            "/api/v1/sessions/{session_id}/context": {
                "get": {
                    "operationId": "getSessionContext",
                    "summary": "Get compact context for a session",
                    "parameters": [_session_path_param()],
                    "responses": {"200": _response("Compact session context")},
                }
            },
            "/api/v1/sessions/{session_id}/turn-contract": {
                "get": {
                    "operationId": "getSessionTurnContract",
                    "summary": "Get turn contract, required files and output rules",
                    "parameters": [_session_path_param()],
                    "responses": {"200": _response("Turn contract")},
                }
            },
            "/api/v1/sessions/{session_id}/required-files-manifest": {
                "get": {
                    "operationId": "getRequiredFilesManifest",
                    "summary": "Get required files manifest and chunk count",
                    "parameters": [_session_path_param()],
                    "responses": {"200": _response("Required files manifest")},
                }
            },
            "/api/v1/sessions/{session_id}/required-files-chunk": {
                "get": {
                    "operationId": "getRequiredFilesChunk",
                    "summary": "Get one chunk of required file contents",
                    "parameters": [
                        _session_path_param(),
                        {
                            "name": "chunk_index",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 0},
                        },
                        {
                            "name": "max_chars",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 30000},
                        },
                        {
                            "name": "max_items",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 3},
                        },
                    ],
                    "responses": {"200": _response("Required files chunk")},
                }
            },
            "/api/v1/sessions/{session_id}/required-files-bundle": {
                "get": {
                    "operationId": "getRequiredFilesBundle",
                    "summary": "Backward-compatible required files chunk endpoint",
                    "parameters": [
                        _session_path_param(),
                        {
                            "name": "chunk_index",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 0},
                        },
                        {
                            "name": "max_chars",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 30000},
                        },
                        {
                            "name": "max_items",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 3},
                        },
                    ],
                    "responses": {"200": _response("Required files chunk")},
                }
            },
            "/api/v1/sessions/{session_id}/apply-turn-result": {
                "post": {
                    "operationId": "applyTurnResult",
                    "summary": "Apply meaningful scene changes to session state",
                    "parameters": [_session_path_param()],
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "turn_file": {"type": "string"},
                                        "data": _object_schema(),
                                        "dry_run": {"type": "boolean", "default": False},
                                        "visible_scene_text": {"type": "string"},
                                    },
                                    "additionalProperties": True,
                                }
                            }
                        },
                    },
                    "responses": {"200": _response("Apply result")},
                }
            },
        },
    }


def _stable_openapi() -> dict:
    return _minimal_gpt_openapi()


app.openapi_schema = None
app.openapi = _stable_openapi  # type: ignore[method-assign]
