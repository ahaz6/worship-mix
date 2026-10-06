"""Console abstraction layer (WORSHIP_MIX.md ch. 11). All console I/O goes through here."""
from __future__ import annotations

from abc import ABC, abstractmethod


class WriteNotAllowed(RuntimeError):
    """Raised when writing while the console is in read-only mode (safety rule #1)."""


class ConsoleAdapter(ABC):
    name: str = "base"

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host, self.port = host, port
        self.write_enabled = False  # Read-only by default!
        self.audit_log: list[dict] = []

    def _guard(self, param: str, old, new) -> None:
        if not self.write_enabled:
            raise WriteNotAllowed(f"{self.name}: write disabled ({param})")
        self.audit_log.append({"param": param, "old": old, "new": new})

    @abstractmethod
    def capabilities(self) -> set[str]: ...

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def set_fader(self, ch: int, db: float, bus: str = "LR") -> None: ...

    @abstractmethod
    async def set_mute(self, ch: int, muted: bool) -> None: ...

    async def set_hpf(self, ch: int, freq_hz: float, on: bool = True) -> None:
        raise NotImplementedError(f"{self.name} cannot set HPF via protocol")

    async def set_peq_band(self, ch: int, band: int, freq_hz: float, gain_db: float, q: float) -> None:
        raise NotImplementedError(f"{self.name} cannot set PEQ via protocol")

    async def set_channel_name(self, ch: int, name: str) -> None:
        raise NotImplementedError

    async def snapshot(self) -> dict:
        return {}

    async def restore(self, snap: dict) -> None: ...
