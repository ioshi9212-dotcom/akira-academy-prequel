from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.assembler import build_scene_packet
from app.loader import (
    DATA,
    create_session as create_session_files,
    deep_merge,
    ensure_session,
    exists,
    list_data_files,
    read_json,
    read_text,
    read_yaml,
    safe_session_id,
    seed_data,
    write_json,
    write_yaml,
)
from app.models import (
    ApplyTurnResultRequest,
    ApplyTurnResultResponse,
    CreateSessionRequest,
    RequiredFilesChunk,
    RequiredFilesManifest,
    ScenePacket,
    SessionInfo,
    TurnRequest,
)
from app.prompt_builder import build_prompt_preview

APP_NAME = "Akira Academy Prequel Clean API"
RESERVED_SESSION_IDS = {"default", "new", "none", "null", "undefined", "session"}

app = FastAPI(title=APP_NAME, version="1.0.0-clean", servers=[{"url": "https://akira-academy-prequel-production.up.railway.app"}])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_session_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value or value.lower() in RESERVED_SESSION_IDS:
        value = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    return safe_session_id(value)


class FileResponse(BaseModel):
    path: str
    content: str


class JsonResponse(BaseModel):
    path: str
    data: Any


@app.on_event("startup")
def startup() -> None:
    seed_data()


@app.get("/health")
def health() -> dict[str, Any]:
    seed_data()
    return {
        "status": "ok",
        "app": APP_NAME,
        "data_dir": str(DATA),
        "volume_seeded": (DATA / ".seeded").exists(),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": APP_NAME,
        "health": "/health",
        "createSession": "POST /api/v1/sessions",
        "getSessionContext": "GET /api/v1/sessions/{session_id}/context",
        "getSessionTurnContract": "POST /api/v1/sessions/{session_id}/turn-contract",
        "getRequiredFilesManifest": "POST /api/v1/sessions/{session_id}/required-files-manifest",
        "getRequiredFilesChunk": "POST /api/v1/sessions/{session_id}/required-files-chunk",
        "buildScenePacket": "POST /api/v1/sessions/{session_id}/scene-packet",
        "applyTurnResult": "POST /api/v1/sessions/{session_id}/apply-turn-result",
    }


@app.post("/api/v1/sessions", response_model=SessionInfo)
def create_session(payload: CreateSessionRequest = CreateSessionRequest()) -> SessionInfo:
    sid = normalize_session_id(payload.session_id)
    meta = create_session_files(sid, title=payload.title or "Academy Prequel Session", reset=payload.reset)
    return SessionInfo(
        session_id=sid,
        title=meta.get("title"),
        created_at=meta.get("created_at") or now(),
        updated_at=meta.get("updated_at") or now(),
        context_url=f"/api/v1/sessions/{sid}/context",
        turn_contract_url=f"/api/v1/sessions/{sid}/turn-contract",
    )


@app.get("/api/v1/sessions/{session_id}/context")
def get_session_context(session_id: str) -> dict[str, Any]:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    return {
        "session_id": sid,
        "current_state": read_json("state/current_state.json", sid, default={}),
        "calendar_runtime": read_json("state/calendar_runtime.json", sid, default={}),
        "state_index": read_yaml("state/index.yaml", sid, default={}),
        "character_index": read_yaml("characters/index.yaml", sid, default={}),
        "location_index": read_yaml("locations/index.yaml", sid, default={}),
        "assembly_chain": read_yaml("assembly/scene_assembly_chain.yaml", sid, default={}),
        "note": "Context is compact. Use scene-packet/required-files for actual scene rendering.",
    }


@app.post("/api/v1/sessions/{session_id}/scene-packet", response_model=ScenePacket)
def build_scene_packet_endpoint(session_id: str, request: TurnRequest = TurnRequest()) -> ScenePacket:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    packet = build_scene_packet(sid, request.user_input, request.mode)
    packet["prompt_preview"] = build_prompt_preview(packet)
    # Keep gameplay Action responses compact: full file contents are available
    # through required-files-chunk for technical/diagnostic mode only.
    packet["loaded_files"] = {}
    return ScenePacket(**packet)


@app.post("/api/v1/sessions/{session_id}/turn-contract")
def get_turn_contract(session_id: str, request: TurnRequest = TurnRequest()) -> dict[str, Any]:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    packet = build_scene_packet(sid, request.user_input, request.mode)
    return {
        "session_id": sid,
        "mode": request.mode,
        "packet_status": packet["packet_status"],
        "current_frame": packet["current_frame"],
        "rendered_header": packet["rendered_header"],
        "player_input": packet["player_input"],
        "required_files": packet["required_files"],
        "missing_files": packet["missing_files"],
        "full_character_ids": packet["full_character_ids"],
        "reference_character_ids": packet["reference_character_ids"],
        "location_ids_loaded": packet["location_ids_loaded"],
        "relationship_pairs_loaded": packet["relationship_pairs_loaded"],
        "rule": "Load required files before scene. GPT must render from scene_packet and loaded content only.",
    }


@app.post("/api/v1/sessions/{session_id}/required-files-manifest", response_model=RequiredFilesManifest)
def get_required_files_manifest(session_id: str, request: TurnRequest = TurnRequest()) -> RequiredFilesManifest:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    packet = build_scene_packet(sid, request.user_input, request.mode)
    return RequiredFilesManifest(
        session_id=sid,
        packet_status=packet["packet_status"],
        required_files=packet["required_files"],
        missing_files=packet["missing_files"],
        full_character_ids=packet["full_character_ids"],
        reference_character_ids=packet["reference_character_ids"],
        location_ids_loaded=packet["location_ids_loaded"],
        relationship_pairs_loaded=packet["relationship_pairs_loaded"],
    )


@app.post("/api/v1/sessions/{session_id}/required-files-chunk", response_model=RequiredFilesChunk)
def get_required_files_chunk(
    session_id: str,
    request: TurnRequest = TurnRequest(),
    chunk_index: int = Query(0, ge=0),
    chunk_size: int = Query(6, ge=1, le=20),
) -> RequiredFilesChunk:
    sid = safe_session_id(session_id)
    ensure_session(sid)
    packet = build_scene_packet(sid, request.user_input, request.mode)
    paths = packet["required_files"]
    start = chunk_index * chunk_size
    selected = paths[start:start + chunk_size]
    files: dict[str, str] = {}
    missing: list[str] = []
    for path in selected:
        if exists(path, sid):
            files[path] = read_text(path, sid)
        else:
            missing.append(path)
    next_index = chunk_index + 1 if start + chunk_size < len(paths) else None
    return RequiredFilesChunk(
        session_id=sid,
        chunk_index=chunk_index,
        next_chunk_index=next_index,
        has_more=next_index is not None,
        files=files,
        missing_files=missing,
    )


@app.post("/api/v1/sessions/{session_id}/apply-turn-result", response_model=ApplyTurnResultResponse)
def apply_turn_result(session_id: str, request: ApplyTurnResultRequest) -> ApplyTurnResultResponse:
    sid = safe_session_id(session_id)
    ensure_session(sid)

    if request.technical:
        return ApplyTurnResultResponse(status="technical_no_state_change", notes=["Technical turn ignored."])

    changed: list[str] = []
    notes: list[str] = []

    def update_json_file(path: str, changes: dict[str, Any]) -> None:
        if not changes:
            return
        old = read_json(path, sid, default={}) or {}
        new = deep_merge(old, changes)
        if new != old:
            if not request.dry_run:
                write_json(path, new, sid)
            changed.append(path)

    def update_yaml_file(path: str, changes: dict[str, Any]) -> None:
        if not changes:
            return
        old = read_yaml(path, sid, default={}) or {}
        new = deep_merge(old, changes)
        if new != old:
            if not request.dry_run:
                write_yaml(path, new, sid)
            changed.append(path)

    update_json_file("state/current_state.json", request.current_state_changes)
    update_json_file("state/calendar_runtime.json", request.calendar_runtime_changes)
    update_json_file("state/inventory_state.json", request.inventory_changes)
    update_json_file("state/reputation_state.json", request.reputation_changes)
    update_json_file("state/rumors_state.json", request.rumors_changes)
    update_json_file("state/power_state.json", request.power_changes)
    update_json_file("state/akira_progress_state.json", request.akira_progress_changes)

    for cid, changes in request.character_memory_changes.items():
        update_json_file(f"state/character_memory/{cid}.json", changes)

    for pair_id, changes in request.relationship_pair_changes.items():
        # Pair id must already be exact. This prevents recreating global relationships.json.
        if "__" not in pair_id:
            notes.append(f"Skipped unsafe pair id: {pair_id}")
            continue
        path = f"state/relationship_pairs/{pair_id}.json"
        update_json_file(path, changes)

    return ApplyTurnResultResponse(
        status="applied" if changed else "no_changes_detected",
        changed_files=changed,
        notes=notes,
    )


@app.get("/api/v1/files")
def list_files() -> dict[str, Any]:
    return {"files": list_data_files()}


@app.get("/api/v1/files/{file_path:path}", response_model=FileResponse)
def get_file(file_path: str) -> FileResponse:
    return FileResponse(path=file_path, content=read_text(file_path))


@app.get("/api/v1/json/{file_path:path}", response_model=JsonResponse)
def get_json(file_path: str) -> JsonResponse:
    try:
        data = json.loads(read_text(file_path))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    return JsonResponse(path=file_path, data=data)
