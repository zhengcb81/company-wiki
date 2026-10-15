"""A: RED contract — the coverage inventory must separate its five axes.

The card's real inconsistency class #1 is ``coverage 名称存在但 gold 不在``:
the matrix collapses five different axes into one ``REAL`` claim —

1. a real original exists for the sample,
2. a loadable gold record exists for it,
3. the original is actually readable through a public entry point,
4. an observation actually selected evidence from it,
5. a formal summary was independently reviewed.

Measured example of the collapse (not hypothetical): ``a_share_annual`` states
"均在真实原件上有金标事实" while citing ``cn-annual``, which has never had a
gold file; ``us_10q`` is cited as ``REAL`` although its sample has no gold and
the historical measurement recorded the US HTML route as ``units=0``. A name
plus a contamination row is not gold coverage, and this module is where that
must become machine-checkable.

This is the DU5-CORPUS package's first real behaviour RED: it reads only
packaged data and must fail for the inconsistency above, not for an import
error. It turns green when ``coverage_matrix`` declares per-sample axes and
the rows stop presenting name-only samples as gold-backed evidence.
"""

from __future__ import annotations

from tools.document_understanding_benchmark.contamination import (
    contraction_covered_sample_ids,
)
from tools.document_understanding_benchmark.coverage_matrix import (
    DOCUMENT_COVERAGE,
    REAL,
    semantic_coverage_summary,
)
from tools.document_understanding_benchmark.gold import load_gold_dir

#: The axes the card names. Each is measured separately and none may be
#: inferred from another.
AXES = ("original", "gold", "readable", "selected", "summary_reviewed")
AXIS_VALUES = {"yes", "no", "unknown"}


def _gold_sample_ids() -> set[str]:
    return {record["sample_id"] for record in load_gold_dir()}


def test_every_coverage_row_declares_per_sample_axes():
    """Each cited sample must carry an explicit five-axis declaration.

    Absent declarations are exactly the old collapsed claim: a reader cannot
    tell whether ``REAL`` means "a file exists", "gold exists" or "measured
    readable".
    """

    problems: list[str] = []
    for row in DOCUMENT_COVERAGE["rows"]:
        axes = row.get("sample_axes")
        if not isinstance(axes, dict):
            problems.append(f"{row['shape']}: no sample_axes declaration")
            continue
        for sample_id in row["sample_ids"]:
            declared = axes.get(sample_id)
            if not isinstance(declared, dict):
                problems.append(f"{row['shape']}->{sample_id}: not declared")
                continue
            for axis in AXES:
                value = declared.get(axis)
                if value not in AXIS_VALUES:
                    problems.append(
                        f"{row['shape']}->{sample_id}: axis {axis}={value!r} "
                        f"must be one of {sorted(AXIS_VALUES)}"
                    )
    assert not problems, "coverage rows lack per-sample axes: " + "; ".join(problems)


def test_gold_axis_is_true_iff_a_loadable_gold_record_exists():
    """The gold axis must agree with the gold directory, not with the row text."""

    gold_ids = _gold_sample_ids()
    problems: list[str] = []
    for row in DOCUMENT_COVERAGE["rows"]:
        for sample_id, declared in (row.get("sample_axes") or {}).items():
            expected = "yes" if sample_id in gold_ids else "no"
            if declared.get("gold") != expected:
                problems.append(
                    f"{row['shape']}->{sample_id}: gold axis "
                    f"{declared.get('gold')!r} but loadable gold says {expected}"
                )
    assert not problems, "gold axis disagrees with packaged gold: " + "; ".join(problems)


def test_original_axis_requires_the_sample_on_the_contamination_list():
    """A declared real original must at least name the sample the project holds."""

    known = contraction_covered_sample_ids()
    problems: list[str] = []
    for row in DOCUMENT_COVERAGE["rows"]:
        for sample_id, declared in (row.get("sample_axes") or {}).items():
            if declared.get("original") == "yes" and sample_id not in known:
                problems.append(f"{row['shape']}->{sample_id}")
    assert not problems, (
        "rows claim a real original for samples the project does not hold: "
        + "; ".join(problems)
    )


def test_no_real_row_presents_name_only_samples_as_gold_coverage():
    """A REAL row must not claim gold backing from a sample with no gold.

    Concretely: if every cited sample has ``gold == "no"``, the row's evidence
    is a named original only, and its label must say so — it may not carry the
    ``real_original`` evidence tag that the matrix documents as "a named sample
    … (whether it also carries gold facts is a separate axis)" while its note
    speaks of 金标事实.
    """

    problems: list[str] = []
    for row in DOCUMENT_COVERAGE["rows"]:
        if row["coverage"] != REAL:
            continue
        axes = row.get("sample_axes") or {}
        gold_backed = [
            sample_id
            for sample_id in row["sample_ids"]
            if (axes.get(sample_id) or {}).get("gold") == "yes"
        ]
        note = row.get("note") or ""
        claims_gold = "金标" in note and "无金标" not in note
        if not gold_backed and claims_gold:
            problems.append(f"{row['shape']}: note claims gold but no gold-backed sample")
        if not gold_backed and row.get("evidence") == "real_original" and "name_only" not in (
            row.get("gap") or ""
        ) and "仅有原件" not in note and "无金标" not in note:
            problems.append(
                f"{row['shape']}: real_original evidence without gold backing "
                "must disclose 无金标/name-only in note or gap"
            )
    assert not problems, "collapsed coverage claims: " + "; ".join(problems)


def test_semantic_coverage_summary_reports_axis_counts_separately():
    """The summary must count axes apart; one merged ``REAL`` count is the bug."""

    summary = semantic_coverage_summary()
    axis_counts = summary.get("axis_counts")
    assert isinstance(axis_counts, dict), "summary has no axis_counts"
    for axis in AXES:
        assert axis in axis_counts, f"axis {axis} missing from summary counts"
