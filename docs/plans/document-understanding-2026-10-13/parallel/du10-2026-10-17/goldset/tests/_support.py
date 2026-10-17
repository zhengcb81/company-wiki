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
import os
import re
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from bs4 import BeautifulSoup  # noqa: F401  (SEC filings are XML-flavored HTML)

CASE_SCHEMA = "du10-summary-goldset-case/1"
INDEX_SCHEMA = "du10-summary-goldset-index/1"

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
CARRIER_ROOTS = {
    "company_raw": ("companies",),
    "dropbox_stock": ("Dropbox", "Stock"),
    "dayu_portfolio": ("dayu-agent", "workspace", "portfolio"),
}
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
                "page": trap.get("page"),
                "exact_quote": trap["exact_quote"],
                "location_kind": trap.get("location_kind", "page" if trap.get("page") else "document"),
            }


def quote_budget_by_document(cases: list[dict]) -> dict[str, int]:
    """Normalized quote characters per unique source document (du-gold budget)."""
    budget: dict[str, int] = {}
    for case in cases:
        sha = case["source_ref"]["source_sha256"]
        total = 0
        for _, _, a in iter_anchors(case):
            total += len(norm(a["exact_quote"]))
        budget[sha] = budget.get(sha, 0) + total
    return budget


def resolve_binding(case: dict, bindings: dict[str, str]) -> str:
    """Resolve a case to its local original via the uncommitted bindings file.

    Returns the absolute path or raises KeyError. The binding must agree with
    the case's carrier root so the read-only resolution stays config-faithful.
    """
    cid = case["case_id"]
    if cid not in bindings:
        raise KeyError(cid)
    path = os.path.abspath(bindings[cid])
    root_parts = CARRIER_ROOTS[case["source_ref"]["carrier_root"]]
    lowered = path.replace("\\", "/").lower()
    marker = "/" + "/".join(root_parts).lower() + "/"
    if marker not in lowered:
        raise ValueError(f"binding for {cid} does not live under carrier root {root_parts}")
    return path


def sha256_file(path: str) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def page_text(path: str, page: int | None, carrier: str) -> str:
    """Read-only extraction. PDF: PyMuPDF page text (1-based physical page) or
    whole document when page is None. HTML: de-tagged text."""
    if carrier == ".pdf":
        import fitz

        doc = fitz.open(path)
        try:
            if page is None:
                return "\n".join(doc[i].get_text("text") for i in range(doc.page_count))
            return doc[page - 1].get_text("text")
        finally:
            doc.close()
    from bs4 import BeautifulSoup

    raw = Path(path).read_bytes()
    return BeautifulSoup(raw, "lxml").get_text("\n")
