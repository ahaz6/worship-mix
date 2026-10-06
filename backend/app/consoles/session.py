"""Writing to a console safely (WORSHIP_MIX.md ch. 15).

- Read-only until `allow_writes(True)`.
- Every apply: snapshot (query current values) -> ramped writes -> audit log.
- Gains move in small steps over ~0.6 s (no audible jumps, Design-Art 10).
- `undo()` restores the last snapshot the same gentle way.
- Consoles without processing control return manual steps instead.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.consoles.changes import Change, describe

RAMP_PARAMS = ("/g", "/trim", "/thr", "/fader")   # continuous values that are ramped
RAMP_STEPS = 6
RAMP_SECONDS = 0.6


class WriteDisabled(RuntimeError):
    pass


@dataclass
class ConsoleSession:
    kind: str
    host: str
    port: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    write_enabled: bool = False
    audit: list[dict] = field(default_factory=list)
    undo_stack: list[dict] = field(default_factory=list)
    client: object | None = None
    mock_state: dict = field(default_factory=dict)

    # -- connection ---------------------------------------------------------
    def connect(self) -> dict:
        if self.kind == "behringer-x32":
            from app.consoles.x32 import OscClient
            self.client = OscClient(self.host, self.port or 10023)
            info = self.client.query("/info")
            return {"connected": info is not None, "info": info,
                    "note": None if info else "No answer from the console. Check IP and network."}
        if self.kind == "allen-heath-sq":
            return {"connected": True, "info": "SQ (MIDI over TCP 51325)",
                    "note": "SQ does not accept EQ, gate, compressor or gain over MIDI. "
                            "Worship Mix shows the exact steps to enter by hand."}
        return {"connected": True, "info": "Mock console", "note": "Simulated console for practice."}

    @property
    def can_write_processing(self) -> bool:
        return self.kind in ("behringer-x32", "mock")

    # -- planning -----------------------------------------------------------
    def plan(self, changes: list[Change]) -> dict:
        steps = [describe(c) for c in changes]
        if not self.can_write_processing:
            return {"mode": "manual", "steps": steps, "messages": []}
        msgs = [m for c in changes for m in self._translate(c)]
        manual = [describe(c) for c in changes if not self._translate(c)]
        return {"mode": "write", "steps": steps, "messages": [{"address": a, "value": v} for a, v in msgs],
                "manual_steps": manual}

    def _translate(self, c: Change):
        from app.consoles.x32 import x32_messages
        return x32_messages(c)  # mock speaks the same address space for practice

    # -- io -----------------------------------------------------------------
    def _read(self, address: str):
        if self.kind == "mock":
            return self.mock_state.get(address)
        return self.client.query(address)  # type: ignore[union-attr]

    def _write(self, address: str, value) -> None:
        if self.kind == "mock":
            self.mock_state[address] = value
        else:
            self.client.send(address, value)  # type: ignore[union-attr]

    def _ramp(self, address: str, old, new, sleep: bool) -> None:
        if isinstance(old, float) and isinstance(new, float) and address.endswith(RAMP_PARAMS):
            for i in range(1, RAMP_STEPS + 1):
                self._write(address, old + (new - old) * i / RAMP_STEPS)
                if sleep:
                    time.sleep(RAMP_SECONDS / RAMP_STEPS)
        else:
            self._write(address, new)

    def apply(self, changes: list[Change], source: str = "user", sleep: bool = True) -> dict:
        plan = self.plan(changes)
        if plan["mode"] == "manual":
            return {**plan, "applied": 0}
        if not self.write_enabled:
            raise WriteDisabled("Writing is off. Tap 'Allow writes' first.")
        msgs = [(m["address"], m["value"]) for m in plan["messages"]]
        snapshot = {a: self._read(a) for a, _ in msgs}
        self.undo_stack.append(snapshot)
        for a, v in msgs:
            old = snapshot.get(a)
            self._ramp(a, old if old is not None else v, v, sleep)
            self.audit.append({"ts": time.time(), "source": source, "address": a, "old": old, "new": v})
        return {**plan, "applied": len(msgs), "undo_available": True}

    def undo(self, sleep: bool = True) -> dict:
        if not self.undo_stack:
            return {"restored": 0}
        if not self.write_enabled:
            raise WriteDisabled("Writing is off. Tap 'Allow writes' first.")
        snap = self.undo_stack.pop()
        n = 0
        for a, old in snap.items():
            if old is None:
                continue
            cur = self._read(a)
            self._ramp(a, cur if cur is not None else old, old, sleep)
            self.audit.append({"ts": time.time(), "source": "undo", "address": a, "old": None, "new": old})
            n += 1
        return {"restored": n}


SESSIONS: dict[str, ConsoleSession] = {}
