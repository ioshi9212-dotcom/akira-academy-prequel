import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_NAME = "Akira Academy Prequel API"
BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://akira-academy-prequel-production.up.railway.app").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", "/data"))

# These folders are source-controlled rules/canon/cards.
# They must refresh from the deployed repo on startup, even if /data already has older copies.
SYNC_FROM_REPO = ["canon", "characters", "gpt", "templates"]

# Runtime state is preserved in the volume and copied only when missing.
STATE_SEED = ["state"]
SESSION_RE = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")

app = FastAPI(title=APP_NAME, version="0.3.5", servers=[{"url": BASE_URL}])

class FileUpdate(BaseModel):
    content: str

class JsonUpdate(BaseModel):
    data: Any

class SessionCreateRequest(BaseModel):
    session_id: str | None = None
    title: str | None = None

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
    sessions: str
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

class SessionInfo(BaseModel):
    session_id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    context: str

class SessionsResponse(BaseModel):
    sessions: list[SessionInfo] = Field(default_factory=list)

class CompactContextResponse(BaseModel):
    session_id: str | None = None
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

def safe_session_id(session_id: str) -> str:
    if not SESSION_RE.match(session_id):
        raise HTTPException(status_code=400, detail="Unsafe session_id")
    return session_id

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

def sync_from_repo(src: Path, dst: Path) -> None:
    """Overwrite source-controlled files in /data without touching session runtime state."""
    if not src.exists():
        return
    if src.is_dir():
        for item in src.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def seed() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name in SYNC_FROM_REPO:
        sync_from_repo(ROOT / name, DATA / name)
    for name in STATE_SEED:
        copy_missing(ROOT / name, DATA / name)
    (DATA / "sessions").mkdir(parents=True, exist_ok=True)
    (DATA / ".seeded").write_text("seeded\n", encoding="utf-8")

def session_dir(session_id: str) -> Path:
    return DATA / "sessions" / safe_session_id(session_id)

def ensure_session(session_id: str) -> Path:
    d = session_dir(session_id)
    if not d.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    return d

def file_root(session_id: str | None = None) -> Path:
    return ensure_session(session_id) if session_id else DATA

def read_text(path: str, session_id: str | None = None) -> str:
    file = file_root(session_id) / safe(path)
    if not file.exists() or not file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file.read_text(encoding="utf-8")

def save_text(path: str, content: str, session_id: str | None = None) -> dict[str, Any]:
    file = file_root(session_id) / safe(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    if session_id:
        touch_session(session_id)
    return {"path": path, "bytes": len(content.encode("utf-8"))}

def read_json(path: str, session_id: str | None = None, default: Any = None) -> Any:
    try:
        return json.loads(read_text(path, session_id=session_id))
    except HTTPException:
        return default

def write_json(path: str, data: Any, session_id: str | None = None) -> None:
    save_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", session_id=session_id)

def touch_session(session_id: str) -> None:
    meta_path = session_dir(session_id) / "session.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    meta["session_id"] = session_id
    meta["updated_at"] = datetime.utcnow().isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def base_recommended_files() -> list[str]:
    return [
        "gpt/engine_prompt.md",
        "gpt/scene_format.md",
        "canon/novella_goal.md",
        "canon/character_story_roles.md",
        "canon/academy_rating_and_training.md",
        "canon/academy_locations.md",
        "canon/academy_tone_and_visual_locks.md",
        "canon/energy_visibility_and_combat_rules.md",
        "canon/source_usage_rules.md",
        "canon/social_dynamics.md",
        "canon/timeline_1198_1206.md",
        "characters/main/akira.md",
        "characters/main/livia_cross.md",
        "characters/main/raiden_sterling.md",
        "characters/main/haru_foster.md",
        "characters/main/samuel_sterling.md",
        "characters/main/ray_carter.md",
        "characters/character_habits.md",
        "characters/locks/livia_akira_friendship_lock.md",
        "characters/locks/akira_no_passive_glitches_lock.md",
        "characters/locks/akira_no_reused_player_lines_lock.md",
        "characters/locks/akira_school_past_livia_dynamic_lock.md",
        "characters/locks/akira_sleep_recovery_livia_guard_lock.md",
        "characters/locks/raiden_lazy_mask_social_lock.md",
        "characters/locks/haru_raiden_attraction_social_reactions_lock.md",
    ]

def context_payload(session_id: str | None = None) -> CompactContextResponse:
    seed()
    note = "Use this endpoint every turn. For separate games, always pass session_id and use session endpoints. Load large lore files through get_file only when needed."
    return CompactContextResponse(
        session_id=session_id,
        current_state=read_json("state/current_state.json", session_id),
        relationships=read_json("state/relationships.json", session_id),
        reputation_state=read_json("state/reputation_state.json", session_id),
        power_state=read_json("state/power_state.json", session_id),
        rumors_state=read_json("state/rumors_state.json", session_id),
        knowledge_state=read_json("state/knowledge_state.json", session_id),
        inventory_state=read_json("state/inventory_state.json", session_id),
        future_locks_progress=read_json("state/future_locks_progress.json", session_id),
        academy_schedule=read_json("state/academy_schedule.json", session_id),
        api_usage_note=note,
        recommended_files=base_recommended_files(),
    )

def repair_state(session_id: str | None = None) -> RepairResponse:
    seed()
    changed, notes = [], []
    current = read_json("state/current_state.json", session_id, default={}) or {}
    inventory = read_json("state/inventory_state.json", session_id, default={}) or {}
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
    write_json("state/current_state.json", current, session_id)
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
    write_json("state/inventory_state.json", inventory, session_id)
    changed.append("state/inventory_state.json")
    return RepairResponse(status="repaired", changed_files=changed, notes=notes)

def output_format_contract() -> dict[str, Any]:
    return {
        "priority": "highest_for_scene_output",
        "dialogue_format": "**Имя или видимый дескриптор** — Реплика. (*короткая ремарка: тон, взгляд, пауза, жест*)",
        "description_format": "*Описание действия, окружения или атмосферы отдельной строкой курсивом.*",
        "rules": [
            "Every spoken line starts with bold speaker name or visible descriptor.",
            "Do not use names Akira has not heard or read yet.",
            "After speaker name use long dash.",
            "Dialogue text is plain.",
            "Optional stage note is short and italic in parentheses.",
            "No long actions in parentheses.",
            "No character thoughts in parentheses.",
            "Descriptions are separate italic paragraphs.",
            "No direct Akira thoughts inside the scene.",
            "Akira thoughts only in bottom block: Мысли Акиры.",
            "Livia is Akira's close school friend for about six years, not a new roommate.",
            "Raiden is always dark-haired.",
            "Raiden does not patiently tolerate sticky female touches; trigger comes from stepmother history, but most people do not know that.",
            "Haru flirts easily, but tires when people see only the charismatic red-haired image, not him.",
            "No passive space or technical glitches around Akira without a direct reason.",
            "If output format is wrong, rewrite before sending."
        ],
        "ending_block": [
            "━━━━━━━━━━━━━━━━━━━━",
            "Что можно сделать:",
            "1.", "2.", "3.", "",
            "Что Акира могла бы сказать:",
            "— “...”", "— “...”", "",
            "Мысли Акиры:",
            "— ...", "— ...",
            "━━━━━━━━━━━━━━━━━━━━"
        ],
        "example": [
            "*Ветер протягивает по главному двору запах мокрого бетона и металла. Несколько студентов задерживают взгляд на белых волосах Акиры.*",
            "**Ливия** — Кофе без сахара, да. Я помню. Я с тобой шесть лет страдаю. (*закатывает глаза*)",
            "**Рыжий студент** — О, новенькие. И сразу такие серьёзные? (*смотрит на Акиру с открытым интересом*)",
            "**Тёмноволосый парень у стены** — Не стой на проходе. (*лениво, не поднимая голоса*)"
        ]
    }

@app.on_event("startup")
def startup():
    seed()

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", app=APP_NAME, data_dir=str(DATA), volume_seeded=(DATA / ".seeded").exists(), public_base_url=BASE_URL)

@app.get("/", response_model=RootResponse)
def root():
    return RootResponse(app=APP_NAME, health="/health", context="/api/v1/context", compact_context="/api/v1/context/compact", sessions="/api/v1/sessions", files="/api/v1/files", repair_start_state="/api/v1/repair/start-state", openapi="/openapi.json")

@app.post("/api/v1/sessions", response_model=SessionInfo)
def create_session(payload: SessionCreateRequest):
    seed()
    sid = safe_session_id(payload.session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}")
    d = session_dir(sid)
    if not d.exists():
        d.mkdir(parents=True, exist_ok=True)
        copy_missing(DATA / "state", d / "state")
        meta = {"session_id": sid, "title": payload.title or "Academy Prequel Session", "created_at": datetime.utcnow().isoformat(), "updated_at": datetime.utcnow().isoformat()}
        (d / "session.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    meta = read_json("session.json", sid) or {}
    return SessionInfo(session_id=sid, title=meta.get("title"), created_at=meta.get("created_at"), updated_at=meta.get("updated_at"), context=f"/api/v1/sessions/{sid}/context")

@app.get("/api/v1/sessions", response_model=SessionsResponse)
def list_sessions():
    seed()
    items = []
    for d in sorted((DATA / "sessions").iterdir() if (DATA / "sessions").exists() else []):
        if d.is_dir() and (d / "session.json").exists():
            meta = json.loads((d / "session.json").read_text(encoding="utf-8"))
            items.append(SessionInfo(session_id=meta.get("session_id", d.name), title=meta.get("title"), created_at=meta.get("created_at"), updated_at=meta.get("updated_at"), context=f"/api/v1/sessions/{d.name}/context"))
    return SessionsResponse(sessions=items)

@app.get("/api/v1/sessions/{session_id}/context", response_model=CompactContextResponse)
def session_context(session_id: str):
    return context_payload(safe_session_id(session_id))

@app.get("/api/v1/sessions/{session_id}/turn-contract")
def session_turn_contract(session_id: str):
    sid = safe_session_id(session_id)
    ensure_session(sid)
    current = read_json("state/current_state.json", sid, default={}) or {}
    knowledge = read_json("state/knowledge_state.json", sid, default={}) or {}
    inventory = read_json("state/inventory_state.json", sid, default={}) or {}
    future = read_json("state/future_locks_progress.json", sid, default={}) or {}
    active = list(dict.fromkeys(current.get("active_characters", []) or []))
    nearby = list(dict.fromkeys(current.get("nearby_characters", []) or []))
    scene_chars = list(dict.fromkeys(active + nearby))
    locks = []
    for lock_id, lock in (future.get("locks") or {}).items():
        if lock.get("status") in {"active", "scheduled", "not_started", "available_but_rare"}:
            locks.append(f"{lock_id}: {lock.get('description', '')}")
    return {
        "session_id": sid,
        "active_character_ids": active,
        "nearby_character_ids": nearby,
        "required_files": base_recommended_files(),
        "output_format_contract": output_format_contract(),
        "allowed_new_facts_this_turn": ["neutral sensory details", "minor gestures", "small social reactions", "new named NPC only if saved after scene"],
        "forbidden_new_facts_this_turn": [
            "future 1206 events as current 1198 facts",
            "hidden nature of Akira revealed without scene basis",
            "NPC knowledge from unseen scenes",
            "new items without state update",
            "dialogue without bold speaker names",
            "direct Akira thoughts inside scene text",
            "Livia treated as new roommate/new acquaintance",
            "Raiden described as light-haired",
            "Raiden treated as literally lazy or absent from academy life",
            "Raiden calmly accepting sticky female touches",
            "Haru treated as a flat womanizer without the image-vs-real-person reason",
            "passive space or technical glitches around Akira without cause"
        ],
        "required_checks_before_answer": [
            "Load session context first.",
            "Obey output_format_contract exactly.",
            "Read required_files before scene.",
            "Check knowledge_state before NPC claims.",
            "Check inventory_state before items.",
            "Livia has known Akira for about six years and knows Jun, Ray, windows/edges, no relationships, and public space energy.",
            "Raiden is strictly dark-haired.",
            "Apply haru_raiden_attraction_social_reactions_lock: Haru flirts easily but tires of people seeing only the red-haired charismatic image; Raiden gets fear/looks/provocations and female touch triggers from stepmother history.",
            "No passive tech/space glitches around Akira without direct cause.",
            "Rewrite before sending if format or locks are wrong."
        ],
        "knowledge_table": {cid: knowledge.get(cid, {}) for cid in scene_chars},
        "inventory_contract": {"visible_inventory": current.get("visible_inventory", []), "nearby_items": current.get("nearby_items", []), "akira_inventory_state": (inventory.get("akira") or {})},
        "canon_locks": locks[:12]
    }

@app.get("/api/v1/sessions/{session_id}/json/{file_path:path}", response_model=JsonFileResponse)
def get_session_json(session_id: str, file_path: str):
    data = json.loads(read_text(file_path, safe_session_id(session_id)))
    return JsonFileResponse(path=file_path, data=data)

@app.put("/api/v1/sessions/{session_id}/json/{file_path:path}", response_model=SaveResponse)
def put_session_json(session_id: str, file_path: str, update: JsonUpdate):
    sid = safe_session_id(session_id)
    r = save_text(file_path, json.dumps(update.data, ensure_ascii=False, indent=2) + "\n", sid)
    return SaveResponse(status="saved", path=r["path"], bytes=r["bytes"])

@app.post("/api/v1/sessions/{session_id}/repair/start-state", response_model=RepairResponse)
def repair_session_start_state(session_id: str):
    return repair_state(safe_session_id(session_id))

@app.get("/api/v1/files", response_model=FilesResponse)
def list_files():
    seed()
    files = [str(p.relative_to(DATA)) for p in DATA.rglob("*") if p.is_file() and p.name != ".seeded"]
    return FilesResponse(data_dir=str(DATA), files=sorted(files))

@app.get("/api/v1/files/{file_path:path}", response_model=TextFileResponse)
def get_file(file_path: str):
    seed()
    return TextFileResponse(path=file_path, content=read_text(file_path))

@app.put("/api/v1/files/{file_path:path}", response_model=SaveResponse)
def put_file(file_path: str, update: FileUpdate):
    seed()
    r = save_text(file_path, update.content)
    return SaveResponse(status="saved", path=r["path"], bytes=r["bytes"])

@app.get("/api/v1/json/{file_path:path}", response_model=JsonFileResponse)
def get_json(file_path: str):
    try:
        data = json.loads(read_text(file_path))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    return JsonFileResponse(path=file_path, data=data)

@app.put("/api/v1/json/{file_path:path}", response_model=SaveResponse)
def put_json(file_path: str, update: JsonUpdate):
    r = save_text(file_path, json.dumps(update.data, ensure_ascii=False, indent=2) + "\n")
    return SaveResponse(status="saved", path=r["path"], bytes=r["bytes"])

@app.get("/api/v1/context", response_model=CompactContextResponse)
def context():
    return context_payload()

@app.get("/api/v1/context/compact", response_model=CompactContextResponse)
def compact_context():
    return context_payload()

@app.post("/api/v1/repair/start-state", response_model=RepairResponse)
def repair_start_state():
    return repair_state()
