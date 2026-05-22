from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_NAME = "Akira Academy Prequel API"
PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://akira-academy-prequel-production.up.railway.app",
).rstrip("/")
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))

SEED_DIRS = ["canon", "characters", "gpt", "state", "templates"]

app = FastAPI(
    title=APP_NAME,
    version="0.1.1",
    servers=[{"url": PUBLIC_BASE_URL, "description": "Railway production"}],
)


class FileUpdate(BaseModel):
    content: str = Field(..., description="Full replacement file content")


class JsonUpdate(BaseModel):
    data: Any = Field(..., description="JSON value to write")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    app: str = Field(..., description="Application name")
    data_dir: str = Field(..., description="Persistent data directory")
    volume_seeded: bool = Field(..., description="Whether the Railway volume has been seeded")
    public_base_url: str = Field(..., description="Public base URL used in OpenAPI servers")


class RootResponse(BaseModel):
    app: str = Field(..., description="Application name")
    health: str = Field(..., description="Health endpoint path")
    context: str = Field(..., description="Context endpoint path")
    files: str = Field(..., description="Files endpoint path")
    openapi: str = Field(..., description="OpenAPI endpoint path")


class FilesResponse(BaseModel):
    data_dir: str = Field(..., description="Persistent data directory")
    files: list[str] = Field(default_factory=list, description="Stored file paths")


class TextFileResponse(BaseModel):
    path: str = Field(..., description="File path relative to DATA_DIR")
    content: str = Field(..., description="Text file content")


class SaveResponse(BaseModel):
    status: str = Field(..., description="Save status")
    path: str = Field(..., description="Saved file path relative to DATA_DIR")
    bytes: int = Field(..., description="Number of bytes written")


class JsonFileResponse(BaseModel):
    path: str = Field(..., description="JSON file path relative to DATA_DIR")
    data: Any = Field(..., description="Parsed JSON content")


class ContextResponse(BaseModel):
    current_state: Any = Field(None, description="Current story state")
    relationships: Any = Field(None, description="Relationship state")
    reputation_state: Any = Field(None, description="Reputation state")
    power_state: Any = Field(None, description="Power state")
    rumors_state: Any = Field(None, description="Rumors state")
    knowledge_state: Any = Field(None, description="Knowledge state")
    inventory_state: Any = Field(None, description="Inventory state")
    future_locks_progress: Any = Field(None, description="Future canon lock progress")
    academy_schedule: Any = Field(None, description="Academy schedule")
    engine_prompt: str | None = Field(None, description="Main engine prompt")
    scene_format: str | None = Field(None, description="Scene format rules")
    character_id_index: str | None = Field(None, description="Character ID index")


def safe_relative_path(path: str) -> Path:
    clean = Path(path)
    if clean.is_absolute() or ".." in clean.parts:
        raise HTTPException(status_code=400, detail="Unsafe path")
    return clean


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    marker = DATA_DIR / ".seeded"
    if marker.exists():
        return

    for folder_name in SEED_DIRS:
        source = REPO_ROOT / folder_name
        target = DATA_DIR / folder_name
        if source.exists() and not target.exists():
            shutil.copytree(source, target)

    marker.write_text("seeded\n", encoding="utf-8")


def read_text_file(relative_path: str) -> str:
    path = DATA_DIR / safe_relative_path(relative_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return path.read_text(encoding="utf-8")


def write_text_file(relative_path: str, content: str) -> dict[str, Any]:
    path = DATA_DIR / safe_relative_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": relative_path, "bytes": len(content.encode("utf-8"))}


@app.on_event("startup")
def startup() -> None:
    ensure_data_dir()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=APP_NAME,
        data_dir=str(DATA_DIR),
        volume_seeded=(DATA_DIR / ".seeded").exists(),
        public_base_url=PUBLIC_BASE_URL,
    )


@app.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(
        app=APP_NAME,
        health="/health",
        context="/api/v1/context",
        files="/api/v1/files",
        openapi="/openapi.json",
    )


@app.get("/api/v1/files", response_model=FilesResponse)
def list_files() -> FilesResponse:
    ensure_data_dir()
    files: list[str] = []
    for path in DATA_DIR.rglob("*"):
        if path.is_file() and path.name != ".seeded":
            files.append(str(path.relative_to(DATA_DIR)))
    return FilesResponse(data_dir=str(DATA_DIR), files=sorted(files))


@app.get("/api/v1/files/{file_path:path}", response_model=TextFileResponse)
def get_file(file_path: str) -> TextFileResponse:
    ensure_data_dir()
    return TextFileResponse(path=file_path, content=read_text_file(file_path))


@app.put("/api/v1/files/{file_path:path}", response_model=SaveResponse)
def update_file(file_path: str, update: FileUpdate) -> SaveResponse:
    ensure_data_dir()
    result = write_text_file(file_path, update.content)
    return SaveResponse(status="saved", path=result["path"], bytes=result["bytes"])


@app.get("/api/v1/json/{file_path:path}", response_model=JsonFileResponse)
def get_json_file(file_path: str) -> JsonFileResponse:
    ensure_data_dir()
    content = read_text_file(file_path)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"File is not valid JSON: {exc}") from exc
    return JsonFileResponse(path=file_path, data=data)


@app.put("/api/v1/json/{file_path:path}", response_model=SaveResponse)
def update_json_file(file_path: str, update: JsonUpdate) -> SaveResponse:
    ensure_data_dir()
    content = json.dumps(update.data, ensure_ascii=False, indent=2)
    result = write_text_file(file_path, content + "\n")
    return SaveResponse(status="saved", path=result["path"], bytes=result["bytes"])


@app.get("/api/v1/context", response_model=ContextResponse)
def get_context() -> ContextResponse:
    ensure_data_dir()

    def read_optional_json(path: str) -> Any:
        try:
            return json.loads(read_text_file(path))
        except HTTPException:
            return None

    def read_optional_text(path: str) -> str | None:
        try:
            return read_text_file(path)
        except HTTPException:
            return None

    return ContextResponse(
        current_state=read_optional_json("state/current_state.json"),
        relationships=read_optional_json("state/relationships.json"),
        reputation_state=read_optional_json("state/reputation_state.json"),
        power_state=read_optional_json("state/power_state.json"),
        rumors_state=read_optional_json("state/rumors_state.json"),
        knowledge_state=read_optional_json("state/knowledge_state.json"),
        inventory_state=read_optional_json("state/inventory_state.json"),
        future_locks_progress=read_optional_json("state/future_locks_progress.json"),
        academy_schedule=read_optional_json("state/academy_schedule.json"),
        engine_prompt=read_optional_text("gpt/engine_prompt.md"),
        scene_format=read_optional_text("gpt/scene_format.md"),
        character_id_index=read_optional_text("characters/character_id_index.md"),
    )
