"""A: RED contract — gold anchors must be where their gold says they are.

Real inconsistency class ``重复/错SHA/错页行`` from the card. The mechanism is
:mod:`tests.anchor_verify`: an independent extraction of the bound original
must contain each anchor's ``exact_quote`` at the location the anchor claims.

Measured on 2026-10-15 against the packaged gold set (317 checkable anchors):

* ``cn-equity/f-phase-two-timeline`` claims page 62 for a quote that sits on
  page 61 — a real wrong-page anchor;
* ``cn-q-sparse/f-cashflow-up-is-not-growth`` claims page 2 for two table
  numbers that sit on page 1 — a real wrong-page anchor;
* four further anchors cannot be checked by independent extraction at all
  (a scanned page with no text layer, CID mojibake, a checkbox glyph and an
  inline-XBRL split) and are recorded as unverifiable, not silently passed.

Old gold files are never edited: the corrections record keeps the old value
replayable and states the measured truth, per INTERFACES (``改错金标需单独更正
记录和版本，旧值仍可回放``). The new DU5 set must be born correct and gets no
correction allowance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.gold import load_bindings, load_gold_dir

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE = REPO_ROOT / "tools" / "document_understanding_benchmark"
CORRECTIONS_PATH = PACKAGE / "gold_corrections.json"
BINDINGS_CANDIDATES = (
    Path.home() / ".du-bench" / "bindings.local.json",
    REPO_ROOT / ".du-bench-out" / "bindings.local.json",
)

#: Fields a correction record may touch. Anything else would let a correction
#: rewrite the fact itself instead of its location.
CORRECTABLE_FIELDS = {"page", "line", "location_kind", "locator"}


def _corrections() -> dict:
    if not CORRECTIONS_PATH.is_file():
        return {"schema_version": "du-gold-corrections/1", "corrections": [], "unverifiable": []}
    return json.loads(CORRECTIONS_PATH.read_text(encoding="utf8"))


def _bindings() -> dict[str, str]:
    for candidate in BINDINGS_CANDIDATES:
        if candidate.is_file():
            try:
                return load_bindings(candidate)
            except Exception:
                continue
    return {}


def _anchor_key(sample_id: str, fact_id: str, set_index: int, anchor_index: int) -> str:
    return f"{sample_id}/{fact_id}/{set_index}/{anchor_index}"


def test_corrections_record_only_touches_location_fields():
    for correction in _corrections().get("corrections", []):
        changed = set(correction.get("proposed", {}))
        assert changed, correction
        assert changed <= CORRECTABLE_FIELDS, (
            f"correction for {correction.get('fact_id')} rewrites {changed - CORRECTABLE_FIELDS}"
        )
        assert correction.get("kind") in {"wrong_page", "wrong_line"}, correction
        assert correction.get("observed", {}).get("method"), correction
        assert correction.get("status") in {"proposed", "applied"}, correction


def test_every_correction_points_at_a_real_anchor_of_a_packaged_gold():
    records = {record["sample_id"]: record for record in load_gold_dir()}
    for correction in _corrections().get("corrections", []):
        record = records.get(correction["sample_id"])
        assert record is not None, correction
        fact = next(
            (f for f in record["facts"] if f["id"] == correction["fact_id"]), None
        )
        assert fact is not None, correction
        anchors = fact["any_support_sets"][correction["set_index"]]
        anchor = anchors[correction["anchor_index"]]
        assert anchor.get("page") == correction["anchor"]["claimed_page"] or (
            anchor.get("line") == correction["anchor"].get("claimed_line")
        ), f"correction claims a different anchor than gold holds: {correction}"


def test_unverifiable_entries_name_the_reason_and_class():
    for entry in _corrections().get("unverifiable", []):
        assert entry.get("sample_id"), entry
        assert entry.get("class") in {
            "no_text_layer",
            "mojibake_cid",
            "extraction_divergence",
        }, entry
        assert entry.get("reason"), entry


@pytest.mark.real_data
def test_du5_gold_anchors_are_all_resolvable_on_their_bound_originals():
    """New gold must be born correct: no correction allowance for du5-*."""

    if os.environ.get("DU_BENCH_ALLOW_REAL_DATA") != "1":
        pytest.skip("set DU_BENCH_ALLOW_REAL_DATA=1 to verify real originals")
    from tools.document_understanding_benchmark.tests.anchor_verify import (
        verify_gold_anchors,
    )

    bindings = _bindings()
    checked = 0
    misses: list[str] = []
    for record in load_gold_dir():
        sample_id = record["sample_id"]
        if not sample_id.startswith("du5-"):
            continue
        bound = bindings.get(sample_id)
        if not bound or not Path(bound).is_file():
            misses.append(f"{sample_id}: no usable local binding")
            continue
        for row in verify_gold_anchors(record, Path(bound)):
            checked += 1
            if not row["ok"]:
                misses.append(f"{sample_id}/{row['fact_id']} {row['where']}: {row['quote'][:40]!r}")
    assert checked > 0, "no du5 anchor was checked"
    assert not misses, "du5 anchors must verify without corrections: " + "; ".join(misses)


@pytest.mark.real_data
def test_all_gold_anchors_verify_or_are_corrected_with_evidence():
    """Every packaged anchor: verified at its claimed location, or corrected.

    A correction is not a pardon: the test re-measures the correction's own
    claim (the quote must be at the proposed location) and the old gold value
    stays untouched for replay.
    """

    if os.environ.get("DU_BENCH_ALLOW_REAL_DATA") != "1":
        pytest.skip("set DU_BENCH_ALLOW_REAL_DATA=1 to verify real originals")
    from tools.document_understanding_benchmark.tests.anchor_verify import (
        verify_gold_anchors,
    )

    corrections = {
        _anchor_key(c["sample_id"], c["fact_id"], c["set_index"], c["anchor_index"]): c
        for c in _corrections().get("corrections", [])
    }
    unverifiable = {e["sample_id"] for e in _corrections().get("unverifiable", [])}
    bindings = _bindings()
    problems: list[str] = []
    verified_corrections = 0
    for record in load_gold_dir():
        sample_id = record["sample_id"]
        bound = bindings.get(sample_id)
        if not bound or not Path(bound).is_file():
            problems.append(f"{sample_id}: no usable local binding")
            continue
        if sample_id in unverifiable:
            continue
        for row in verify_gold_anchors(record, Path(bound)):
            if row["ok"]:
                continue
            key = _anchor_key(sample_id, row["fact_id"], row["set_index"], row["anchor_index"])
            correction = corrections.get(key)
            if correction is None:
                problems.append(
                    f"{key} {row['where']}: unverified and not in the corrections record"
                )
                continue
            # Re-measure the correction's own claim against the original.
            probe = dict(record)
            proposed = correction["proposed"]
            probe_anchor = {
                "page": proposed.get("page"),
                "line": proposed.get("line"),
                "location_kind": proposed.get("location_kind"),
                "exact_quote": row["quote"],
            }
            probe_fact = {"id": row["fact_id"], "any_support_sets": [[probe_anchor]]}
            probe["facts"] = [probe_fact]
            recheck = verify_gold_anchors(probe, Path(bound))
            if recheck and recheck[0]["ok"]:
                verified_corrections += 1
            else:
                problems.append(f"{key}: correction {proposed} not verifiable either")
    assert not problems, "gold anchors neither verify nor carry evidence: " + "; ".join(problems)
