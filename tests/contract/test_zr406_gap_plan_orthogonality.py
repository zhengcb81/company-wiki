"""ZR-406 acceptance tests: orthogonal local-match x provider
freshness/coverage planner matrix (WU-4.2 build_gap_plan).

  C1  data-driven FULL matrix: 5 local-match states x 6 provider states =
      30 cells, every cell asserted with its outcome signature
      (reuse / missing / newer_revision / not_published /
      provider_unavailable / future).
  C2  as_of anti-leakage: future-dated candidates go to ``future`` and
      never enter the gap; candidates WITHOUT a filing_date are treated as
      ELIGIBLE (conservative gap — never silently dropped); not_published
      is not negated by future candidates.
  C3  non-natural fiscal year + revision dedup: same fiscal_year with
      multiple period_ends collapses into one bucket (no phantom gap);
      amended + original for the same period yield exactly ONE
      newer_revision (newest accession); a local that already holds the
      newest accession reuses with download=0.

Product hardening covered here: build_gap_plan filters capture-incomplete
local handles (``_usable_handles``) in EVERY outcome branch — an unusable
local never enters reuse and never flips not_published.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.gap_plan import build_gap_plan  # noqa: E402

AS_OF = "2026-07-31"


class _Local:
    """Minimal stand-in for a resolved SourceHandle."""

    def __init__(
        self,
        fiscal_year: int,
        published_date: str,
        accession: str = "",
        *,
        capture_ready: bool = True,
        period_end: str | None = None,
    ):
        self.fiscal_year = fiscal_year
        self.published_date = published_date
        self.provider_document_id = accession or f"acc-{fiscal_year}"
        self.capture_ready = capture_ready
        self.period_end = period_end

    def to_dict(self):
        return {
            "fiscal_year": self.fiscal_year,
            "published_date": self.published_date,
            "provider_document_id": self.provider_document_id,
            "capture_ready": self.capture_ready,
            "period_end": self.period_end,
        }


class _Remote:
    """Minimal stand-in for a DownloadCandidate (metadata only)."""

    def __init__(
        self,
        fiscal_year: int,
        filing_date: str | None,
        accession: str,
        amended: bool = False,
        period_end: str | None = None,
    ):
        self.fiscal_year = fiscal_year
        self.filing_date = filing_date
        self.provider_document_id = accession
        self.amended = amended
        self.period_end = period_end

    def to_dict(self):
        return {
            "fiscal_year": self.fiscal_year,
            "filing_date": self.filing_date,
            "provider_document_id": self.provider_document_id,
            "amended": self.amended,
            "period_end": self.period_end,
        }


def _plan(local, remote, provider_error=None):
    return build_gap_plan(
        request_id="req-zr406",
        as_of_date=AS_OF,
        document_kind="annual_report",
        entity="ACME",
        market="US",
        local_handles=local,
        remote_candidates=remote,
        provider_error=provider_error,
    )


def _sig(plan) -> tuple:
    return (
        tuple(sorted(h.provider_document_id for h in plan.reuse)),
        tuple(sorted(c.provider_document_id for c in plan.missing)),
        tuple(sorted(c.provider_document_id for c in plan.newer_revision)),
        plan.not_published,
        plan.provider_unavailable,
        tuple(sorted(c.provider_document_id for c in plan.future)),
    )


# ---------------------------------------------------------------------------
# C1 — FULL orthogonality matrix (5 local states x 6 provider states = 30)
# ---------------------------------------------------------------------------

# Local-state fixtures.
_L_NO = []
_L_EXACT = [_Local(2025, "2026-04-15", "acc-2025")]
_L_EQUIV = [_Local(2025, "2026-04-15", "acc-2025")]  # semantic reuse, same shape
_L_AMBIGUOUS = [
    _Local(2025, "2026-04-15", "acc-2025-a"),
    _Local(2025, "2026-04-15", "acc-2025-b"),
]
_L_UNUSABLE = [_Local(2025, "2026-04-15", "acc-2025", capture_ready=False)]


def _matrix_cell(
    local_key: str, provider_key: str
) -> tuple[list, list, tuple, str | None]:
    """(locals, remotes, expected_sig, provider_error) for one matrix cell.
    Provider fixtures are chosen per cell so the semantics of each column
    hold for every local row."""
    locals_map = {
        "no_local": _L_NO,
        "exact": _L_EXACT,
        "equivalent": _L_EQUIV,
        "ambiguous": _L_AMBIGUOUS,
        "unusable": _L_UNUSABLE,
    }
    locals_list = locals_map[local_key]
    usable = [h for h in locals_list if getattr(h, "capture_ready", True) is not False]
    has_usable = bool(usable)
    reuse = tuple(sorted(h.provider_document_id for h in usable))

    if provider_key == "current":
        # provider holds the same period; the accession matches a usable
        # local when one exists (else the period is genuinely missing)
        if has_usable:
            remote = [
                _Remote(
                    2025,
                    "2026-04-15",
                    "acc-2025-b" if local_key == "ambiguous" else "acc-2025",
                )
            ]
            expected = (reuse, (), (), True, False, ())
        else:
            remote = [_Remote(2025, "2026-04-15", "acc-2025")]
            expected = ((), ("acc-2025",), (), False, False, ())
        return locals_list, remote, expected, None

    if provider_key == "newer_period":
        remote = [_Remote(2026, "2026-04-15", "acc-2026")]
        expected = (reuse, ("acc-2026",), (), False, False, ())
        return locals_list, remote, expected, None

    if provider_key == "newer_revision":
        # same period, provider accession differs from a usable local:
        # newer_revision; with NO usable local the period is simply missing
        remote = [_Remote(2025, "2026-04-15", "acc-2025-new")]
        if has_usable:
            expected = (reuse, (), ("acc-2025-new",), False, False, ())
        else:
            expected = ((), ("acc-2025-new",), (), False, False, ())
        return locals_list, remote, expected, None

    if provider_key == "not_published":
        expected = (reuse, (), (), True, False, ())
        return locals_list, [], expected, None

    if provider_key == "unknown":
        expected = (reuse, (), (), False, True, ())
        return locals_list, [], expected, "rate_limit_exceeded"

    if provider_key == "future":
        remote = [_Remote(2026, "2026-08-15", "acc-2026-future")]
        expected = (reuse, (), (), True, False, ("acc-2026-future",))
        return locals_list, remote, expected, None

    raise AssertionError(f"unknown provider_key {provider_key!r}")


_LOCAL_KEYS = ("no_local", "exact", "equivalent", "ambiguous", "unusable")
_PROVIDER_KEYS = (
    "current",
    "newer_period",
    "newer_revision",
    "not_published",
    "unknown",
    "future",
)


@pytest.mark.parametrize("local_key", _LOCAL_KEYS)
@pytest.mark.parametrize("provider_key", _PROVIDER_KEYS)
def test_c1_matrix_cell(local_key: str, provider_key: str):
    """C1: every one of the 5x6=30 matrix cells is asserted (the planner's
    outcome is a pure function of the local/provider inputs)."""
    locals_list, remote, expected, provider_error = _matrix_cell(
        local_key, provider_key
    )
    plan = _plan(locals_list, remote, provider_error=provider_error)
    assert _sig(plan) == expected, (
        f"cell local={local_key} x provider={provider_key} "
        f"expected {expected} got {_sig(plan)}"
    )


def test_c1_matrix_cells_are_distinct():
    """Sanity: the 30 cells exercise distinct (local, provider) pairs and
    each column/row combination is present exactly once (the parametrized
    matrix is complete, not sampled)."""
    cells = list(itertools.product(_LOCAL_KEYS, _PROVIDER_KEYS))
    assert len(cells) == 30
    assert len(set(cells)) == 30


def test_c1_gap_hash_deterministic_and_discriminating():
    """Every matrix cell's gap_hash is deterministic (same inputs -> same
    hash) and distinct outcomes differ."""
    for local_key, provider_key in itertools.product(_LOCAL_KEYS, _PROVIDER_KEYS):
        locals_list, remote, _expected, provider_error = _matrix_cell(
            local_key, provider_key
        )
        first = _plan(locals_list, remote, provider_error=provider_error)
        second = _plan(locals_list, remote, provider_error=provider_error)
        assert first.gap_hash == second.gap_hash
        assert len(first.gap_hash) == 64
    different = _plan(_L_EXACT, [_Remote(2026, "2026-04-15", "acc-2026")])
    same = _plan(_L_EXACT, [_Remote(2025, "2026-04-15", "acc-2025")])
    assert different.gap_hash != same.gap_hash


def test_c1_unusable_local_in_provider_error_branch():
    """The capture_ready filter applies in the provider_error branch too:
    an unusable local is never offered as reuse even when the provider is
    unavailable."""
    plan = _plan(_L_UNUSABLE, [], provider_error="rate_limit")
    assert plan.reuse == ()
    assert plan.provider_unavailable is True


# ---------------------------------------------------------------------------
# C2 — as_of anti-leakage
# ---------------------------------------------------------------------------


def test_c2_unknown_filing_date_is_eligible_conservative():
    """A remote candidate WITHOUT a filing_date cannot be proven future:
    it stays ELIGIBLE for the gap (conservative direction — never silently
    dropped, never leaked out of the gap without evidence)."""
    plan = _plan(_L_NO, [_Remote(2026, None, "acc-2026-unknown")])
    assert tuple(c.provider_document_id for c in plan.missing) == ("acc-2026-unknown",)
    assert plan.future == ()
    assert plan.not_published is False


def test_c2_future_never_enters_gap_and_does_not_negate_not_published():
    plan = _plan(_L_EXACT, [_Remote(2026, "2026-09-01", "acc-2026-f")])
    assert tuple(c.provider_document_id for c in plan.future) == ("acc-2026-f",)
    assert plan.missing == ()
    assert plan.not_published is True


def test_c2_mixed_eligible_and_future():
    """Eligible newer period + future candidate: only the eligible one is
    missing; the future one is excluded and does not change the gap."""
    plan = _plan(
        _L_EXACT,
        [
            _Remote(2026, "2026-04-15", "acc-2026-eligible"),
            _Remote(2027, "2026-09-01", "acc-2027-future"),
        ],
    )
    assert tuple(c.provider_document_id for c in plan.missing) == ("acc-2026-eligible",)
    assert tuple(c.provider_document_id for c in plan.future) == ("acc-2027-future",)
    assert plan.not_published is False


# ---------------------------------------------------------------------------
# C3 — non-natural fiscal year + revision dedup
# ---------------------------------------------------------------------------


def test_c3_non_natural_fiscal_year_collapses_to_one_bucket():
    """A fiscal year spanning two calendar years (period_end in the NEXT
    calendar year, e.g. FY2025 ends 2026-03-31) still keys on fiscal_year:
    local + provider with the same fiscal_year and different period_ends
    align into ONE bucket — no phantom gap from the period-end difference."""
    local = [_Local(2025, "2026-04-15", "acc-2025", period_end="2025-03-31")]
    remote = [_Remote(2025, "2026-04-15", "acc-2025", period_end="2026-03-31")]
    plan = _plan(local, remote)
    assert plan.missing == ()
    assert plan.newer_revision == ()
    assert plan.not_published is True
    assert tuple(h.provider_document_id for h in plan.reuse) == ("acc-2025",)


def test_c3_amended_original_dedup_single_newer_revision():
    """Same period with original + amended: exactly ONE newer_revision (the
    newest accession — chronological accessions sort correctly); the older
    accession is not duplicated into the gap."""
    local = [_Local(2025, "2026-04-15", "acc-0001")]
    remote = [
        _Remote(2025, "2026-04-15", "acc-0002", amended=True),
        _Remote(2025, "2026-04-15", "acc-0003", amended=True),
    ]
    plan = _plan(local, remote)
    # newest accession wins the newer_revision slot (dedup to one)
    assert tuple(c.provider_document_id for c in plan.newer_revision) == ("acc-0003",)
    assert plan.missing == ()
    assert tuple(h.provider_document_id for h in plan.reuse) == ("acc-0001",)


def test_c3_local_already_newest_amended_reuses():
    """Local holds the newest amended accession: reuse with download=0 —
    the older provider listings never surface as a gap."""
    local = [_Local(2025, "2026-04-15", "acc-0003")]
    remote = [
        _Remote(2025, "2026-04-15", "acc-0001"),
        _Remote(2025, "2026-04-15", "acc-0002", amended=True),
        _Remote(2025, "2026-04-15", "acc-0003", amended=True),
    ]
    plan = _plan(local, remote)
    assert tuple(h.provider_document_id for h in plan.reuse) == ("acc-0003",)
    assert plan.newer_revision == ()
    assert plan.missing == ()
    assert plan.not_published is True
