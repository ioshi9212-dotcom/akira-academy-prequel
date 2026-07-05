"""Runtime header/footer hotfix v29 scene packet rendered header.

Keeps runtime simple, serves a minimal GPT-compatible OpenAPI schema,
enables living NPC memory, explicit non-Akira POV mode, scene format rules,
and transport-only size-guard context/turn-contract endpoints.

Important: OpenAPI must expose TurnContractWithPromptPreview schema because
the smoke test checks that exact component name.
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
try:
    import app.npc_living_runtime_patch as npc_living_patch  # noqa: F401
except Exception:
    npc_living_patch = None
try:
    import app.pov_switch_runtime_patch as pov_switch_patch  # noqa: F401
except Exception:
    pov_switch_patch = None
try:
    import app.response_size_guard_runtime_patch as response_size_guard_patch  # noqa: F401
except Exception:
    response_size_guard_patch = None
try:
    import app.scene_packet_runtime_patch as scene_packet_patch  # noqa: F401
except Exception:
    scene_packet_patch = None

app.version = "0.3.75-scene-packet-rendered-header-v4"

rt.MEDIUM_STYLE_FORMAT_DIGEST = """
## Medium scene style digest — strict Academy scene format
Use old Academy header/footer. Energy should be visually/physically felt when relevant: cold, heat, sound, vibration, pressure, metal tremor, trajectory shift. Personal energy is in character cards, not in separate per-type files.
"""


def _object_schema(properties: dict | None = None, *, required: list[str] | None = None) -> dict:
    schema = {
        "type": "object",
        "properties": properties or {},
        "additionalProperties": True,
    }
    if required:
        schema["required"] = required
    return schema


def _array_string() -> dict:
    return {"type": "array", "items": {"type": "string"}}


def _components_schemas() -> dict:
    return {
        "TurnContractWithPromptPreview": _object_schema(
            {
                "session_id": {"type": "string"},
                "mode": {"type": "string"},
                "active_character_ids": _array_string(),
                "nearby_character_ids": _array_string(),
                "required_files": _array_string(),
                "load_if_needed_files": _array_string(),
                "reference_only_files": _array_string(),
                "required_file_tiers": _object_schema(),
                "output_format_contract": _object_schema(),
                "required_checks_before_answer": _array_string(),
                "knowledge_table": _object_schema(),
                "inventory_contract": _object_schema(),
                "relationship_context": _object_schema(),
                "story_context": _object_schema(),
                "prompt_preview": {"type": "string"},
                "prompt_preview_usage": {"type": "string"},
                "usage_note": {"type": "string"},
            },
            required=["session_id", "required_files", "prompt_preview"],
        ),
        "SizeGuardContextResponse": _object_schema(
            {
                "session_id": {"type": "string"},
                "mode": {"type": "string"},
                "current_state": _object_schema(),
                "active_character_ids": _array_string(),
                "nearby_character_ids": _array_string(),
                "required_files": _array_string(),
                "load_if_needed_files": _array_string(),
                "reference_only_files": _array_string(),
                "required_file_tiers": _object_schema(),
                "usage_note": {"type": "string"},
            },
            required=["session_id"],
        ),
        "SessionResponse": _object_schema(
            {
                "session_id": {"type": "string"},
                "title": {"type": "string"},
                "created_at": {"type": "string"},
                "updated_at": {"type": "string"},
            },
            required=["session_id"],
        ),
        "HealthResponse": _object_schema(
            {
                "status": {"type": "string"},
                "app": {"type": "string"},
                "version": {"type": "string"},
                "public_base_url": {"type": "string"},
            }
        ),
        "RequiredFilesManifestResponse": _object_schema(
            {
                "session_id": {"type": "string"},
                "required_files": _array_string(),
                "files": {"type": "array", "items": _object_schema()},
                "missing_files": _array_string(),
                "chunks_total": {"type": "integer"},
                "loaded_count": {"type": "integer"},
                "missing_count": {"type": "integer"},
            }
        ),
        "RequiredFilesChunkResponse": _object_schema(
            {
                "session_id": {"type": "string"},
                "required_files": _array_string(),
                "chunk_index": {"type": "integer"},
                "chunks_total": {"type": "integer"},
                "has_more": {"type": "boolean"},
                "next_chunk_index": {"type": "integer"},
                "loaded_files": {"type": "array", "items": _object_schema()},
                "missing_files": _array_string(),
                "loaded_count": {"type": "integer"},
                "missing_count": {"type": "integer"},
                "total_loaded_parts": {"type": "integer"},
            }
        ),
        "BuildScenePacketRequest": _object_schema(
            {
                "player_input": {"type": "string"},
                "mode": {"type": "string", "default": "game_turn"},
                "include_sources": {"type": "boolean", "default": False},
                "include_diagnostics": {"type": "boolean", "default": True},
                "include_source_index": {"type": "boolean", "default": True},
                "max_file_chars": {"type": "integer", "default": 12000},
                "max_total_chars": {"type": "integer", "default": 70000},
            }
        ),
        "ScenePacketResponse": _object_schema(
            {
                "session_id": {"type": "string"},
                "mode": {"type": "string"},
                "usage_note": {"type": "string"},
                "scene_packet": _object_schema(),
                "loaded_files": {"type": "array", "items": _object_schema()},
                "missing_files": _array_string(),
                "diagnostics": _object_schema(),
            },
            required=["session_id", "scene_packet"],
        ),
        "ApplyTurnResultResponse": _object_schema(
            {
                "status": {"type": "string"},
                "session_id": {"type": "string"},
                "changed_files": _array_string(),
                "visible_scene_text": {"type": "string"},
                "final_scene_text": {"type": "string"},
            }
        ),
    }


def _response_ref(description: str, schema_name: str) -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"},
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


def _chunk_query_params() -> list[dict]:
    return [
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
    ]


def _minimal_gpt_openapi() -> dict:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Akira Academy Prequel Actions",
            "version": app.version,
        },
        "servers": [{"url": base.BASE_URL}],
        "components": {
            "schemas": _components_schemas(),
        },
        "paths": {
            "/health": {
                "get": {
                    "operationId": "health",
                    "summary": "Check API health and runtime version",
                    "responses": {"200": _response_ref("API health status", "HealthResponse")},
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
                                "schema": _object_schema(
                                    {
                                        "session_id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "reset": {"type": "boolean"},
                                    }
                                )
                            }
                        },
                    },
                    "responses": {"200": _response_ref("Created session", "SessionResponse")},
                }
            },
            "/api/v1/sessions/{session_id}/context": {
                "get": {
                    "operationId": "getSessionContext",
                    "summary": "Get size-guard compact context for a session",
                    "parameters": [_session_path_param()],
                    "responses": {"200": _response_ref("Compact session context", "SizeGuardContextResponse")},
                }
            },
            "/api/v1/sessions/{session_id}/turn-contract": {
                "get": {
                    "operationId": "getSessionTurnContract",
                    "summary": "Get size-guard compact turn contract",
                    "parameters": [_session_path_param()],
                    "responses": {"200": _response_ref("Turn contract", "TurnContractWithPromptPreview")},
                }
            },
            "/api/v1/sessions/{session_id}/required-files-manifest": {
                "get": {
                    "operationId": "getRequiredFilesManifest",
                    "summary": "Get required files manifest and chunk count",
                    "parameters": [_session_path_param()],
                    "responses": {"200": _response_ref("Required files manifest", "RequiredFilesManifestResponse")},
                }
            },
            "/api/v1/sessions/{session_id}/required-files-chunk": {
                "get": {
                    "operationId": "getRequiredFilesChunk",
                    "summary": "Get one chunk of required file contents",
                    "parameters": [_session_path_param()] + _chunk_query_params(),
                    "responses": {"200": _response_ref("Required files chunk", "RequiredFilesChunkResponse")},
                }
            },
            "/api/v1/sessions/{session_id}/required-files-bundle": {
                "get": {
                    "operationId": "getRequiredFilesBundle",
                    "summary": "Backward-compatible required files chunk endpoint",
                    "parameters": [_session_path_param()] + _chunk_query_params(),
                    "responses": {"200": _response_ref("Required files chunk", "RequiredFilesChunkResponse")},
                }
            },
            "/api/v1/sessions/{session_id}/build-scene-packet": {
                "post": {
                    "operationId": "buildScenePacket",
                    "summary": "Build one compact scene packet for the next gameplay scene",
                    "parameters": [_session_path_param()],
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/BuildScenePacketRequest"}
                            }
                        },
                    },
                    "responses": {"200": _response_ref("Compact scene packet", "ScenePacketResponse")},
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
                                "schema": _object_schema(
                                    {
                                        "turn_file": {"type": "string"},
                                        "data": _object_schema(),
                                        "dry_run": {"type": "boolean", "default": False},
                                        "visible_scene_text": {"type": "string"},
                                    }
                                )
                            }
                        },
                    },
                    "responses": {"200": _response_ref("Apply result", "ApplyTurnResultResponse")},
                }
            },
        },
    }


def _stable_openapi() -> dict:
    return _minimal_gpt_openapi()


app.openapi_schema = None
app.openapi = _stable_openapi  # type: ignore[method-assign]
