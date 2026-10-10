"""Exact transcript parser versions shared by generation and source replay.

Old layouts are never upgraded in place: the requested saved version retains
its heading, speaker and end-boundary semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TRANSCRIPT_PARSER_VERSION = "0.3.1"
TranscriptLayout = Literal["legacy", "natural", "natural_affiliation", "natural_affiliation_boundary"]
_TRANSCRIPT_PARSER_LAYOUTS: dict[str, TranscriptLayout] = {
    "0.1.0": "legacy",
    "0.1.1": "legacy",
    "0.2.0": "natural",
    "0.3.0": "natural_affiliation",
    "0.3.1": "natural_affiliation_boundary",
}


@dataclass(frozen=True)
class TranscriptParserContract:
    parser_name: str
    parser_version: str
    layout: TranscriptLayout


def transcript_parser_contract(parser_version: str | None = None) -> TranscriptParserContract:
    """Return one exact layout; unknown versions cannot reinterpret old calls."""
    version = TRANSCRIPT_PARSER_VERSION if parser_version is None else parser_version
    if not isinstance(version, str) or version not in _TRANSCRIPT_PARSER_LAYOUTS:
        raise ValueError("unsupported transcript parser version")
    return TranscriptParserContract(
        "selective_narrative_parser", version, _TRANSCRIPT_PARSER_LAYOUTS[version]
    )
