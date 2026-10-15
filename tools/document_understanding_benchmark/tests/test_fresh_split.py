"""A: RED contract tests for the contamination list, coverage matrix and fresh gold.

The card (DU3-QUALITY §4/§5) asks for three things this module does not yet
have:

1. a **contamination list** that names every sample already inspected by the
   project, so no inspected original can be presented as fresh evidence;
2. a **document-coverage matrix** that separates *real*, *synthetic* and
   *missing* coverage per document shape, where a schema-valid record is not
   proof of semantic coverage;
3. **truly new gold** for one previously unused A-share, H-share and US company,
   with a business-fact support set frozen before the new output is read.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.document_understanding_benchmark.gold import GOLD_DIR, load_gold_dir

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE = REPO_ROOT / "tools" / "document_understanding_benchmark"


# ---------------------------------------------------------------------------
# contamination list
# ---------------------------------------------------------------------------


def test_contamination_list_exists_and_covers_every_existing_sample():
    from tools.document_understanding_benchmark.contamination import (
        CONTAMINATION,
        contraction_covered_sample_ids,
    )

    assert CONTAMINATION["schema_version"] == "du-contamination/1"
    covered = contraction_covered_sample_ids()
    packaged = {record["sample_id"] for record in load_gold_dir()}
    missing = sorted(packaged - covered)
    assert not missing, f"inspected samples not on the contamination list: {missing}"


def test_contamination_list_marks_prior_inspection_honestly():
    from tools.document_understanding_benchmark.contamination import CONTAMINATION

    for row in CONTAMINATION["samples"]:
        assert row["sample_id"]
        assert row["status"] in {"contaminated", "fresh"}
        if row["status"] == "contaminated":
            assert row["why"], f"{row['sample_id']} is contaminated with no reason"
            assert row["used_for"]


def test_fresh_samples_are_declared_fresh_and_used_for_nothing_before():
    from tools.document_understanding_benchmark.contamination import (
        CONTAMINATION,
        fresh_sample_ids,
    )

    fresh = fresh_sample_ids()
    assert fresh, "the card requires at least one genuinely new sample per market"
    by_id = {row["sample_id"]: row for row in CONTAMINATION["samples"]}
    for sample_id in fresh:
        assert by_id[sample_id]["used_for"] == []


# ---------------------------------------------------------------------------
# document coverage matrix
# ---------------------------------------------------------------------------


COVERAGE_BUCKETS = {"real", "synthetic", "missing"}
# The shapes the card names. Each must be present with an explicit state.
REQUIRED_SHAPES = {
    "a_share_annual",
    "a_share_interim",
    "a_share_quarterly",
    "hk_annual",
    "hk_interim",
    "hk_quarterly",
    "us_10k",
    "us_10q",
    "us_20f",
    "us_interim",
    "ipo_prospectus",
    "us_s1_f1",
    "equity_offering",
    "convertible_bond",
    "investor_relations",
    "earnings_call",
    "results_release",
    "presentation_deck",
    "sec_8k_6k_exhibit",
    "amended_filing",
    "low_business_administrative",
}


def test_coverage_matrix_declares_every_required_shape():
    from tools.document_understanding_benchmark.coverage_matrix import DOCUMENT_COVERAGE

    assert DOCUMENT_COVERAGE["schema_version"] == "du-coverage-matrix/1"
    have = {row["shape"] for row in DOCUMENT_COVERAGE["rows"]}
    missing = sorted(REQUIRED_SHAPES - have)
    assert not missing, f"card shapes absent from the matrix: {missing}"


def test_every_coverage_row_is_real_synthetic_or_explicitly_missing():
    from tools.document_understanding_benchmark.coverage_matrix import DOCUMENT_COVERAGE

    for row in DOCUMENT_COVERAGE["rows"]:
        assert row["coverage"] in COVERAGE_BUCKETS, row
        if row["coverage"] == "missing":
            assert row["gap"], f"{row['shape']} is missing with no stated gap"
        if row["coverage"] in {"real", "synthetic"}:
            assert row["sample_ids"], f"{row['shape']} claims coverage with no sample"


def test_schema_validity_is_never_accepted_as_semantic_coverage():
    """A shape whose record only proves the schema must be reported as missing."""

    from tools.document_understanding_benchmark.coverage_matrix import (
        DOCUMENT_COVERAGE,
        semantic_coverage_summary,
    )

    summary = semantic_coverage_summary()
    assert summary["schema_only_shapes"], (
        "the matrix must name shapes covered only by schema-valid records"
    )
    for row in DOCUMENT_COVERAGE["rows"]:
        if row["coverage"] == "synthetic":
            assert row["evidence"] == "synthetic_fixture"


def test_coverage_matrix_names_the_known_absent_us_containers():
    """Old set preserved + new set validated (DU5-CORPUS, 2026-10-15).

    ``us_s1_f1`` and ``amended_filing`` remain missing with their named gaps —
    those old cases are kept, not deleted. ``sec_8k_6k_exhibit`` changed state
    on evidence: DU5 froze a real 8-K container / EX-99.1 exhibit pair
    (du5-us-msft-8k + du5-us-msft-ex991), so the row is now real-backed, and
    the new assertion is that it keeps the container/exhibit separation
    disclosure instead of pretending the gap never existed.
    """

    from tools.document_understanding_benchmark.coverage_matrix import DOCUMENT_COVERAGE

    by_shape = {row["shape"]: row for row in DOCUMENT_COVERAGE["rows"]}
    for shape in ("us_s1_f1", "amended_filing"):
        assert by_shape[shape]["coverage"] == "missing", shape
        assert by_shape[shape]["gap"], shape

    exhibit_row = by_shape["sec_8k_6k_exhibit"]
    assert exhibit_row["coverage"] == "real"
    assert set(exhibit_row["sample_ids"]) == {"du5-us-msft-8k", "du5-us-msft-ex991"}
    assert "REQ-3" in exhibit_row["note"], (
        "the production-side container/attachment acceptance (REQ-3) must stay "
        "open in the row's disclosure even though benchmark coverage is real"
    )


# ---------------------------------------------------------------------------
# fresh gold
# ---------------------------------------------------------------------------


def test_fresh_gold_records_exist_for_each_market():
    from tools.document_understanding_benchmark.contamination import fresh_sample_ids

    records = {record["sample_id"]: record for record in load_gold_dir()}
    fresh = {sample_id: records[sample_id] for sample_id in fresh_sample_ids()
             if sample_id in records}
    markets = {record.get("market") for record in fresh.values()}
    assert {"CN", "HK", "US"} <= markets, f"fresh gold markets incomplete: {markets}"


def test_fresh_gold_is_holdout_and_has_expected_families():
    from tools.document_understanding_benchmark.contamination import fresh_sample_ids

    records = {record["sample_id"]: record for record in load_gold_dir()}
    for sample_id in fresh_sample_ids():
        if sample_id not in records:
            continue
        record = records[sample_id]
        assert record["scope"] == "holdout", sample_id
        assert record["expected_route_families"], sample_id
        assert record["facts"], sample_id


def test_fresh_gold_quote_budget_is_respected():
    from tools.document_understanding_benchmark.contamination import fresh_sample_ids

    records = {record["sample_id"]: record for record in load_gold_dir()}
    for sample_id in fresh_sample_ids():
        if sample_id not in records:
            continue
        assert records[sample_id]["gold_quote_chars"] <= 8 * 1024, sample_id


def test_fresh_gold_was_frozen_before_the_new_output_was_read():
    """The support set must be recorded with a freeze marker and a digest."""

    from tools.document_understanding_benchmark.contamination import fresh_sample_ids

    for sample_id in fresh_sample_ids():
        path = GOLD_DIR / f"{sample_id}.json"
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf8"))
        assert raw.get("support_set_frozen_before_output") is True, sample_id
        assert raw.get("support_set_digest"), sample_id


def test_fresh_gold_support_digest_matches_its_facts():
    """The freeze marker must be checkable, not decorative."""

    from tools.document_understanding_benchmark.contamination import (
        fresh_sample_ids,
        support_set_digest,
    )

    for sample_id in fresh_sample_ids():
        path = GOLD_DIR / f"{sample_id}.json"
        if not path.is_file():
            continue
        raw = json.loads(path.read_text(encoding="utf8"))
        assert support_set_digest(raw) == raw["support_set_digest"], sample_id


def test_fresh_gold_binds_to_a_real_original_sha():
    """Every fresh record carries a real SHA, resolvable through local bindings."""

    from tools.document_understanding_benchmark.contamination import fresh_sample_ids
    from tools.document_understanding_benchmark.gold import GoldError, load_bindings

    candidates = (
        Path.home() / ".du-bench" / "bindings.local.json",
        REPO_ROOT / ".du-bench-out" / "bindings.local.json",
    )
    bindings: dict[str, str] = {}
    for candidate in candidates:
        if candidate.is_file():
            try:
                bindings = load_bindings(candidate)
            except GoldError:
                bindings = {}
            break
    if not bindings:
        pytest.skip("no local bindings file on this host")

    records = {record["sample_id"]: record for record in load_gold_dir()}
    bound = 0
    for sample_id in fresh_sample_ids():
        record = records.get(sample_id)
        if record is None:
            continue
        path = bindings.get(sample_id)
        if not path or not Path(path).is_file():
            continue
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert actual == record["source_sha256"], f"{sample_id} SHA drift"
        bound += 1
    assert bound > 0, "no fresh gold record had a usable local binding"


def test_new_companies_do_not_reuse_a_company_already_in_the_benchmark():
    """Fresh means a company, not just a new file for a known company.

    The known set is taken from the contamination list (which names the company
    of every previously inspected sample), not from the gold records: only the
    fresh gold carries a ``company`` field, so building the known set from gold
    would silently yield ``{None}`` and let any company through.
    """

    from tools.document_understanding_benchmark.contamination import (
        CONTAMINATION,
        contamination_by_id,
        fresh_sample_ids,
    )

    fresh = fresh_sample_ids()
    known = {
        row["company"]
        for row in CONTAMINATION["samples"]
        if row["status"] == "contaminated" and row.get("company")
    }
    assert known, "contamination list must name the companies already used"
    records = {record["sample_id"]: record for record in load_gold_dir()}
    for sample_id in fresh:
        record = records.get(sample_id)
        if record is None:
            continue
        company = record.get("company") or contamination_by_id()[sample_id].get("company")
        assert company not in known, (
            f"{sample_id} reuses {company}, which the benchmark already used"
        )


def test_every_real_coverage_row_names_a_known_real_sample():
    """A 'real' coverage row must cite samples the project actually holds.

    The matrix's rule is "real => a named sample on the contamination list with a
    real local original". Enforced here so a row cannot claim real coverage from
    an invented sample id; carrying gold facts is a separate axis.
    """

    from tools.document_understanding_benchmark.contamination import (
        contraction_covered_sample_ids,
    )
    from tools.document_understanding_benchmark.coverage_matrix import (
        DOCUMENT_COVERAGE,
        REAL,
    )

    known = contraction_covered_sample_ids()
    offenders: list[str] = []
    for row in DOCUMENT_COVERAGE["rows"]:
        if row["coverage"] != REAL:
            continue
        for sample_id in row["sample_ids"]:
            if sample_id not in known:
                offenders.append(f"{row['shape']}->{sample_id}")
    assert not offenders, f"real coverage cites samples not on the contamination list: {offenders}"
