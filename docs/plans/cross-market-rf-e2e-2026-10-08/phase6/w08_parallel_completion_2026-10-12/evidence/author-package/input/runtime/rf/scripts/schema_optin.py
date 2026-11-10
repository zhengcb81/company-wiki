"""ZR-711: additive schema 3.8 opt-in converter.

3.8 = 3.7 + ``operating_units`` (mine-year operations per ZR-605). The
converter is deliberately boring:

  convert_3_7_to_3_8(doc) — bumps the version and adds
      ``operating_units: []``. The empty list IS the honest gap: the
      converter never guesses, fabricates, or derives mine data from
      segment parameters (no volume×price pseudo revenue).
  convert_3_8_to_3_7(doc) — restores 3.7 and strips every 3.8-only
      additive key. Round-tripping a 3.7 document
      (3.7 → 3.8 → 3.7) yields a document canonically equal to the
      original, so the opt-in flag is fully reversible.
"""

from __future__ import annotations

import copy
from typing import Any

from contracts.constants import FORECAST_SCHEMA_VERSION, OPT_IN_SCHEMA_VERSION
from contracts.evidence import require

# Every schema-3.8-only additive key (stripped on downgrade).
OPT_IN_ONLY_KEYS = ("operating_units",)


def convert_3_7_to_3_8(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a 3.7 document to the 3.8 opt-in schema.

    Adds ``operating_units: []`` — an explicit gap. The converter never
    guesses values: mine-year operations must be authored (or extracted
    upstream), never derived here.
    """
    result = copy.deepcopy(data)
    require(
        result.get("schema_version") == FORECAST_SCHEMA_VERSION,
        f"convert_3_7_to_3_8 requires schema_version {FORECAST_SCHEMA_VERSION}, "
        f"got {result.get('schema_version')!r}",
    )
    result["schema_version"] = OPT_IN_SCHEMA_VERSION
    result.setdefault("operating_units", [])
    return result


def convert_3_8_to_3_7(data: dict[str, Any]) -> dict[str, Any]:
    """Downgrade a 3.8 document back to 3.7 (opt-out / rollback).

    Strips every 3.8-only additive key. A round-tripped 3.7 document is
    canonically equal to its original.
    """
    result = copy.deepcopy(data)
    require(
        result.get("schema_version") == OPT_IN_SCHEMA_VERSION,
        f"convert_3_8_to_3_7 requires schema_version {OPT_IN_SCHEMA_VERSION}, "
        f"got {result.get('schema_version')!r}",
    )
    for key in OPT_IN_ONLY_KEYS:
        result.pop(key, None)
    result["schema_version"] = FORECAST_SCHEMA_VERSION
    return result
