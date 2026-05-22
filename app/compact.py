import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_NAME = "Akira Academy Prequel API"
BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://akira-academy-prequel-production.up.railway.app").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", "/data"))
SEED = ["canon", "characters", "gpt", "state", "templates"]

app = FastAPI(title=APP_NAME, version="0.2.2", servers=[{"url": BASE_URL}])

class FileUpdate(BaseModel):
    content: str

class JsonUpdate(BaseModel):
    data: Any

class HealthResponse(BaseModel):
    status: str
    app: str
    data_dir: str
    volume_seeded: bool
    public_base_url: str

class RootResponse(BaseModel):
    app: str
    health: str
    context: str
    compact_context: str
    files: str
    repair_start_state: str
    openapi: str

class FilesResponse(BaseModel):
    data_dir: str
    files: list[str] = Field(default_factory=list)

class TextFileResponse(BaseModel):
    path: str
    content: str

class SaveResponse(BaseModel):
    status: str
    path: str
    bytes: int

class JsonFileResponse(BaseModel):
    path: str
    data: Any

class CompactContextResponse(BaseModel):
    current_state: Any = None
    relationships: Any = None
    reputation_state: Any = None
    power_state: Any = None
    rumors_state: Any = None
    knowledge_state: Any = None
    inventory_state: Any = None
    future_locks_progress: Any = None
    academy_schedule: Any = None
    api_usage_note: str
    recommended_files: list[str] = Field(default_factory=list)

class RepairResponse(BaseModel):
    status: str
    changed_files: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

def safe(p: str) -> Path:
    path = Path(p)
    if path.is_absolute() or ".." in path.parts:
        raise HTTPException(status_code=400, detail="Unsafe path")
    return path

def copy_missing(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_dir():
        for item in src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src)
                target = dst / rel
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
    elif not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def seed() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name in SEED:
        copy_missing(ROOT / name, DATA / name)
    (DATA / ".seeded").write_text("seeded\n", encoding="utf-8")

def text(path: str) -> str:
    file = DATA / safe(path)
    if not file.exists() or not file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file.read_text(encoding="utf-8")

def save(path: str, content: str) -> dict[str, Any]:
    file = DATA / safe(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    return {"path": path, "bytes": len(content.encode("utf-8"))}

def j(path: str) -> Any:
    try:
        return json.loads(text(path))
    except HTTPException:
        return None

def write_json(path: str, data: Any) -> None:
    save(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def context_payload() -> CompactContextResponse:
    seed()
    return CompactContextResponse(
        current_state=j("state/current_state.json"),
        relationships=j("state/relationships.json"),
        reputation_state=j("state/reputation_state.json"),
        power_state=j("state/power_state.json"),
        rumors_state=j("state/rumors_state.json"),
        knowledge_state=j("state/knowledge_state.json"),
        inventory_state=j("state/inventory_state.json"),
        future_locks_progress=j("state/future_locks_progress.json"),
        academy_schedule=j("state/academy_schedule.json"),
        api_usage_note="Use /api/v1/context or /api/v1/context/compact every turn. Both return compact context. Load large lore files through get_file only when needed.",
        recommended_files=["gpt/engine_prompt.md", "gpt/scene_format.md", "characters/character_habits.md", "canon/academy_tone_and_visual_locks.md", "canon/energy_visibility_and_combat_rules.md", "canon/source_usage_rules.md", "canon/social_dynamics.md", "canon/timeline_1198_1206.md"],
    )

@app.on_event("startup")
def startup():
    seed()

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", app=APP_NAME, data_dir=str(DATA), volume_seeded=(DATA / ".seeded").exists(), public_base_url=BASE_URL)

@app.get("/", response_model=RootResponse)
def root():
    return RootResponse(app=APP_NAME, health="/health", context="/api/v1/context", compact_context="/api/v1/context/compact", files="/api/v1/files", repair_start_state="/api/v1/repair/start-state", openapi="/openapi.json")

@app.get("/api/v1/files", response_model=FilesResponse)
def list_files():
    seed()
    files = [str(p.relative_to(DATA)) for p in DATA.rglob("*") if p.is_file() and p.name != ".seeded"]
    return FilesResponse(data_dir=str(DATA), files=sorted(files))

@app.get("/api/v1/files/{file_path:path}", response_model=TextFileResponse)
def get_file(file_path: str):
    seed()
    return TextFileResponse(path=file_path, content=text(file_path))

@app.put("/api/v1/files/{file_path:path}", response_model=SaveResponse)
def put_file(file_path: str, update: FileUpdate):
    seed()
    r = save(file_path, update.content)
    return SaveResponse(status="saved", path=r["path"], bytes=r["bytes"])

@app.get("/api/v1/json/{file_path:path}", response_model=JsonFileResponse)
def get_json(file_path: str):
    seed()
    try:
        data = json.loads(text(file_path))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    return JsonFileResponse(path=file_path, data=data)

@app.put("/api/v1/json/{file_path:path}", response_model=SaveResponse)
def put_json(file_path: str, update: JsonUpdate):
    seed()
    r = save(file_path, json.dumps(update.data, ensure_ascii=False, indent=2) + "\n")
    return SaveResponse(status="saved", path=r["path"], bytes=r["bytes"])

@app.get("/api/v1/context", response_model=CompactContextResponse)
def context():
    return context_payload()

@app.get("/api/v1/context/compact", response_model=CompactContextResponse)
def compact_context():
    return context_payload()

@app.post("/api/v1/repair/start-state", response_model=RepairResponse)
def repair_start_state():
    seed()
    changed = []
    notes = []

    current = j("state/current_state.json") or {}
    inventory = j("state/inventory_state.json") or {}

    active = current.setdefault("active_characters", [])
    nearby = current.setdefault("nearby_characters", [])
    if "akira" not in active:
        active.append("akira")
    if "livia_cross" not in active and "livia_cross" not in nearby:
        nearby.append("livia_cross")
        notes.append("Added livia_cross as nearby at academy start.")

    current.setdefault("visible_inventory", [])
    current.setdefault("nearby_items", [])
    current.setdefault("current_scene_goal", "прибытие в Академию Астрейн и первые социальные контакты")
    write_json("state/current_state.json", current)
    changed.append("state/current_state.json")

    akira_inv = inventory.setdefault("akira", {})
    akira_inv.setdefault("visible_inventory", [])
    akira_inv.setdefault("nearby_items", [])
    akira_inv.setdefault("academy_issued_items", [])

    for item in current.get("visible_inventory", []):
        if item not in akira_inv["visible_inventory"]:
            akira_inv["visible_inventory"].append(item)
    for item in current.get("nearby_items", []):
        if item not in akira_inv["nearby_items"]:
            akira_inv["nearby_items"].append(item)

    write_json("state/inventory_state.json", inventory)
    changed.append("state/inventory_state.json")

    return RepairResponse(status="repaired", changed_files=changed, notes=notes)
