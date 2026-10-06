"""Console connection + safe writing API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.consoles.changes import Change
from app.consoles.session import SESSIONS, ConsoleSession, WriteDisabled

router = APIRouter(prefix="/consoles", tags=["consoles"])

KINDS = {
    "mock": {"label": "Mock console (practice)", "port": 0, "writes_processing": True},
    "behringer-x32": {"label": "Behringer X32 / Midas M32", "port": 10023, "writes_processing": True},
    "allen-heath-sq": {"label": "Allen & Heath SQ (manual steps)", "port": 51325, "writes_processing": False},
}


class ConnectIn(BaseModel):
    kind: str
    host: str = "127.0.0.1"
    port: int | None = None


class ChangeIn(BaseModel):
    target: str
    param: str
    value: dict
    note: str = ""


class ChangesIn(BaseModel):
    changes: list[ChangeIn]


def _session(sid: str) -> ConsoleSession:
    if sid not in SESSIONS:
        raise HTTPException(404, "Console session not found. Connect again.")
    return SESSIONS[sid]


def _changes(body: ChangesIn) -> list[Change]:
    return [Change(c.target, c.param, c.value, c.note) for c in body.changes]


@router.get("/kinds")
def kinds() -> dict:
    return KINDS


@router.post("/connect")
def connect(body: ConnectIn) -> dict:
    if body.kind not in KINDS:
        raise HTTPException(400, "Unknown console type.")
    s = ConsoleSession(body.kind, body.host, body.port or KINDS[body.kind]["port"])
    info = s.connect()
    SESSIONS[s.id] = s
    return {"session": s.id, "kind": s.kind, "write_enabled": False, **info,
            "writes_processing": KINDS[body.kind]["writes_processing"]}


@router.post("/{sid}/writes")
def set_writes(sid: str, enabled: bool) -> dict:
    s = _session(sid)
    s.write_enabled = enabled
    return {"write_enabled": s.write_enabled}


@router.post("/{sid}/plan")
def plan(sid: str, body: ChangesIn) -> dict:
    return _session(sid).plan(_changes(body))


@router.post("/{sid}/apply")
def apply(sid: str, body: ChangesIn) -> dict:
    try:
        return _session(sid).apply(_changes(body))
    except WriteDisabled as e:
        raise HTTPException(409, str(e)) from e


@router.post("/{sid}/undo")
def undo(sid: str) -> dict:
    try:
        return _session(sid).undo()
    except WriteDisabled as e:
        raise HTTPException(409, str(e)) from e


@router.get("/{sid}/audit")
def audit(sid: str) -> list[dict]:
    return _session(sid).audit[-200:]
