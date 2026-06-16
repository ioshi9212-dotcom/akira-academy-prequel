"""Serve the stable Custom GPT Actions schema from /openapi.json.

FastAPI auto-generates operationIds like root__get and
session_context_api_v1_sessions__session_id__context_get when routes do not
explicitly set operation_id. Custom GPT then sees the wrong tool names and stops
before the required session startup flow.

This patch makes the deployed app expose the hand-written GPT Actions schema
from gpt/actions_schema_minimal_with_bundle_openapi_3_1.json as its live
/openapi.json, while keeping all actual runtime routes unchanged.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.context_transport_runtime_patch import app
from app import compact as base

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "gpt" / "actions_schema_minimal_with_bundle_openapi_3_1.json"


def _inject_begin_scene_setup(schema: dict[str, Any]) -> None:
    paths = schema.setdefault("paths", {})
    paths["/api/v1/scene/startup"] = {
        "post": {
            "operationId": "beginSceneSetup",
            "summary": "One-call startup action for gameplay scene assembly",
            "description": (
                "Use this first for any gameplay start/continue command such as 'начнем'. "
                "It creates or reuses a session and returns context, turn contract, required-files manifest and first chunk."
            ),
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "title": {"type": "string"},
                                "max_chars": {"type": "integer", "default": 30000},
                                "max_items": {"type": "integer", "default": 3},
                            },
                            "additionalProperties": False,
                        }
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Scene assembly packet",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "session_id": {"type": "string"},
                                    "usage_rule": {"type": "string"},
                                    "current_state": {"type": "object", "additionalProperties": True},
                                    "active_character_ids": {"type": "array", "items": {"type": "string"}},
                                    "nearby_character_ids": {"type": "array", "items": {"type": "string"}},
                                    "context": {"type": "object", "additionalProperties": True},
                                    "turn_contract": {"type": "object", "additionalProperties": True},
                                    "required_files_manifest": {"type": "object", "additionalProperties": True},
                                    "first_required_files_chunk": {"type": "object", "additionalProperties": True},
                                    "next_required_action": {"type": "string"},
                                },
                                "required": ["status", "session_id", "current_state", "turn_contract", "required_files_manifest", "first_required_files_chunk"],
                                "additionalProperties": True,
                            }
                        }
                    },
                }
            },
        }
    }


def _load_stable_schema() -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = copy.deepcopy(schema)

    # Keep the schema URL aligned with the current deployment env.
    schema["servers"] = [{"url": base.BASE_URL}]

    info = schema.setdefault("info", {})
    info["title"] = "Akira Academy Prequel Actions"
    info["version"] = getattr(app, "version", info.get("version", "runtime"))

    _inject_begin_scene_setup(schema)
    return schema


def stable_custom_gpt_openapi() -> dict[str, Any]:
    if getattr(app, "openapi_schema", None):
        return app.openapi_schema  # type: ignore[return-value]
    app.openapi_schema = _load_stable_schema()
    return app.openapi_schema  # type: ignore[return-value]


app.openapi_schema = None
app.openapi = stable_custom_gpt_openapi  # type: ignore[method-assign]
