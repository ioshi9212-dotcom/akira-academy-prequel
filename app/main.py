from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
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
    version="0.1.0",
    servers=[{"url": PUBLIC_BASE_URL, "description": "Railway production"}],
)


class FileUpdate(BaseModel):
    content: str = Field(..., description="Full replacement file content")


class JsonUpdate(BaseModel):
    data: Any = Field(..., description="JSON value to write")


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


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": APP_NAME,
        "data_dir": str(DATA_DIR),
        "volume_seeded": (DATA_DIR / ".seeded").exists(),
        "public_base_url": PUBLIC_BASE_URL,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": APP_NAME,
        "health": "/health",
        "context": "/api/v1/context",
        "files": "/api/v1/files",
        "openapi": "/openapi.json",
    }


@app.get("/api/v1/files")
def list_files() -> dict[str, Any]:
    ensure_data_dir()
    files: list[str] = []
    for path in DATA_DIR.rglob("*"):
        if path.is_file() and path.name != ".seeded":
            files.append(str(path.relative_to(DATA_DIR)))
    return {"data_dir": str(DATA_DIR), "files": sorted(files)}


@app.get("/api/v1/files/{file_path:path}", response_class=PlainTextResponse)
def get_file(file_path: str) -> str:
    ensure_data_dir()
    return read_text_file(file_path)


@app.put("/api/v1/files/{file_path:path}")
def update_file(file_path: str, update: FileUpdate) -> dict[str, Any]:
    ensure_data_dir()
    result = write_text_file(file_path, update.content)
    return {"status": "saved", **result}


@app.get("/api/v1/json/{file_path:path}")
def get_json_file(file_path: str) -> Any:
    ensure_data_dir()
    content = read_text_file(file_path)
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"File is not valid JSON: {exc}") from exc


@app.put("/api/v1/json/{file_path:path}")
def update_json_file(file_path: str, update: JsonUpdate) -> dict[str, Any]:
    ensure_data_dir()
    content = json.dumps(update.data, ensure_ascii=False, indent=2)
    result = write_text_file(file_path, content + "\n")
    return {"status": "saved", **result}


@app.get("/api/v1/context")
def get_context() -> dict[str, Any]:
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

    return {
        "current_state": read_optional_json("state/current_state.json"),
        "relationships": read_optional_json("state/relationships.json"),
        "reputation_state": read_optional_json("state/reputation_state.json"),
        "power_state": read_optional_json("state/power_state.json"),
        "rumors_state": read_optional_json("state/rumors_state.json"),
        "knowledge_state": read_optional_json("state/knowledge_state.json"),
        "inventory_state": read_optional_json("state/inventory_state.json"),
        "future_locks_progress": read_optional_json("state/future_locks_progress.json"),
        "academy_schedule": read_optional_json("state/academy_schedule.json"),
        "engine_prompt": read_optional_text("gpt/engine_prompt.md"),
        "scene_format": read_optional_text("gpt/scene_format.md"),
        "character_id_index": read_optional_text("characters/character_id_index.md"),
    }
