from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    session_id: str | None = None
    title: str | None = None
    reset: bool = False


class SessionInfo(BaseModel):
    session_id: str
    title: str | None = None
    created_at: str
    updated_at: str
    context_url: str
    turn_contract_url: str


class TurnRequest(BaseModel):
    user_input: str = ""
    mode: Literal["play", "technical", "audit"] = "play"


class RequiredFilesManifest(BaseModel):
    session_id: str
    packet_status: str
    required_files: list[str] = Field(default_factory=list)
    missing_files: list[str] = Field(default_factory=list)
    full_character_ids: list[str] = Field(default_factory=list)
    reference_character_ids: list[str] = Field(default_factory=list)
    location_ids_loaded: list[str] = Field(default_factory=list)
    relationship_pairs_loaded: list[str] = Field(default_factory=list)


class RequiredFilesChunk(BaseModel):
    session_id: str
    chunk_index: int
    next_chunk_index: int | None = None
    has_more: bool
    files: dict[str, str] = Field(default_factory=dict)
    missing_files: list[str] = Field(default_factory=list)


class ScenePacket(BaseModel):
    session_id: str
    packet_status: str
    rendered_header: str
    player_input: dict[str, Any] = Field(default_factory=dict)
    current_frame: dict[str, Any] = Field(default_factory=dict)
    required_files: list[str] = Field(default_factory=list)
    loaded_files: dict[str, str] = Field(default_factory=dict)
    missing_files: list[str] = Field(default_factory=list)
    full_character_ids: list[str] = Field(default_factory=list)
    reference_character_ids: list[str] = Field(default_factory=list)
    location_ids_loaded: list[str] = Field(default_factory=list)
    relationship_pairs_loaded: list[str] = Field(default_factory=list)
    prompt_preview: str | None = None


class ApplyTurnResultRequest(BaseModel):
    scene_text: str = ""
    technical: bool = False
    current_state_changes: dict[str, Any] = Field(default_factory=dict)
    calendar_runtime_changes: dict[str, Any] = Field(default_factory=dict)
    character_memory_changes: dict[str, Any] = Field(default_factory=dict)
    relationship_pair_changes: dict[str, Any] = Field(default_factory=dict)
    inventory_changes: dict[str, Any] = Field(default_factory=dict)
    reputation_changes: dict[str, Any] = Field(default_factory=dict)
    rumors_changes: dict[str, Any] = Field(default_factory=dict)
    power_changes: dict[str, Any] = Field(default_factory=dict)
    akira_progress_changes: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class ApplyTurnResultResponse(BaseModel):
    status: str
    changed_files: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
