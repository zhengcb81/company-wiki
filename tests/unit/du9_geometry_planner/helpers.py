"""Hand-calculated DU9 fixture loading plus the frozen baseline event stream.

This module deliberately does NOT import the planner package: the RED root-cause
module must stay collectible and runnable before the capability exists.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "du9_geometry_planner"
    / "fixture_geometry_planner.json"
)


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def windows_by_key(fixture: dict) -> dict[str, dict]:
    return {window["window_key"]: window for window in fixture["windows"]}


def covering_windows(fixture: dict, page: int) -> list[str]:
    """Every fixture window whose declared range covers ``page``, declaration order."""
    return [
        window["window_key"]
        for window in fixture["windows"]
        if window["physical_start"] <= page <= window["physical_end"]
    ]


def all_candidate_events(fixture: dict) -> list[tuple[int, list[str]]]:
    """Sequential physical-page arrival, every page an observed candidate.

    Mirrors ROOT's well-formed behavior: each arrival carries every covering
    window key (declaration order; the planner must canonicalize itself).
    """
    return [
        (page, covering_windows(fixture, page))
        for page in range(1, fixture["page_count"] + 1)
    ]


def legacy_front_greedy_admissions(fixture: dict) -> dict[str, list[int]]:
    """The diagnosed production behavior: front-first requests until the shared
    64-page fine-geometry limit dies. No class reservations, no fairness.

    This is the root-cause baseline DU9 exists to replace; it is frozen here as
    documentation and as the RED counterparty for the independent expectation.
    """
    limit = fixture["limits"]["max_pages"]
    budget = limit
    admitted: dict[str, list[int]] = {}
    for window in sorted(
        fixture["windows"],
        key=lambda w: (w["physical_start"], w["window_key"]),
    ):
        for page in range(window["physical_start"], window["physical_end"] + 1):
            if budget <= 0:
                return admitted
            budget -= 1
            admitted.setdefault(window["window_key"], []).append(page)
    return admitted


def class_of_window(fixture: dict, window_key: str) -> str:
    window = windows_by_key(fixture)[window_key]
    rule = {
        rule["rule_key"]: rule for rule in fixture["policy"]["rules"]
    }[window["rule_key"]]
    return rule["geometry_intent"]["demand_class"]


def admitted_by_class(fixture: dict, admitted: dict[str, list[int]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for window_key, pages in admitted.items():
        counts[class_of_window(fixture, window_key)] = (
            counts.get(class_of_window(fixture, window_key), 0) + len(pages)
        )
    return counts
