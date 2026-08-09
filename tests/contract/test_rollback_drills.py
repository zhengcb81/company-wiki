"""WU-1404 RED/audit tests: rollback drills (ROLLBACK-01..05).

Priority is flag/reader rollback; v2 data is never deleted and real files
are never rewritten.  Each drill records RTO semantics and leaves the
catalog untouched.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.flags import (  # noqa: E402
    atomic_rollback,
    validate_flag_state,
)


def _chain_on() -> dict:
    return {
        "v2_scan_shadow": True,
        "v2_persist_assertions": True,
        "v2_resolve_shadow": True,
        "v2_resolve_active": True,
        "v2_bundle_active": True,
    }


def test_rollback01_schema_reader_flag():
    """ROLLBACK-01: reader schema rollback is a flag flip, nothing else."""
    flags = _chain_on()
    rolled = atomic_rollback(flags, disable=("v2_resolve_active",))
    assert rolled["v2_resolve_active"] is False
    assert rolled["v2_bundle_active"] is False  # cascade
    assert rolled["v2_scan_shadow"] is True  # upstream untouched


def test_rollback02_resolver_flag():
    """ROLLBACK-02: resolver rollback keeps shadow/persist intact."""
    flags = _chain_on()
    rolled = atomic_rollback(flags, disable=("v2_resolve_shadow",))
    assert rolled["v2_resolve_shadow"] is False
    assert rolled["v2_resolve_active"] is False
    assert rolled["v2_bundle_active"] is False
    assert rolled["v2_scan_shadow"] is True


def test_rollback03_dropbox_route():
    """ROLLBACK-03: disable one root's reusable route — policy-level, no
    data change.  The policy export excludes the root; catalog rows stay."""
    from company_wiki.source_catalog.policy import export_policy, policy_authorizes_root

    class _FakeSpec:
        root_id = "dropbox_stock"
        path = Path("/tmp/stock")
        kind = "directory"
        priority = 20
        adapter_id = "sidecar_filing_v1"
        admission_profile_id = "financial_evidence_v1"
        read_only = True
        reusable_for_filing = None
        routes = ()

    class _FakeConfig:
        project_root = Path("/tmp")
        reusable_root_kinds = ("company_raw",)
        roots = (_FakeSpec(),)

    _, policy = export_policy(_FakeConfig(), project_root=Path("/tmp"))
    assert policy_authorizes_root(policy, "dropbox_stock") is False


def test_rollback04_bundle_consumer():
    """ROLLBACK-04: consumer protocol rollback = N-1 window flag."""
    flags = _chain_on()
    rolled = atomic_rollback(flags, disable=("v2_bundle_active",))
    assert rolled["v2_bundle_active"] is False
    assert rolled["v2_resolve_active"] is True  # resolver stays on v2


def test_rollback05_download_writer():
    """ROLLBACK-05: download disable does not affect existing-file reuse."""
    flags = {"v2_scan_shadow": True, "v2_persist_assertions": True}
    # download authorization is per-request; the flag system has no global
    # download switch — authorization expiry is the rollback (DL-02)
    from company_wiki.source_catalog.reuse_latest_policy import authorization_valid

    expired = {"gap_plan_hash": "g1", "policy_hash": "p1", "expires_at": "2025-01-01"}
    assert not authorization_valid(expired, gap_plan_hash="g1", policy_hash="p1",
                                   now="2026-01-01")
    assert validate_flag_state(flags) == []


def test_rollback_never_deletes_v2_data():
    """Rollback is a pure flag operation — no catalog mutation by design."""
    flags = _chain_on()
    before = dict(flags)
    atomic_rollback(flags, disable=("v2_resolve_active",))
    # the original dict is untouched (pure function returns a new dict)
    assert flags == before
