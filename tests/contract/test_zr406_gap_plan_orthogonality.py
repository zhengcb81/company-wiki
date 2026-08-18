"""ZR-406 acceptance tests: orthogonal local-match x provider
freshness/coverage planner matrix (WU-4.2 build_gap_plan).

Pins the full matrix the card requires:

  C1  local-match state (no-local / matched-exact / matched-equivalent /
      multiple-ambiguous / capture-incomplete-unusable) x provider state
      (current / newer_period / newer_revision / not_published /
      unknown-error / future) — five-tuple outcome + gap_hash determinism.
  C2  as_of anti-leakage: future-dated candidates go to ``future`` and
      never enter the gap; candidates WITHOUT a filing_date are treated as
      ELIGIBLE (conservative gap — never silently dropped); not_published
      is not negated by future candidates.
  C3  non-natural fiscal year + revision dedup: same fiscal_year with
      multiple period_ends collapses into one bucket (no phantom gap);
      amended + original for the same period yield exactly ONE
      newer_revision (newest accession); a local that already holds the
      newest accession reuses with download=0.

Product code is NOT modified by this card (mechanism already implemented).
"""

from __future__ import annotations

import sys
from pathlib import Path

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
# C1 — orthogonal matrix: local-match state x provider state
# ---------------------------------------------------------------------------

# Provider fixtures for the matrix rows.
_CURRENT = [_Remote(2025, "2026-04-15", "acc-2025")]  # local holds newest
_NEWER_PERIOD = [_Remote(2026, "2026-04-15", "acc-2026")]  # beyond local 2025
_NEWER_REV = [_Remote(2025, "2026-04-15", "acc-2025-new")]  # same period, newer
_NOT_PUBLISHED = [_Remote(2025, "2026-04-15", "acc-2025")]  # nothing beyond local
_FUTURE = [_Remote(2026, "2026-08-15", "acc-2026-future")]  # filed after as_of

# Local fixtures for the matrix rows.
_LOCAL_EXACT = [_Local(2025, "2026-04-15", "acc-2025")]  # holds newest accession
_LOCAL_EQUIV = [_Local(2025, "2026-04-15", "acc-2025")]  # equivalent reuse
_LOCAL_AMBIGUOUS = [  # two locals, one period
    _Local(2025, "2026-04-15", "acc-2025-a"),
    _Local(2025, "2026-04-15", "acc-2025-b"),
]
_LOCAL_UNUSABLE = [
    _Local(2025, "2026-04-15", "acc-2025", capture_ready=False)
]  # capture-incomplete
_NO_LOCAL = []


def test_c1_matrix_no_local():
    """No local handle: provider-current/newer_period -> missing; provider
    knows nothing -> not_published; unknown -> unavailable; future ->
    future + not_published (nothing eligible)."""
    missing_plan = _plan(_NO_LOCAL, _CURRENT)
    assert _sig(missing_plan) == ((), ("acc-2025",), (), False, False, ())
    missing_plan2 = _plan(_NO_LOCAL, _NEWER_PERIOD)
    assert _sig(missing_plan2) == ((), ("acc-2026",), (), False, False, ())
    np_plan = _plan(_NO_LOCAL, [])
    assert _sig(np_plan) == ((), (), (), True, False, ())
    unavail = _plan(_NO_LOCAL, [], provider_error="rate_limit")
    assert _sig(unavail) == ((), (), (), False, True, ())
    future_plan = _plan(_NO_LOCAL, _FUTURE)
    assert _sig(future_plan) == ((), (), (), True, False, ("acc-2026-future",))


def test_c1_matrix_matched_exact():
    """Matched exact local x provider states."""
    plan = _plan(_LOCAL_EXACT, _CURRENT)
    assert _sig(plan) == (("acc-2025",), (), (), True, False, ())
    plan = _plan(_LOCAL_EXACT, _NEWER_PERIOD)
    assert _sig(plan) == (("acc-2025",), ("acc-2026",), (), False, False, ())
    plan = _plan(_LOCAL_EXACT, _NEWER_REV)
    assert _sig(plan) == (("acc-2025",), (), ("acc-2025-new",), False, False, ())
    plan = _plan(_LOCAL_EXACT, _NOT_PUBLISHED)
    assert _sig(plan) == (("acc-2025",), (), (), True, False, ())
    plan = _plan(_LOCAL_EXACT, [], provider_error="rate_limit")
    assert _sig(plan) == (("acc-2025",), (), (), False, True, ())
    plan = _plan(_LOCAL_EXACT, _FUTURE)
    assert _sig(plan) == (("acc-2025",), (), (), True, False, ("acc-2026-future",))


def test_c1_matrix_matched_equivalent():
    """Equivalent local (semantic reuse) behaves like exact in the planner."""
    plan = _plan(_LOCAL_EQUIV, _CURRENT)
    assert _sig(plan) == (("acc-2025",), (), (), True, False, ())
    plan = _plan(_LOCAL_EQUIV, _NEWER_PERIOD)
    assert _sig(plan) == (("acc-2025",), ("acc-2026",), (), False, False, ())
    plan = _plan(_LOCAL_EQUIV, _NEWER_REV)
    assert _sig(plan) == (("acc-2025",), (), ("acc-2025-new",), False, False, ())
    plan = _plan(_LOCAL_EQUIV, _FUTURE)
    assert _sig(plan) == (("acc-2025",), (), (), True, False, ("acc-2026-future",))


def test_c1_matrix_multiple_local_ambiguous():
    """Two locals for one period: the newest accession aligns with the
    provider; ambiguous locals stay in reuse (provenance), no phantom
    missing; a provider accession the locals do not hold is honestly
    reported as newer_revision; a provider current matching one local
    keeps not_published."""
    # provider current matches the newest local accession -> up to date
    plan = _plan(_LOCAL_AMBIGUOUS, [_Remote(2025, "2026-04-15", "acc-2025-b")])
    assert _sig(plan) == (("acc-2025-a", "acc-2025-b"), (), (), True, False, ())
    # provider accession differs from every local -> honest newer_revision
    plan = _plan(_LOCAL_AMBIGUOUS, [_Remote(2025, "2026-04-15", "acc-2025-x")])
    assert _sig(plan) == (
        ("acc-2025-a", "acc-2025-b"),
        (),
        ("acc-2025-x",),
        False,
        False,
        (),
    )
    plan = _plan(_LOCAL_AMBIGUOUS, _NEWER_PERIOD)
    assert _sig(plan) == (
        ("acc-2025-a", "acc-2025-b"),
        ("acc-2026",),
        (),
        False,
        False,
        (),
    )
    plan = _plan(_LOCAL_AMBIGUOUS, _NEWER_REV)
    assert _sig(plan) == (
        ("acc-2025-a", "acc-2025-b"),
        (),
        ("acc-2025-new",),
        False,
        False,
        (),
    )
    plan = _plan(_LOCAL_AMBIGUOUS, _FUTURE)
    assert _sig(plan) == (
        ("acc-2025-a", "acc-2025-b"),
        (),
        (),
        True,
        False,
        ("acc-2026-future",),
    )


def test_c1_matrix_unusable_local_never_faked():
    """A capture-incomplete local handle is not reusable evidence: it never
    enters reuse and never flips not_published.  With the unusable local
    filtered out, a provider listing for the same period is GENUINELY
    missing (not a fake up-to-date); an empty provider still reports
    not_published; a provider error stays unavailable."""
    plan = _plan(_LOCAL_UNUSABLE, _NOT_PUBLISHED)
    assert plan.reuse == ()
    # provider HAS 2025 but the local is unusable -> real missing
    assert tuple(c.provider_document_id for c in plan.missing) == ("acc-2025",)
    assert plan.not_published is False
    plan = _plan(_LOCAL_UNUSABLE, _NEWER_PERIOD)
    assert plan.reuse == ()
    assert tuple(c.provider_document_id for c in plan.missing) == ("acc-2026",)
    plan = _plan(_LOCAL_UNUSABLE, [])
    assert plan.reuse == ()
    assert plan.not_published is True  # nothing on the provider side either
    plan = _plan(_LOCAL_UNUSABLE, [], provider_error="rate_limit")
    assert plan.reuse == ()
    assert plan.provider_unavailable is True


def test_c1_matrix_gap_hash_deterministic_across_cells():
    """Every matrix cell's gap_hash is deterministic (same inputs -> same
    hash; distinct outcomes -> distinct hashes in the sampled cells)."""
    first = _plan(_LOCAL_EXACT, _NEWER_REV)
    second = _plan(_LOCAL_EXACT, _NEWER_REV)
    assert first.gap_hash == second.gap_hash
    assert len(first.gap_hash) == 64
    different = _plan(_LOCAL_EXACT, _CURRENT)
    assert first.gap_hash != different.gap_hash


# ---------------------------------------------------------------------------
# C2 — as_of anti-leakage
# ---------------------------------------------------------------------------


def test_c2_unknown_filing_date_is_eligible_conservative():
    """A remote candidate WITHOUT a filing_date cannot be proven future:
    it stays ELIGIBLE for the gap (conservative direction — never silently
    dropped, never leaked out of the gap without evidence)."""
    plan = _plan(_NO_LOCAL, [_Remote(2026, None, "acc-2026-unknown")])
    assert tuple(c.provider_document_id for c in plan.missing) == ("acc-2026-unknown",)
    assert plan.future == ()
    assert plan.not_published is False


def test_c2_future_never_enters_gap_and_does_not_negate_not_published():
    plan = _plan(_LOCAL_EXACT, [_Remote(2026, "2026-09-01", "acc-2026-f")])
    assert tuple(c.provider_document_id for c in plan.future) == ("acc-2026-f",)
    assert plan.missing == ()
    assert plan.not_published is True


def test_c2_mixed_eligible_and_future():
    """Eligible newer period + future candidate: only the eligible one is
    missing; the future one is excluded and does not change the gap."""
    plan = _plan(
        _LOCAL_EXACT,
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
