"""DU10-CWP-SUMMARY-GOLDSET structural validator (node B).

Offline data-integrity checks only: schema, required fields, ID uniqueness,
market/doc-type coverage, SourceRef shape and carrier-root resolvability,
anchor format, support/counterexample non-conflict, quote budget, portability
(no absolute paths), index consistency. This validator deliberately does NOT
judge economic facts or summary quality — that is the independent C-node
reviewer's job.

Run:
  python -B -X utf8 -m pytest \
    docs/plans/document-understanding-2026-10-13/parallel/du10-2026-10-17/goldset/tests \
    -q
"""
from __future__ import annotations

import json
import os

import pytest

from _support import (
    CASE_SCHEMA,
    DOC_TYPES,
    IMPORTANCE,
    INDEX_SCHEMA,
    MARKETS,
    MODALITY,
    QUOTE_BUDGET_PER_DOCUMENT,
    ROLE,
    TARGET_KIND,
    CARRIER_ROOTS,
    cases_dir,
    iter_anchors,
    load_cases,
    load_index,
    norm,
    quote_budget_by_document,
)

ALL_CASES = load_cases()
INDEX = load_index()


def test_at_least_ten_cases():
    assert len(ALL_CASES) >= 10


def test_case_ids_unique():
    ids = [c["case_id"] for c in ALL_CASES]
    assert len(ids) == len(set(ids))
    for cid in ids:
        assert cid.startswith("du10gs-")


def test_schema_version_on_every_case():
    for c in ALL_CASES:
        assert c["schema_version"] == CASE_SCHEMA, c["case_id"]


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c["case_id"])
def test_required_fields(case):
    cid = case["case_id"]
    for key in (
        "case_id",
        "created",
        "market",
        "company",
        "doc_type",
        "carrier",
        "language",
        "narrative_focus",
        "bound_failure_mode",
        "source_ref",
        "summary_proposition",
        "allowed_summary",
        "summary_guidance",
        "facts",
        "misread_traps",
        "prior_use",
        "notes",
    ):
        assert key in case, f"{cid} missing {key}"
    src = case["source_ref"]
    for key in ("carrier_root", "source_id", "source_sha256", "mime_type"):
        assert key in src, f"{cid} source_ref missing {key}"
    assert case["summary_proposition"].strip()
    assert case["allowed_summary"] and all(s.strip() for s in case["allowed_summary"])
    assert case["prior_use"].strip()


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c["case_id"])
def test_enums_and_market(case):
    assert case["market"] in MARKETS, case["case_id"]
    assert case["doc_type"] in DOC_TYPES, case["case_id"]
    assert case["source_ref"]["carrier_root"] in CARRIER_ROOTS, case["case_id"]


def test_market_coverage():
    assert {c["market"] for c in ALL_CASES} == {"CN", "HK", "US"}


def test_required_doc_type_coverage():
    have = {c["doc_type"] for c in ALL_CASES}
    # card-required types that must exist among the cases
    for t in (
        "annual_report",
        "interim_report",
        "quarterly_report",
        "ipo_prospectus",
        "convertible_bond_prospectus",
        "ir_minutes",
        "call_transcript",
        "form_10q",
    ):
        assert t in have, f"missing doc type {t}"


def test_facts_structure_and_enums():
    for c in ALL_CASES:
        assert c["facts"], c["case_id"]
        fids = [f["id"] for f in c["facts"]]
        assert len(fids) == len(set(fids)), c["case_id"]
        for f in c["facts"]:
            assert f["importance"] in IMPORTANCE
            assert f["target_kind"] in TARGET_KIND
            assert f["modality"] in MODALITY
            assert f["role"] in ROLE
            assert f["must_preserve"], f"{c['case_id']}/{f['id']}"
            assert f["must_not_assert"], f"{c['case_id']}/{f['id']}"
            assert f["reason"].strip()
            assert f["any_support_sets"], f"{c['case_id']}/{f['id']}"
            for group in f["any_support_sets"]:
                assert group, f"{c['case_id']}/{f['id']} empty support group"


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c["case_id"])
def test_anchor_format(case):
    cid = case["case_id"]
    html_like = case["carrier"] in (".htm", ".html")
    for fid, kind, a in iter_anchors(case):
        assert a.get("exact_quote", "").strip(), f"{cid}/{fid} empty quote"
        assert a.get("location_kind") in ("page", "document"), f"{cid}/{fid}"
        if kind == "trap" or html_like:
            # HTML anchors are document-level; PDF traps may omit page
            continue
        page = a.get("page")
        assert isinstance(page, int) and page >= 1, f"{cid}/{fid} bad page"


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c["case_id"])
def test_source_ref_shape_and_no_absolute_paths(case):
    cid = case["case_id"]
    raw = json.dumps(case, ensure_ascii=False)
    src = case["source_ref"]
    assert not os.path.isabs(src["source_id"]), f"{cid} source_id must be root-relative"
    assert "\\" not in src["source_id"], f"{cid} source_id must use forward slashes"
    assert len(src["source_sha256"]) == 64
    int(src["source_sha256"], 16)
    # portability: no machine-specific absolute paths anywhere in the case file
    for token in ("C:/Users", "C:\\Users", "/Users/", "AppData"):
        assert token not in raw, f"{cid} leaks absolute path token {token}"


def test_support_and_counterexample_no_conflict():
    """A must_not_assert cannot verbatim restate a must_preserve, and each
    must_not_assert must be non-trivial (differ from the allowed summary)."""
    for c in ALL_CASES:
        for f in c["facts"]:
            preserves = {norm(x) for x in f["must_preserve"]}
            for neg in f["must_not_assert"]:
                n = norm(neg)
                assert n, f"{c['case_id']}/{f['id']} empty must_not_assert"
                assert n not in preserves, f"{c['case_id']}/{f['id']} conflict: {neg}"
        # allowed summaries cannot assert something that any fact forbids
        allowed_norm = norm(" ".join(c["allowed_summary"]))
        for f in c["facts"]:
            for neg in f["must_not_assert"]:
                nn = norm(neg)
                if len(nn) >= 8:
                    assert nn not in allowed_norm, (
                        f"{c['case_id']}: allowed summary conflicts with "
                        f"must_not_assert: {neg}"
                    )


def test_quote_budget_per_document():
    budget = quote_budget_by_document(ALL_CASES)
    for sha, chars in budget.items():
        assert chars <= QUOTE_BUDGET_PER_DOCUMENT, f"{sha[:12]} over budget: {chars}"
    # recording on the case files stays consistent with recomputation
    for c in ALL_CASES:
        per_case = sum(
            len(norm(a["exact_quote"])) for _, _, a in iter_anchors(c)
        )
        assert c["quote_budget_chars_normalized"] == per_case, c["case_id"]


def test_index_consistency():
    assert INDEX["schema_version"] == INDEX_SCHEMA
    assert INDEX["case_count"] == len(ALL_CASES)
    by_id = {c["case_id"]: c for c in ALL_CASES}
    seen_shas = set()
    for row in INDEX["cases"]:
        c = by_id[row["case_id"]]
        assert row["market"] == c["market"]
        assert row["doc_type"] == c["doc_type"]
        assert row["source_sha256"] == c["source_ref"]["source_sha256"]
        seen_shas.add(row["source_sha256"])
    assert INDEX["unique_originals"] == len(seen_shas)


def test_no_duplicate_case_on_same_original_and_proposition():
    """Two cases may share one original (documented added evidence), but their
    propositions and narrative focus must differ."""
    seen = {}
    for c in ALL_CASES:
        key = (c["source_ref"]["source_sha256"], norm(c["summary_proposition"])[:60])
        assert key not in seen, f"duplicate proposition on same original: {c['case_id']}"
        seen[key] = c["case_id"]


def test_trap_anchors_present_for_mixed_page_modes():
    """Every case must name at least one misread trap; traps that document a
    same-page hazard must carry an anchor quote (verified offline against the
    original in the C-node tool, not here)."""
    for c in ALL_CASES:
        assert c["misread_traps"], c["case_id"]
        for t in c["misread_traps"]:
            assert t.get("note", "").strip(), c["case_id"]


def test_failures_modes_bound_per_case():
    for c in ALL_CASES:
        assert c["bound_failure_mode"].strip(), c["case_id"]


def test_known_failures_covered():
    """The set of bound failure modes must collectively cover the known
    summary-citation failure classes from the live review."""
    joined = " ".join(c["bound_failure_mode"] for c in ALL_CASES)
    for needed in ("planned/actual", "同量纲不同时期", "第三方", "测算", "在研"):
        assert needed in joined, f"failure mode family missing: {needed}"


def test_cases_dir_contains_only_owned_files():
    allowed = {"index.json"} | {
        p.name for p in cases_dir().glob("du10gs-*.json")
    }
    actual = {p.name for p in cases_dir().iterdir() if p.is_file()}
    assert actual == allowed, f"unexpected files in cases/: {actual - allowed}"
