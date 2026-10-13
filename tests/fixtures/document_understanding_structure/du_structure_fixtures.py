"""Frozen du-input/1 fixture loading for the DU-STRUCTURE lane.

Fixtures are committed JSON, so the lane's tests never depend on the owner's
live catalog, on the network, or on a PDF parser being installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_ROOT = Path(__file__).resolve().parent
INPUT_DIR = FIXTURE_ROOT / "inputs"


def available_inputs() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in INPUT_DIR.glob("*.json")))


def load_input(name: str) -> dict[str, Any]:
    path = INPUT_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"unknown du-input fixture: {name}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != "du-input/1":
        raise ValueError(f"fixture {name} is not du-input/1")
    return payload


def load_observation(name: str) -> dict[str, Any]:
    """Return only the du-input/1 observation fields (fixture metadata dropped)."""
    payload = load_input(name)
    return {
        key: value
        for key, value in payload.items()
        if key in {"schema_version", "source_ref", "metadata", "coverage", "units"}
    }


__all__ = ["FIXTURE_ROOT", "INPUT_DIR", "available_inputs", "load_input", "load_observation"]
