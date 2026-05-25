import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_NAME = "Akira Academy Prequel API"
BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://akira-academy-prequel-production.up.railway.app").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", "/data"))

# Source-controlled folders refresh into /data on startup.
# Runtime state/sessions are preserved in Railway volume.
SYNC_FROM_REPO = ["canon", "characters", "gpt", "templates"]
STATE_SEED = ["state"]
SESSION_RE = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")

REL_METRICS = [
    "affection",
    "trust",
    "tension",
    "jealousy",
    "respect",
    "curiosity",
    "resentment",
]

STATE_SECTION_MAP = [
    ("state/current_state.json", ["current_state_changes", "current_state", "state_changes"]),
    ("state/knowledge_state.json", ["knowledge_changes", "knowledge_state_changes", "knowledge_state"]),
    ("state/reputation_state.json", ["reputation_changes", "reputation_state_changes", "reputation_state"]),
    ("state/rumors_state.json", ["rumor_changes", "rumors_changes", "rumors_state_changes", "rumors_state"]),
    ("state/inventory_state.json", ["inventory_changes", "inventory_state_changes", "inventory_state"]),
    ("state/power_state.json", ["power_changes", "power_state_changes", "power_state"]),
    ("state/future_locks_progress.json", ["future_locks_changes", "future_locks_progress_changes", "future_locks_progress"]),
]

app = FastAPI(title=APP_NAME, version="0.3.8", servers=[{"url": BASE_URL}])


class FileUpdate(BaseModel):
    content: str


class JsonUpdate(BaseModel):
    data: object


class SessionCreateRequest(BaseModel):
    session_id: str | None = None
    title: str | None = None


class ApplyTurnResultRequest(BaseModel):
    turn_file: str | None = None
    data: object | None = None
    dry_run: bool = False


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
    apply_turn_result: str
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
    data: object


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
    current_state: object | None = None
    relationships: object | None = None
    reputation_state: object | None = None
    power_state: object | None = None
    rumors_state: object | None = None
    knowledge_state: object | None = None
    inventory_state: object | None = None
    future_locks_progress: object | None = None
    academy_schedule: object | None = None
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


def save_text(path: str, content: str, session_id: str | None = None) -> dict:
    file = file_root(session_id) / safe(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    if session_id:
        touch_session(session_id)
    return {"path": path, "bytes": len(content.encode("utf-8"))}


def read_json(path: str, session_id: str | None = None, default=None):
    try:
        return json.loads(read_text(path, session_id=session_id))
    except HTTPException:
        return default


def write_json(path: str, data, session_id: str | None = None) -> None:
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


def existing_repo_files(pattern: str) -> list[str]:
    return sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern) if p.is_file())


def base_recommended_files() -> list[str]:
    core_files = [
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
        "characters/character_habits.md",
    ]
    dynamic_files = []
    dynamic_files += existing_repo_files("gpt/locks/*.md")
    dynamic_files += existing_repo_files("characters/main/*.md")
    dynamic_files += existing_repo_files("characters/locks/*.md")
    # Preserve order while removing duplicates and missing files.
    result = []
    for path in core_files + dynamic_files:
        if path not in result and (ROOT / path).exists():
            result.append(path)
    return result


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


def output_format_contract() -> dict:
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
            "No empty scenes: every scene needs a hook, conflict, conversation, observation, social reaction, rumor, consequence, or time skip.",
            "Livia is Akira's close school friend for about six years, not a new roommate.",
            "Raiden is always dark-haired.",
            "Raiden does not patiently tolerate sticky female touches; trigger comes from stepmother history, but most people do not know that.",
            "Haru flirts easily, but tires when people see only the charismatic red-haired image, not him.",
            "No passive space or technical glitches around Akira without a direct reason.",
            "If output format is wrong, rewrite before sending.",
        ],
    }


def latest_turn_file(session_id: str) -> Path:
    root = ensure_session(session_id)
    candidates = []

    for folder in [
        root / "turn_results",
        root / "turns",
        DATA / "turn_results",
    ]:
        if folder.exists():
            candidates += [p for p in folder.glob("turn_*.json") if p.is_file()]

    if not candidates:
        raise HTTPException(status_code=404, detail="No turn_results files found")

    return sorted(candidates, key=lambda p: p.name)[-1]


def read_turn_payload(session_id: str, req: ApplyTurnResultRequest) -> tuple[str, dict]:
    if isinstance(req.data, dict):
        return "inline", req.data

    root = ensure_session(session_id)

    if req.turn_file:
        safe_name = Path(req.turn_file).name

        candidates = [
            root / safe(req.turn_file),
            root / "turn_results" / safe_name,
        ]

        turn_path = next((p for p in candidates if p.exists() and p.is_file()), None)

        if turn_path is None:
            raise HTTPException(status_code=404, detail="Turn result file not found")
    else:
        turn_path = latest_turn_file(session_id)

    try:
        return str(turn_path.relative_to(root)), json.loads(turn_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid turn result JSON: {exc}") from exc


def deep_merge(dst, src):
    if not isinstance(src, dict):
        return dst

    if not isinstance(dst, dict):
        dst = {}

    for key, value in src.items():
        if isinstance(value, dict):
            dst[key] = deep_merge(dst.get(key, {}), value)

        elif isinstance(value, list):
            existing = dst.get(key, [])
            if not isinstance(existing, list):
                existing = []

            for item in value:
                if item not in existing:
                    existing.append(item)

            dst[key] = existing

        else:
            dst[key] = value

    return dst


def find_section(payload: dict, names: list[str]):
    for name in names:
        if name in payload:
            return payload[name]

    data = payload.get("data")
    if isinstance(data, dict):
        for name in names:
            if name in data:
                return data[name]

    return None


def normalize_change_items(section):
    if not section:
        return []

    if isinstance(section, dict):
        result = []
        for key, value in section.items():
            if isinstance(value, dict):
                result.append({"id": key, **value})
            else:
                result.append({"id": key, "value": value})
        return result

    if isinstance(section, list):
        return [x for x in section if isinstance(x, dict)]

    return []


def default_relationship(status: str = "отношения появились после сцены") -> dict:
    data = {metric: 0 for metric in REL_METRICS}
    data["status"] = status
    data["notes"] = []
    return data


def apply_relationship_changes(session_id: str, payload: dict, dry_run: bool) -> bool:
    section = find_section(
        payload,
        [
            "relationship_changes",
            "relationships_changes",
            "relationship_deltas",
            "relationships",
        ],
    )

    items = normalize_change_items(section)

    if not items:
        return False

    state = read_json("state/relationships.json", session_id, default={}) or {}

    pairs = state.setdefault("pairs", {})
    changed = False

    for item in items:
        pair = item.get("pair") or item.get("pair_id") or item.get("id")

        if not pair or "__" not in str(pair):
            continue

        rel = pairs.setdefault(str(pair), default_relationship())

        for metric in REL_METRICS:
            delta_key = f"{metric}_delta"

            if delta_key in item:
                rel[metric] = max(
                    0,
                    min(100, int(rel.get(metric, 0)) + int(item.get(delta_key) or 0)),
                )
                changed = True

            elif metric in item and isinstance(item.get(metric), int):
                rel[metric] = max(0, min(100, int(item[metric])))
                changed = True

        if isinstance(item.get("status"), str):
            rel["status"] = item["status"]
            changed = True

        notes = item.get("notes") or item.get("add_notes") or item.get("note")

        if isinstance(notes, str):
            notes = [notes]

        if isinstance(notes, list):
            rel_notes = rel.setdefault("notes", [])

            for note in notes:
                if note and note not in rel_notes:
                    rel_notes.append(note)
                    changed = True

    if changed and not dry_run:
        write_json("state/relationships.json", state, session_id)

    return changed


def apply_json_section(
    session_id: str,
    payload: dict,
    file_path: str,
    names: list[str],
    dry_run: bool,
) -> bool:
    section = find_section(payload, names)

    if not isinstance(section, dict) or not section:
        return False

    state = read_json(file_path, session_id, default={}) or {}

    old_dump = json.dumps(state, ensure_ascii=False, sort_keys=True)

    new_state = deep_merge(state, section)

    new_dump = json.dumps(new_state, ensure_ascii=False, sort_keys=True)

    if new_dump != old_dump:
        if not dry_run:
            write_json(file_path, new_state, session_id)
        return True

    return False


@app.on_event("startup")
def startup():
    seed()


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", app=APP_NAME, data_dir=str(DATA), volume_seeded=(DATA / ".seeded").exists(), public_base_url=BASE_URL)


@app.get("/", response_model=RootResponse)
def root():
    return RootResponse(
        app=APP_NAME,
        health="/health",
        context="/api/v1/context",
        compact_context="/api/v1/context/compact",
        sessions="/api/v1/sessions",
        files="/api/v1/files",
        repair_start_state="/api/v1/repair/start-state",
        apply_turn_result="/api/v1/sessions/{session_id}/apply-turn-result",
        openapi="/openapi.json",
    )


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
            "empty scenes where nothing happens and no line moves",
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
            "passive space or technical glitches around Akira without cause",
        ],
        "required_checks_before_answer": [
            "Load session context first.",
            "Obey output_format_contract exactly.",
            "Read required_files before scene, including gpt/locks/no_empty_scenes_lock.md and gpt/locks/apply_state_after_turn_lock.md.",
            "After each scene, apply turn result to state files or call /api/v1/sessions/{session_id}/apply-turn-result.",
            "Check knowledge_state before NPC claims.",
            "Check inventory_state before items.",
            "No empty scenes: if Akira goes for coffee/sleeps/walks, add a hook or compress to the next meaningful event.",
            "Livia has known Akira for about six years and knows Jun, Ray, windows/edges, no relationships, and public space energy.",
            "Raiden is strictly dark-haired.",
            "Apply haru_raiden_attraction_social_reactions_lock: Haru flirts easily but tires of people seeing only the red-haired charismatic image; Raiden gets fear/looks/provocations and female touch triggers from stepmother history.",
            "No passive tech/space glitches around Akira without direct cause.",
            "Rewrite before sending if format or locks are wrong.",
        ],
        "knowledge_table": {cid: knowledge.get(cid, {}) for cid in scene_chars},
        "inventory_contract": {
            "visible_inventory": current.get("visible_inventory", []),
            "nearby_items": current.get("nearby_items", []),
            "akira_inventory_state": (inventory.get("akira") or {}),
        },
        "canon_locks": locks[:12],
    }


@app.post("/api/v1/sessions/{session_id}/apply-turn-result")
def apply_turn_result(
    session_id: str,
    request: ApplyTurnResultRequest = ApplyTurnResultRequest(),
):
    sid = safe_session_id(session_id)
    ensure_session(sid)

    source, payload = read_turn_payload(sid, request)

    changed_files = []

    if apply_relationship_changes(sid, payload, request.dry_run):
        changed_files.append("state/relationships.json")

    for path, names in STATE_SECTION_MAP:
        if apply_json_section(sid, payload, path, names, request.dry_run):
            changed_files.append(path)

    return {
        "status": "applied" if changed_files else "no_changes_detected",
        "session_id": sid,
        "source": source,
        "dry_run": request.dry_run,
        "changed_files": changed_files,
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
