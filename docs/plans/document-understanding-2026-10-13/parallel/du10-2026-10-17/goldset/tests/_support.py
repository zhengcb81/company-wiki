"""Shared helpers for DU10-CWP-SUMMARY-GOLDSET tests and the read-only anchor
verifier.

Conventions reused from the existing DU lanes:

- quote comparison is whitespace-normalized (all whitespace removed) both
  sides, matching ``review/deliverables/families`` PDF/HTML rules;
- anchor format follows du-gold/1: ``{page | line, exact_quote}`` plus
  ``location_kind`` (``page`` for PDF physical pages, ``document`` for HTML
  whole-text matching);
- machine-local bindings (absolute paths) are never committed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CASE_SCHEMA = "du10-summary-goldset-case/2"
INDEX_SCHEMA = "du10-summary-goldset-index/2"

MARKETS = {"CN", "HK", "US"}
DOC_TYPES = {
    "annual_report",
    "interim_report",
    "quarterly_report",
    "ipo_prospectus",
    "convertible_bond_prospectus",
    "ir_minutes",
    "call_transcript",
    "form_10q",
}
# vocabulary reused from the existing du-gold/1 corpus
IMPORTANCE = {"critical", "normal"}
TARGET_KIND = {"required_business", "disposition_context", "correctness_if_emitted"}
MODALITY = {"plan", "actual", "unknown", "negation", "question", "conditional", "third_party"}
ROLE = {
    "company_filing",
    "management_answer",
    "analyst_question",
    "company_statement",
    "management_prepared",
    "third_party",
    "editorial_summary",
    "operator",
}
# configured carrier roots; mapping mirrors config/source_catalog.yaml (read-only)
QUOTE_BUDGET_PER_DOCUMENT = 8 * 1024  # du-gold/1: excerpts per document <= 8KiB


def goldset_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def cases_dir() -> Path:
    return goldset_dir() / "cases"


def load_cases() -> list[dict]:
    cases = []
    for p in sorted(cases_dir().glob("du10gs-*.json")):
        cases.append(json.loads(p.read_text(encoding="utf-8")))
    return cases


def load_index() -> dict:
    return json.loads((cases_dir() / "index.json").read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def iter_anchors(case: dict):
    """Yield (fact_id, trap_or_fact, anchor) for every anchor in the case."""
    for fact in case.get("facts", []):
        for group in fact.get("any_support_sets", []):
            for a in group:
                yield fact["id"], "fact", a
    for trap in case.get("misread_traps", []):
        if trap.get("exact_quote"):
            yield trap.get("kind", "trap"), "trap", {
                **{k: trap[k] for k in ("unit_id", "source_locator") if k in trap},
                "page": trap.get("page"),
                "exact_quote": trap["exact_quote"],
                "location_kind": trap.get("location_kind", "page" if trap.get("page") else "document"),
            }


def quote_budget_by_document(cases: list[dict]) -> dict[str, int]:
    """Normalized quote characters per unique source document (du-gold budget)."""
    budget: dict[str, int] = {}
    for case in cases:
        sha = case["source_ref"]["content_sha256"]
        total = 0
        for _, _, a in iter_anchors(case):
            total += len(norm(a["exact_quote"]))
        budget[sha] = budget.get(sha, 0) + total
    return budget
