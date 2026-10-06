"""In-memory session store for measurements, custom curves and mic calibration.

TODO(M-persist): move to SQLite (WORSHIP_MIX.md ch. 17) so measurements survive restarts.
"""
from __future__ import annotations

import itertools

import numpy as np

from app.tuning.measure import Measurement

_ids = itertools.count(1)
MEASUREMENTS: dict[str, dict] = {}       # id -> {"label", "m": Measurement, "room": dict}
CUSTOM_CURVES: dict[str, tuple[np.ndarray, np.ndarray]] = {}
MIC_CAL: dict[str, tuple[np.ndarray, np.ndarray] | None] = {"active": None}


def add(label: str, m: Measurement, room: dict | None = None) -> str:
    mid = f"m{next(_ids)}"
    MEASUREMENTS[mid] = {"label": label, "m": m, "room": room or {}}
    return mid


def get(mid: str) -> Measurement:
    if mid not in MEASUREMENTS:
        raise KeyError(mid)
    return MEASUREMENTS[mid]["m"]
