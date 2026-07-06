from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR", "/data"))
SESSION_RE = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")

# Clean repo data directories. Do not include app/gpt/engine runtime locks here.
DATA_DIRS_TO_SEED = [
    "assembly",
    "calendar",
    "canon_lore",
    "characters",
    "locations",
    "rules",
    "state",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_session_id(session_id: str) -> str:
    if not SESSION_RE.match(session_id or ""):
        raise HTTPException(status_code=400, detail="Unsafe session_id")
    return session_id


def safe_path(path: str) -> Path:
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise HTTPException(status_code=400, detail="Unsafe path")
    return p


def _copy_tree(src: Path, dst: Path) -> None:
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


def seed_data() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name in DATA_DIRS_TO_SEED:
        _copy_tree(ROOT / name, DATA / name)
    (DATA / "sessions").mkdir(parents=True, exist_ok=True)
    (DATA / ".seeded").write_text(utc_now() + "\n", encoding="utf-8")


def session_root(session_id: str) -> Path:
    return DATA / "sessions" / safe_session_id(session_id)


def ensure_session(session_id: str) -> Path:
    root = session_root(session_id)
    if not root.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    return root


def create_session(session_id: str, title: str = "Academy Prequel Session", reset: bool = False) -> dict[str, Any]:
    seed_data()
    sid = safe_session_id(session_id)
    root = session_root(sid)
    if reset and root.exists():
        shutil.rmtree(root)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        # Session state is writable overlay; canonical content remains read-only in DATA.
        _copy_tree(DATA / "state", root / "state")
        meta = {
            "session_id": sid,
            "title": title,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        write_text("session.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n", sid)
    meta = read_json("session.json", sid, default={}) or {}
    return meta


def _candidate_paths(path: str, session_id: str | None = None) -> list[Path]:
    rel = safe_path(path)
    items: list[Path] = []
    if session_id:
        items.append(session_root(session_id) / rel)
    items.append(DATA / rel)
    items.append(ROOT / rel)
    return items


def exists(path: str, session_id: str | None = None) -> bool:
    return any(p.exists() and p.is_file() for p in _candidate_paths(path, session_id))


def read_text(path: str, session_id: str | None = None, default: str | None = None) -> str:
    for p in _candidate_paths(path, session_id):
        if p.exists() and p.is_file():
            return p.read_text(encoding="utf-8")
    if default is not None:
        return default
    raise HTTPException(status_code=404, detail=f"File not found: {path}")


def write_text(path: str, content: str, session_id: str | None = None) -> None:
    root = session_root(session_id) if session_id else DATA
    target = root / safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    if session_id and path != "session.json":
        touch_session(session_id)


def read_json(path: str, session_id: str | None = None, default: Any = None) -> Any:
    try:
        return json.loads(read_text(path, session_id))
    except HTTPException:
        return default
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: str, data: Any, session_id: str | None = None) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", session_id)


def read_yaml(path: str, session_id: str | None = None, default: Any = None) -> Any:
    try:
        text = read_text(path, session_id)
    except HTTPException:
        return default
    try:
        return yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML in {path}: {exc}") from exc


def write_yaml(path: str, data: Any, session_id: str | None = None) -> None:
    write_text(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False), session_id)


def touch_session(session_id: str) -> None:
    meta = read_json("session.json", session_id, default={}) or {}
    meta["session_id"] = session_id
    meta["updated_at"] = utc_now()
    write_text("session.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n", session_id)


def deep_merge(base: Any, changes: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(changes, dict):
        return changes
    out = dict(base)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def list_data_files() -> list[str]:
    seed_data()
    return sorted(
        str(p.relative_to(DATA))
        for p in DATA.rglob("*")
        if p.is_file() and p.name != ".seeded" and "/sessions/" not in str(p)
    )
