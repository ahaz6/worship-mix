"""Module 5 - preset library loader + deterministic scene builder."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

PRESET_DIR = Path(os.environ.get("WM_PRESET_DIR", Path(__file__).resolve().parents[3] / "presets"))


def load_presets() -> dict[str, dict]:
    data = yaml.safe_load((PRESET_DIR / "instruments.yaml").read_text(encoding="utf-8"))
    return data["instruments"]


def build_scene(lineup: list[dict]) -> list[dict]:
    """lineup: [{"name": "Lead Vocal Agi", "instrument": "lead_vocal_m"}, ...]"""
    presets = load_presets()
    scene = []
    for ch, item in enumerate(lineup, start=1):
        p = presets.get(item["instrument"], {})
        scene.append({"channel": ch, "name": item["name"][:12], "instrument": item["instrument"], **p})
    return scene
