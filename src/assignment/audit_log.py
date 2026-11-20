"""
Assignment 11 — Audit Log starter (TODO).

Records every interaction for forensics. Never blocks by itself —
other layers catch attacks; this layer makes them reviewable.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def default_audit_log_path() -> str:
    """Always resolve to <repo>/outputs/… (safe when cwd is src/)."""
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "outputs" / "audit_log.json")


class AuditLogPlugin:
    """Framework-agnostic audit logger (wire into ADK callbacks or your pipeline)."""

    def __init__(self):
        self.name = "audit_log"
        self.logs: list[dict] = []
        self._open: dict[str, float] = {}

    def record_input(self, *, user_id: str, text: str, request_id: str | None = None):
        """Store input and start timestamp keyed by request ID."""
        rid = request_id or str(uuid.uuid4())
        self._open[rid] = time.monotonic()
        self.logs.append({"request_id": rid, "user_id": user_id, "input": text, "started_at": utc_now_iso()})
        return rid

    def record_output(
        self,
        *,
        user_id: str,
        text: str,
        blocked: bool = False,
        layer: str | None = None,
        request_id: str | None = None,
    ):
        """Store output, decision and latency alongside its input entry."""
        rid = request_id
        if rid is None:
            rid = next((row["request_id"] for row in reversed(self.logs) if row.get("user_id") == user_id and "output" not in row), None)
        row = next((row for row in reversed(self.logs) if row.get("request_id") == rid), None)
        if row is None:
            rid = rid or str(uuid.uuid4())
            row = {"request_id": rid, "user_id": user_id, "started_at": utc_now_iso()}
            self.logs.append(row)
        row.update({"output": text, "blocked": bool(blocked), "layer": layer, "latency_ms": round((time.monotonic() - self._open.pop(rid, time.monotonic())) * 1000, 2), "completed_at": utc_now_iso()})

    def export_json(self, filepath: str | None = None):
        """Write logs to disk (JSON array) under repo-root ``outputs/`` by default."""
        path = Path(filepath or default_audit_log_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.logs, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
