#!/usr/bin/env python3
"""Smoke diagnostics for the Akira Academy Prequel GPT Actions runtime.

This script intentionally checks the exact startup chain used by the Custom GPT:
health -> createSession -> getSessionContext -> getSessionTurnContract
-> getRequiredFilesManifest -> getRequiredFilesChunk loop.

It also verifies that /openapi.json exposes the stable GPT operationIds.
This is important because Custom GPT imports tools from OpenAPI. If the live
schema exposes FastAPI-generated names like root__get instead of health or
getSessionContext, the runtime can be healthy while the GPT still cannot start.

Modes:
- --local: import app.server and run endpoints with FastAPI TestClient.
- --live-url URL: call a deployed Railway/public API URL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "gpt" / "actions_schema_minimal_with_bundle_openapi_3_1.json"
EXPECTED_OPERATION_IDS = {
    "health",
    "createSession",
    "getSessionContext",
    "getSessionTurnContract",
    "getRequiredFilesManifest",
    "getRequiredFilesChunk",
    "getRequiredFilesBundle",
    "getSessionJson",
    "getProjectFile",
    "repairSceneRoster",
    "applyTurnResult",
}
FORBIDDEN_FASTAPI_OPERATION_IDS = {
    "root__get",
    "list_sessions_api_v1_sessions_get",
    "session_context_api_v1_sessions__session_id__context_get",
    "repair_session_start_state_api_v1_sessions__session_id__repair_start_state_post",
}
EXPECTED_LOCAL_ROUTES = {
    ("GET", "/health"),
    ("POST", "/api/v1/sessions"),
    ("GET", "/api/v1/sessions/{session_id}/context"),
    ("GET", "/api/v1/sessions/{session_id}/turn-contract"),
    ("GET", "/api/v1/sessions/{session_id}/required-files-manifest"),
    ("GET", "/api/v1/sessions/{session_id}/required-files-chunk"),
    ("POST", "/api/v1/sessions/{session_id}/apply-turn-result"),
}


def fail(message: str, *, details: Any | None = None) -> None:
    print(f"\n❌ SMOKE FAIL: {message}", file=sys.stderr)
    if details is not None:
        if not isinstance(details, str):
            details = json.dumps(details, ensure_ascii=False, indent=2, default=str)
        print(details, file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"✅ {message}")


def load_static_schema() -> dict[str, Any]:
    if not SCHEMA_PATH.exists():
        fail("Static GPT Actions schema file is missing", details=str(SCHEMA_PATH))
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail("Static GPT Actions schema is not valid JSON", details=str(exc))
    return schema


def extract_operation_ids(schema: dict[str, Any]) -> set[str]:
    paths = schema.get("paths")
    if not isinstance(paths, dict) or not paths:
        fail("OpenAPI schema has no paths", details=schema)

    operation_ids: set[str] = set()
    for _path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, spec in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            if isinstance(spec, dict) and spec.get("operationId"):
                operation_ids.add(str(spec["operationId"]))
    return operation_ids


def check_schema_operation_ids(schema: dict[str, Any], *, label: str) -> None:
    operation_ids = extract_operation_ids(schema)
    missing = sorted(EXPECTED_OPERATION_IDS - operation_ids)
    forbidden = sorted(operation_ids & FORBIDDEN_FASTAPI_OPERATION_IDS)
    if missing or forbidden:
        fail(
            f"{label} OpenAPI schema exposes wrong tool operations",
            details={
                "missing_required_operationIds": missing,
                "forbidden_fastapi_operationIds": forbidden,
                "seen_operationIds": sorted(operation_ids),
            },
        )
    ok(f"{label} OpenAPI schema contains stable GPT operationIds")


def check_static_schema() -> None:
    check_schema_operation_ids(load_static_schema(), label="static")


def import_local_app():
    # Important: DATA_DIR must be isolated before importing app.server because the app seeds data on startup.
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="akira-smoke-data-"))
    os.environ.setdefault("PUBLIC_BASE_URL", "https://akira-academy-prequel-production.up.railway.app")

    try:
        from app.server import app  # type: ignore
    except Exception as exc:
        fail("Cannot import app.server:app", details=repr(exc))
    return app


def check_local_routes(app) -> None:
    seen: set[tuple[str, str]] = set()
    route_dump: list[dict[str, Any]] = []
    for route in getattr(app, "router", object()).routes:
        path = getattr(route, "path", None)
        methods = sorted(getattr(route, "methods", []) or [])
        operation_id = getattr(route, "operation_id", None)
        route_dump.append({"path": path, "methods": methods, "operation_id": operation_id})
        for method in methods:
            seen.add((method, path))

    missing = sorted(EXPECTED_LOCAL_ROUTES - seen)
    if missing:
        fail("Runtime app is missing required local routes", details={"missing": missing, "routes": route_dump})

    ok("local app.server exposes required routes")


def make_local_requester(app) -> Callable[[str, str, Any | None], tuple[int, Any]]:
    try:
        from fastapi.testclient import TestClient  # type: ignore
    except Exception as exc:
        fail("Cannot import FastAPI TestClient. Install httpx in CI.", details=repr(exc))

    client = TestClient(app)

    def request(method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
        response = client.request(method, path, json=body)
        text = response.text
        try:
            data = response.json()
        except Exception:
            data = text
        return response.status_code, data

    return request


def make_live_requester(base_url: str) -> Callable[[str, str, Any | None], tuple[int, Any]]:
    base = base_url.rstrip("/")

    def request(method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
        payload = None
        headers = {"Accept": "application/json"}
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{base}{path}", data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8", "replace")
                try:
                    return resp.status, json.loads(raw)
                except Exception:
                    return resp.status, raw
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                data: Any = json.loads(raw)
            except Exception:
                data = raw
            return exc.code, data
        except Exception as exc:
            fail(f"Live request failed: {method} {base}{path}", details=repr(exc))

    return request


def assert_status(status: int, data: Any, method: str, path: str) -> None:
    if status < 200 or status >= 300:
        fail(f"Endpoint returned non-2xx: {method} {path}", details={"status": status, "response": data})


def run_toolflow(request: Callable[[str, str, Any | None], tuple[int, Any]], *, mode_label: str) -> None:
    print(f"\n=== {mode_label}: live/imported OpenAPI ===")
    status, openapi = request("GET", "/openapi.json", None)
    assert_status(status, openapi, "GET", "/openapi.json")
    if not isinstance(openapi, dict):
        fail("/openapi.json did not return an object", details=openapi)
    check_schema_operation_ids(openapi, label=mode_label)

    print(f"\n=== {mode_label}: health ===")
    status, health = request("GET", "/health", None)
    assert_status(status, health, "GET", "/health")
    if not isinstance(health, dict) or health.get("status") != "ok":
        fail("Health response is not usable", details=health)
    ok(f"{mode_label}: health ok ({health.get('version') or health.get('app')})")

    print(f"\n=== {mode_label}: createSession ===")
    status, session = request("POST", "/api/v1/sessions", {})
    assert_status(status, session, "POST", "/api/v1/sessions")
    if not isinstance(session, dict) or not session.get("session_id"):
        fail("createSession did not return session_id", details=session)
    sid = str(session["session_id"])
    ok(f"{mode_label}: session created: {sid}")

    print(f"\n=== {mode_label}: getSessionContext ===")
    status, context = request("GET", f"/api/v1/sessions/{sid}/context", None)
    assert_status(status, context, "GET", f"/api/v1/sessions/{sid}/context")
    if not isinstance(context, dict):
        fail("getSessionContext did not return an object", details=context)
    current_state = context.get("current_state")
    if not isinstance(current_state, dict) or not current_state:
        fail("getSessionContext returned empty/missing current_state", details=context)
    if current_state.get("project_slug") != "akira-academy-prequel":
        fail("current_state.project_slug is wrong or missing", details=current_state)
    ok(f"{mode_label}: context has current_state")

    print(f"\n=== {mode_label}: getSessionTurnContract ===")
    status, contract = request("GET", f"/api/v1/sessions/{sid}/turn-contract", None)
    assert_status(status, contract, "GET", f"/api/v1/sessions/{sid}/turn-contract")
    if not isinstance(contract, dict):
        fail("getSessionTurnContract did not return an object", details=contract)
    required_files = contract.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        fail("turn-contract has empty/missing required_files", details=contract)
    if not contract.get("output_format_contract"):
        fail("turn-contract has empty/missing output_format_contract", details=contract)
    ok(f"{mode_label}: turn contract ok, required_files={len(required_files)}")

    print(f"\n=== {mode_label}: getRequiredFilesManifest ===")
    status, manifest = request("GET", f"/api/v1/sessions/{sid}/required-files-manifest", None)
    assert_status(status, manifest, "GET", f"/api/v1/sessions/{sid}/required-files-manifest")
    if not isinstance(manifest, dict):
        fail("manifest did not return an object", details=manifest)
    missing_count = int(manifest.get("missing_count") or 0)
    chunks_total = int(manifest.get("chunks_total") or 0)
    if chunks_total <= 0:
        fail("manifest reports zero chunks", details=manifest)
    if missing_count > 0:
        fail("manifest reports missing required files", details=manifest)
    ok(f"{mode_label}: manifest ok, chunks_total={chunks_total}")

    print(f"\n=== {mode_label}: getRequiredFilesChunk loop ===")
    chunk_index = 0
    loaded_paths: set[str] = set()
    guard = 0
    while True:
        guard += 1
        if guard > 50:
            fail("chunk loop exceeded safety guard")
        status, chunk = request(
            "GET",
            f"/api/v1/sessions/{sid}/required-files-chunk?chunk_index={chunk_index}&max_chars=30000&max_items=3",
            None,
        )
        assert_status(status, chunk, "GET", "/required-files-chunk")
        if not isinstance(chunk, dict):
            fail("chunk did not return an object", details=chunk)
        loaded_files = chunk.get("loaded_files")
        if not isinstance(loaded_files, list) or not loaded_files:
            fail("chunk has empty/missing loaded_files", details=chunk)
        for item in loaded_files:
            if isinstance(item, dict) and item.get("path"):
                loaded_paths.add(str(item["path"]))
        if not chunk.get("has_more"):
            break
        next_index = chunk.get("next_chunk_index")
        if not isinstance(next_index, int):
            fail("chunk has has_more=true but invalid next_chunk_index", details=chunk)
        chunk_index = next_index

    if not loaded_paths:
        fail("no required files were loaded through chunks")
    ok(f"{mode_label}: chunks loaded {len(loaded_paths)} unique files")

    print(f"\n=== {mode_label}: result ===")
    print(json.dumps({
        "mode": mode_label,
        "session_id": sid,
        "health": health,
        "loaded_paths_sample": sorted(loaded_paths)[:20],
        "loaded_paths_count": len(loaded_paths),
    }, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Run diagnostics against imported app.server")
    parser.add_argument("--live-url", default="", help="Run diagnostics against deployed API base URL")
    args = parser.parse_args()

    check_static_schema()

    if args.local:
        app = import_local_app()
        check_local_routes(app)
        run_toolflow(make_local_requester(app), mode_label="local")

    if args.live_url:
        # Railway can need a moment after deploy; do one short retry cycle for first health call.
        time.sleep(2)
        run_toolflow(make_live_requester(args.live_url), mode_label="live")

    if not args.local and not args.live_url:
        fail("Nothing to run. Use --local and/or --live-url URL.")


if __name__ == "__main__":
    main()
