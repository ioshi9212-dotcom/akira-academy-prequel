from __future__ import annotations

import json
import os
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

import app.compact_context_patch as ccp
import app.response_size_guard_runtime_patch as size_guard
import app.state_write_runtime_patch as state_write
from app import compact as base
from app.services.ai_provider import AIProviderError, generate_ai_response

app = base.app

try:
    if "canon/character_depth_and_rotation.md" not in size_guard.BASE_RULE_FILES:
        size_guard.BASE_RULE_FILES.insert(1, "canon/character_depth_and_rotation.md")
except Exception:
    pass

PIPELINE_ID = "local_lmstudio_academy_turn_v1"
LOCAL_RUNTIME_VERSION = "0.3.65-local-lmstudio-depth-v1"


class LocalTurnRequest(BaseModel):
    user_input: str = ""
    mode: Literal["play", "technical", "audit"] = "play"
    dry_run: bool = True
    save_result: bool = False
    ai_provider: str | None = None
    include_prompt_bundle: bool = False
    auto_create_session: bool = True


class LocalTurnResponse(BaseModel):
    success: bool
    pipeline: str = PIPELINE_ID
    session_id: str
    mode: str
    dry_run: bool
    provider: str
    scene_text: str
    state_changes_applied: bool = False
    changed_files: list[str] = Field(default_factory=list)
    required_files_status: list[dict[str, Any]] = Field(default_factory=list)
    prompt_bundle: dict[str, Any] | None = None
    error: str | None = None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _local_context_mode() -> bool:
    provider = os.getenv("AI_PROVIDER", "").strip().lower()
    base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "").lower()
    if provider in {"lmstudio", "lm-studio", "local", "local_lm_studio"}:
        return True
    if os.getenv("LOCAL_LM_STUDIO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return any(marker in base_url for marker in ("127.0.0.1", "localhost", "0.0.0.0"))


def _ensure_session(sid: str, auto_create: bool) -> None:
    base.seed()
    try:
        base.ensure_session(sid)
        return
    except HTTPException as exc:
        if not auto_create or exc.status_code != 404:
            raise
    base.create_session(base.SessionCreateRequest(session_id=sid, title="LM Studio local session"))


def _unique(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in result:
            result.append(item)
    return result


def _read_required_source(path: str, session_id: str) -> tuple[str | None, str | None]:
    safe_path = str(path or "").strip()
    if not safe_path:
        return None, None

    if safe_path == "runtime/scene_context_digest.md":
        try:
            return size_guard.rt.build_scene_context_digest(session_id), "runtime"
        except Exception:
            pass

    if safe_path.startswith("state/"):
        try:
            return base.read_text(safe_path, session_id), "session_state"
        except Exception:
            try:
                return base.read_text(safe_path), "seed_state"
            except Exception:
                return None, None

    try:
        return base.read_text(safe_path), "project"
    except Exception:
        return None, None


def _required_files(session_id: str, current: dict[str, Any], future: dict[str, Any]) -> list[str]:
    files: list[str] = []
    try:
        files.extend(size_guard._required_files(current, future))
    except Exception:
        try:
            files.extend(base.recommended_files_for_context(current, future))
        except Exception:
            files = []

    high_signal = [
        "runtime/scene_context_digest.md",
        "canon/character_depth_and_rotation.md",
        "gpt/locks/runtime_scene_rules_digest.md",
        "gpt/locks/npc_living_scene_rules.md",
        "gpt/locks/character_presence_rotation_lock.md",
        "gpt/locks/player_input_anchor_lock.md",
        "gpt/scene_format.md",
        "state/current_state.json",
        "state/story_lines.json",
        "state/relationships.json",
        "state/knowledge_state.json",
    ]
    return _unique(high_signal + files)


def _file_limit(path: str, default_limit: int, local_mode: bool) -> int:
    if path == "runtime/scene_context_digest.md":
        return min(default_limit + (1600 if local_mode else 2600), 4200)
    if path == "canon/character_depth_and_rotation.md":
        return min(default_limit + (1200 if local_mode else 2200), 3600)
    if path.startswith("characters/"):
        return min(default_limit + (700 if local_mode else 1500), 3400)
    if path.startswith("state/"):
        return min(default_limit + (500 if local_mode else 1000), 2600)
    if path.startswith("gpt/locks/"):
        return min(default_limit + (450 if local_mode else 900), 2200)
    return default_limit


def _source_context(session_id: str, required_files: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    local_mode = _local_context_mode()
    total_limit = _env_int("SOURCE_CONTEXT_MAX_CHARS", 11500 if local_mode else 22000)
    file_limit = _env_int("SOURCE_CONTEXT_FILE_MAX_CHARS", 950 if local_mode else 2200)
    statuses: list[dict[str, Any]] = []
    result: list[dict[str, Any]] = []
    total = 0

    for path in required_files:
        content, source = _read_required_source(path, session_id)
        status: dict[str, Any] = {"path": path, "loaded": bool(content), "chars": len(content or ""), "source": source or "missing"}
        statuses.append(status)
        if not content or total >= total_limit:
            continue
        per_file = _file_limit(path, file_limit, local_mode)
        piece = content[:per_file]
        remaining = total_limit - total
        if len(piece) > remaining:
            piece = piece[:remaining]
        if piece.strip():
            result.append({"path": path, "source": source or "project", "content": piece})
            total += len(piece)

    return result, statuses


def _system_prompt() -> str:
    return """
Ты — локальный backend-controlled AI writer для интерактивной новеллы “Академия Астрейн · 1198”.
Пользователь играет ТОЛЬКО за Акиру. Не пиши прямую речь Акиры, если пользователь не дал её вне скобок.

Верни ТОЛЬКО JSON object без markdown fences:
{"scene_text":"...","state_changes":{}}

Обязательно используй source_context:
- runtime/scene_context_digest.md;
- canon/character_depth_and_rotation.md;
- карточки активных/nearby персонажей;
- state/current_state, story_lines, relationships, knowledge_state;
- gpt locks и scene_format.

Правила сцены:
- Акира не управляет миром своим намерением. NPC могут продолжать, давить, уклоняться, ошибаться, запоминать, отступать или отвечать действием.
- Персонажи реагируют только на видимое/слышимое: слова, тон, дистанцию, движение, предметы, публичный контекст, энергию, свои знания.
- Не давай NPC hidden knowledge без источника.
- Не делай персонажей функциями сцены. У каждого видимого действия должна быть причина: характер, цель, статус, страх, долг, симпатия, раздражение, отношения или знание.
- Не делай толпу одним организмом. 1–3 точных реакции лучше, чем “все посмотрели/замолчали”.
- POV только через восприятие Акиры. Не называй людей объективно “харизматичными/уверенными/интересными”; показывай действием.
- Хару и Райден заметны в Академии, но не обязаны быть удобными Акире. Хару действует через движение/мяч/социальный шум. Райден давит паузой, холодом, дистанцией и молчанием.
- Ливия не декор: она прикрывает, язвит, замечает социальный риск и может увести давление.
- Киара/социальная орбита проверяется, если сцена касается Хару, Райдена, Ливии, статуса или внимания.

Формат:
- Сцена начинается старым академическим visual-novel header.
- Диалог: **Имя/видимый дескриптор** — текст. (*короткая ремарка*)
- Игровой ответ — только сцена, без API/debug/status.
- Нижние блоки: ✦ Что можно сделать / ✦ Что Акира могла бы сказать / ✦ Мысли Акиры / ✦ Уровни / ✦ Отношения.
- Варианты действий должны иметь разные последствия: риск, информация, скорость, контроль, отношения, социальное давление, репутация или маршрут.
""".strip()


def _build_prompt_bundle(session_id: str, user_input: str, mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current = base.read_json("state/current_state.json", session_id, default={}) or {}
    future = base.read_json("state/future_locks_progress.json", session_id, default={}) or {}
    relationships = base.read_json("state/relationships.json", session_id, default={}) or {}
    knowledge = base.read_json("state/knowledge_state.json", session_id, default={}) or {}
    story_lines = base.read_json("state/story_lines.json", session_id, default={}) or {}

    required_files = _required_files(session_id, current, future)
    source_context, statuses = _source_context(session_id, required_files)

    bundle = {
        "pipeline": PIPELINE_ID,
        "system_prompt": _system_prompt(),
        "session_id": session_id,
        "mode": mode,
        "user_input": user_input,
        "current_state": current,
        "relationship_slice": size_guard._relationship_slice(relationships, size_guard._scene_chars(current, future)),
        "knowledge_slice": size_guard._knowledge_slice(knowledge, size_guard._scene_chars(current, future)),
        "story_slice": size_guard._story_slice(story_lines),
        "progress_panel": size_guard._progress_slice(session_id, relationships),
        "required_files": required_files,
        "source_context": source_context,
        "output_json_contract": {
            "scene_text": "complete visible gameplay scene only, no markdown fence",
            "state_changes": {
                "current_state_changes": {},
                "relationship_changes": {},
                "knowledge_changes": {},
                "story_lines_changes": {},
                "reputation_changes": {},
                "rumors_changes": {},
                "inventory_changes": {},
                "power_changes": {},
                "future_locks_changes": {},
            },
        },
        "quality_gate": {
            "do_not_copy_prompt_text": True,
            "no_api_status_summary": True,
            "no_functional_npcs": True,
            "do_not_write_akira_speech_unless_player_wrote_it": True,
            "npc_knowledge_source_required": True,
            "action_options_need_distinct_consequences": True,
        },
        "forbidden_generic_phrases": [
            "все замолчали",
            "все посмотрели на Акиру",
            "харизматичный рыжий",
            "уверенный парень",
            "интересный Райден",
            "Акира может",
            "подойти поговорить",
            "игнорировать и идти дальше",
        ],
    }
    return bundle, statuses


def _clean_scene_text(scene_text: str) -> str:
    text = str(scene_text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _scene_quality_issues(scene_text: str) -> list[str]:
    lower = scene_text.lower()
    issues: list[str] = []
    for phrase in [
        "все замолчали",
        "все посмотрели на акиру",
        "харизматичный рыж",
        "уверенный парень",
        "интересный райден",
        "акира может",
        "api",
        "debug",
        "status",
    ]:
        if phrase in lower:
            issues.append(f"generic/technical phrase: {phrase}")
    if "✦ что можно сделать" not in lower:
        issues.append("missing action block")
    if "✦ что акира могла бы сказать" not in lower:
        issues.append("missing speech options block")
    if "✦ мысли акиры" not in lower:
        issues.append("missing Akira thoughts block")
    if "**" not in scene_text:
        issues.append("missing bold speaker names")
    return issues[:12]


def _apply_state_changes(session_id: str, scene_text: str, changes: dict[str, Any], dry_run: bool) -> tuple[bool, list[str]]:
    payload = changes if isinstance(changes, dict) else {}
    request = ccp.ApplyTurnResultWithVisibleSceneRequest(
        data=payload,
        dry_run=dry_run,
        visible_scene_text=scene_text,
        render_packet={"pipeline": PIPELINE_ID, "source": "local_lmstudio_turn"},
    )
    result = state_write.apply_turn_result_with_state_guard(session_id, request)
    changed_files = list(getattr(result, "changed_files", []) or [])
    return bool(changed_files), changed_files


@app.post("/api/v2/sessions/{session_id}/turn", response_model=LocalTurnResponse)
def run_local_lmstudio_turn(session_id: str, req: LocalTurnRequest) -> LocalTurnResponse:
    sid = base.safe_session_id(session_id)
    _ensure_session(sid, req.auto_create_session)

    prompt_bundle, statuses = _build_prompt_bundle(sid, req.user_input, req.mode)

    try:
        ai_result = generate_ai_response(req.ai_provider, prompt_bundle)
    except AIProviderError as exc:
        return LocalTurnResponse(
            success=False,
            session_id=sid,
            mode=req.mode,
            dry_run=req.dry_run,
            provider=req.ai_provider or os.getenv("AI_PROVIDER", "env/default"),
            scene_text="",
            required_files_status=statuses,
            prompt_bundle=prompt_bundle if req.include_prompt_bundle else None,
            error=str(exc),
        )

    scene_text = _clean_scene_text(str(ai_result.get("scene_text", "")))
    changes = ai_result.get("state_changes", {}) if isinstance(ai_result.get("state_changes"), dict) else {}

    issues = _scene_quality_issues(scene_text)
    if issues and str(ai_result.get("provider", "")).lower() not in {"mock", "dry", "test"}:
        repair_bundle = dict(prompt_bundle)
        repair_bundle["quality_repair_required"] = True
        repair_bundle["quality_repair_issues"] = issues
        repair_bundle["failed_scene_excerpt"] = scene_text[:2200]
        repair_bundle["system_prompt"] = (
            str(prompt_bundle.get("system_prompt", ""))
            + "\n\nSTYLE-GATE FAILED. Перепиши сцену заново: без API/status/debug, без generic, с живыми реакциями персонажей, "
            + "с bold speaker names, нижними блоками и разными последствиями действий. Верни только JSON object."
        )
        try:
            repaired = generate_ai_response(req.ai_provider, repair_bundle)
            repaired_text = _clean_scene_text(str(repaired.get("scene_text", "")))
            if repaired_text and len(_scene_quality_issues(repaired_text)) <= len(issues):
                ai_result = repaired
                scene_text = repaired_text
                changes = repaired.get("state_changes", {}) if isinstance(repaired.get("state_changes"), dict) else {}
        except AIProviderError:
            pass

    applied = False
    changed_files: list[str] = []
    if req.save_result and scene_text:
        applied, changed_files = _apply_state_changes(sid, scene_text, changes, req.dry_run)

    return LocalTurnResponse(
        success=True,
        session_id=sid,
        mode=req.mode,
        dry_run=req.dry_run,
        provider=str(ai_result.get("provider", req.ai_provider or "mock")),
        scene_text=scene_text,
        state_changes_applied=applied,
        changed_files=changed_files,
        required_files_status=statuses,
        prompt_bundle=prompt_bundle if req.include_prompt_bundle else None,
    )


app.version = LOCAL_RUNTIME_VERSION

_ORIGINAL_OPENAPI = app.openapi


def _openapi_with_local_turn() -> dict[str, Any]:
    schema = _ORIGINAL_OPENAPI()
    if not isinstance(schema, dict):
        schema = {}
    schema.setdefault("components", {}).setdefault("schemas", {})
    schema["components"]["schemas"]["LocalTurnRequest"] = LocalTurnRequest.model_json_schema()
    schema["components"]["schemas"]["LocalTurnResponse"] = LocalTurnResponse.model_json_schema()
    schema.setdefault("paths", {})["/api/v2/sessions/{session_id}/turn"] = {
        "post": {
            "operationId": "runLocalLmstudioTurn",
            "summary": "Generate one gameplay turn with local LM Studio/OpenAI-compatible provider",
            "parameters": [
                {
                    "name": "session_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/LocalTurnRequest"}
                    }
                },
            },
            "responses": {
                "200": {
                    "description": "Local model turn result",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LocalTurnResponse"}
                        }
                    },
                }
            },
        }
    }
    return schema


app.openapi_schema = None
app.openapi = _openapi_with_local_turn  # type: ignore[method-assign]
