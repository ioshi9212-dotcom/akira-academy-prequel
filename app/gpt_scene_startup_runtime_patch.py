"""One-call startup action for Custom GPT gameplay.

Some Custom GPT runs refuse before calling the multi-step startup chain. This
endpoint gives the model a single obvious first tool: beginSceneSetup. It creates
(or reuses) a session and returns the complete scene assembly packet needed to
start gameplay: context, turn contract, manifest and first required-files chunk.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.context_transport_runtime_patch import app
from app import compact as base
import app.compact_context_patch as ccp


class BeginSceneSetupRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Optional existing session_id. If missing, a new session is created.",
    )
    title: str | None = Field(default=None)
    max_chars: int = Field(default=30000)
    max_items: int = Field(default=3)


def _as_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _create_or_reuse_session(request: BeginSceneSetupRequest) -> str:
    base.seed()
    if request.session_id:
        sid = base.safe_session_id(request.session_id)
        try:
            base.ensure_session(sid)
            return sid
        except HTTPException:
            # If the GPT provides a stale session id, create it from seed state
            # instead of failing before gameplay can start.
            pass
    else:
        sid = base.safe_session_id(f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}")

    session_path = base.session_dir(sid)
    session_path.mkdir(parents=True, exist_ok=True)
    base.copy_missing(base.DATA / "state", session_path / "state")
    meta = {
        "session_id": sid,
        "title": request.title or "Academy Prequel Session",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    (session_path / "session.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sid


def _turn_contract(session_id: str) -> Any:
    endpoint = getattr(ccp, "session_turn_contract_with_prompt_preview", None)
    if callable(endpoint):
        return endpoint(session_id)
    return base.session_turn_contract(session_id)


@app.post("/api/v1/scene/startup", operation_id="beginSceneSetup")
def begin_scene_setup(request: BeginSceneSetupRequest = BeginSceneSetupRequest()):
    sid = _create_or_reuse_session(request)

    context = _as_plain(base.context_payload(sid))
    contract = _as_plain(_turn_contract(sid))
    manifest = _as_plain(ccp.get_required_files_manifest(sid))
    first_chunk = _as_plain(
        ccp.get_required_files_chunk(
            sid,
            chunk_index=0,
            max_chars=request.max_chars,
            max_items=request.max_items,
        )
    )

    return {
        "status": "ready",
        "session_id": sid,
        "usage_rule": (
            "Use this response as the scene assembly packet. Do not answer with 'no access to game state'. "
            "If first_chunk.has_more is true, continue with getRequiredFilesChunk using next_chunk_index until has_more=false, then render gameplay."
        ),
        "current_state": context.get("current_state") if isinstance(context, dict) else None,
        "active_character_ids": contract.get("active_character_ids") if isinstance(contract, dict) else [],
        "nearby_character_ids": contract.get("nearby_character_ids") if isinstance(contract, dict) else [],
        "context": context,
        "turn_contract": contract,
        "required_files_manifest": manifest,
        "first_required_files_chunk": first_chunk,
        "next_required_action": (
            "call getRequiredFilesChunk with next_chunk_index"
            if isinstance(first_chunk, dict) and first_chunk.get("has_more")
            else "render_gameplay_scene"
        ),
    }
