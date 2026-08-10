"""FC-303 RED/acceptance tests: v1/v2 scanner shadow parity over a frozen
corpus.

The runner compares v1 (_scan_root_v1) and v2 (registered adapter) on the
same immutable tree: candidate count, relative paths, roles, content
hashes, entity/kind/status identity and exclusion reasons.  Every
explainable diff must be registered in the migration-rules ledger;
unexplained diffs block.  EX-08 mutation: a future root with a configured
adapter must dispatch via the adapter — never fall back to the legacy
kind-based v1 path.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pytest  # noqa: E402

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _frozen_company_raw(tmp_path: Path) -> Path:
    """A frozen company_raw tree: one company, two primary docs + sidecars,
    one incomplete sidecar (no primary)."""
    raw = tmp_path / "companies" / "Acme" / "raw"
    raw.mkdir(parents=True)
    (raw / "2025.pdf").write_bytes(b"pdf-2025")
    (raw / "2025.source.json").write_text(
        '{"fiscal_year": 2025, "provider": "example"}', encoding="utf-8"
    )
    (raw / "2024.pdf").write_bytes(b"pdf-2024")
    (raw / "orphan.source.json").write_text(
        '{"fiscal_year": 2024}', encoding="utf-8"
    )
    return tmp_path / "companies"


def _frozen_directory(tmp_path: Path) -> Path:
    """A frozen directory root: two docs with one sidecar pair."""
    root = tmp_path / "stock"
    root.mkdir()
    (root / "a.pdf").write_bytes(b"a")
    (root / "a.source.json").write_text(
        '{"fiscal_year": 2025}', encoding="utf-8"
    )
    (root / "b.md").write_bytes(b"b")
    return root


def _company_raw_root(path: Path) -> RootSpec:
    return RootSpec(
        root_id="company_raw",
        path=path,
        kind="company_raw",
        adapter_id="company_raw_v1",
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )


def _directory_root(path: Path) -> RootSpec:
    return RootSpec(
        root_id="dropbox_stock",
        path=path,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )


# --- frozen-corpus parity runner -------------------------------------------


def _register_company_raw_rules(company_root: Path) -> None:
    """FC-303 flow: run parity, register the explainable diffs as migration
    rules, re-run -> ok.  v1 marks sidecar metadata candidates 'incomplete'
    while the v2 adapter emits normalized metadata with 'active' status —
    an explainable semantic difference, not a blocker."""
    from company_wiki.source_catalog.shadow_parity import (
        register_migration_rule,
        reset_migration_ledger,
        run_root_shadow_parity,
    )

    reset_migration_ledger()
    root = _company_raw_root(company_root)
    report = run_root_shadow_parity(root, ("Acme",))
    assert report.total_v1 == report.total_v2, (
        f"candidate count drift: v1={report.total_v1} v2={report.total_v2}"
    )
    for diff in report.blockers:
        if diff.field == "status" and diff.path.endswith(".source.json"):
            register_migration_rule(
                (diff.path, "status"),
                "v1 marks sidecar metadata incomplete; v2 adapter emits normalized metadata with active status (FC-303 migration rule)",
                against=report,
            )
        elif diff.field == "identity" and diff.path.endswith(".source.json"):
            register_migration_rule(
                (diff.path, "identity"),
                "identity hash differs only because source_status differs (same root cause as the status rule)",
                against=report,
            )
        else:
            raise AssertionError(
                f"unexplainable diff: {diff.path}:{diff.field} "
                f"v1={diff.v1_value!r} v2={diff.v2_value!r}"
            )
    report = run_root_shadow_parity(root, ("Acme",))
    assert report.ok, (
        f"still blocking after rules: {[(d.path, d.field) for d in report.blockers]}"
    )


def test_parity_runner_company_raw_explainable_diffs_registered(tmp_path):
    _register_company_raw_rules(_frozen_company_raw(tmp_path))


def test_parity_runner_directory_explainable_diffs_registered(tmp_path):
    """The directory corpus has one explainable diff: v1 emits sidecar
    metadata candidates, the sidecar adapter emits primaries only.  FC-303
    flow: register the rule, re-run -> ok."""
    from company_wiki.source_catalog.shadow_parity import (
        register_migration_rule,
        reset_migration_ledger,
        run_root_shadow_parity,
    )

    reset_migration_ledger()
    root = _directory_root(_frozen_directory(tmp_path))
    report = run_root_shadow_parity(root, ())
    # the presence diff is explainable (v1 emits sidecar metadata; v2
    # adapter emits primaries only) — counts may differ until the rule
    # is registered, then the report must be clean
    for diff in report.blockers:
        if diff.field == "presence" and diff.path.endswith(".source.json"):
            register_migration_rule(
                (diff.path, "presence"),
                "v1 emits sidecar metadata candidates; v2 sidecar adapter emits primaries only (FC-303 migration rule)",
                against=report,
            )
        else:
            raise AssertionError(
                f"unexplainable diff: {diff.path}:{diff.field} "
                f"v1={diff.v1_value!r} v2={diff.v2_value!r}"
            )
    report = run_root_shadow_parity(root, ())
    assert report.ok, (
        f"still blocking after rules: {[(d.path, d.field) for d in report.blockers]}"
    )


def test_parity_runner_compares_content_hashes(tmp_path):
    """The runner must compare content hashes, not just presence/role."""
    from company_wiki.source_catalog.shadow_parity import (
        reset_migration_ledger,
        run_root_shadow_parity,
    )

    reset_migration_ledger()
    corpus = _frozen_company_raw(tmp_path)
    root = _company_raw_root(corpus)
    report = run_root_shadow_parity(root, ("Acme",))
    assert report.total_v1 == report.total_v2
    # after registering the explainable sidecar rules the corpus is clean
    _register_company_raw_rules(corpus)


def test_parity_runner_detects_hash_tamper(tmp_path):
    """Mutation: a v2 candidate with a wrong content hash must be caught
    as an unexplained diff (blocker)."""
    import company_wiki.source_catalog.shadow_parity as sp

    corpus = _frozen_company_raw(tmp_path)
    root = _company_raw_root(corpus)
    original = sp._v2_adapter_candidates

    def tampered(root):
        # declared hash flipped vs the on-disk file (SPI-03 violation)
        items = original(root)
        for item in items:
            if item.relative_path.endswith("2025.pdf"):
                object.__setattr__(item, "content_sha256", "0" * 64)
        return items

    sp._v2_adapter_candidates = tampered
    try:
        report = sp.run_root_shadow_parity(root, ("Acme",))
    finally:
        sp._v2_adapter_candidates = original
    assert not report.ok
    assert any(d.field == "content_sha256" for d in report.diffs)


# --- migration-rules ledger -------------------------------------------------


def test_migration_ledger_holds_explainable_diffs(tmp_path):
    """Every explainable diff must be registered in the ledger; registering
    a rule with no matching diff is a ledger error (no dead entries)."""
    from company_wiki.source_catalog.shadow_parity import (
        register_migration_rule,
        migration_ledger,
        reset_migration_ledger,
        run_root_shadow_parity,
    )

    reset_migration_ledger()
    corpus = _frozen_company_raw(tmp_path)
    _register_company_raw_rules(corpus)  # registers the real rules
    assert len(migration_ledger()) == 4  # 2 paths x (status, identity)
    # a phantom rule must be rejected (no matching diff on the frozen corpus)
    report = run_root_shadow_parity(_company_raw_root(corpus), ("Acme",))
    with pytest.raises(ValueError):
        register_migration_rule(
            ("2025.pdf", "presence"), "phantom rule with no diff",
            against=report,
        )
    # ledger stays unchanged
    assert len(migration_ledger()) == 4


# --- EX-08: future root dispatches via adapter, never legacy fallback ------


def test_ex08_future_root_never_falls_back_to_legacy(tmp_path, monkeypatch):
    """A future root (directory kind + sidecar adapter) must dispatch via
    the registered adapter in the v2 path; falling back to the legacy
    kind-based v1 scanner is forbidden.

    Two guards (FC-303 review F1): (1) an adapter_for invocation spy —
    the v2 path MUST have gone through adapter dispatch, which v1 never
    does; (2) a v2-only marker — the adapter's NormalizedCandidate
    metadata flows into group_metadata, which the v1 scanner for a plain
    file does not carry."""
    from company_wiki.source_catalog import adapter_dispatch
    from company_wiki.source_catalog.scanner import scan_root_strategy

    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    (root_dir / "x.pdf").write_bytes(b"x")
    root = RootSpec(
        root_id="future_lake",
        path=root_dir,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )
    calls: list[str] = []
    original = adapter_dispatch.adapter_for

    def spying_adapter_for(target):
        calls.append(target.root_id)
        return original(target)

    monkeypatch.setattr(adapter_dispatch, "adapter_for", spying_adapter_for)
    candidates, _, _ = scan_root_strategy(root, (), v2_scan_shadow=True)
    assert calls == ["future_lake"], (
        f"v2 path did not dispatch through the adapter (calls={calls}) — "
        f"legacy fallback detected"
    )
    assert any(c.relative_path.endswith("x.pdf") for c in candidates)


def test_ex08_adapter_error_fails_closed_not_legacy_fallback(tmp_path, monkeypatch):
    """EX-08 F1 guard 2: when the adapter itself errors, the v2 path must
    fail closed (ScannerFacadeError) — it must NOT fall back to the legacy
    v1 scanner."""
    from company_wiki.source_catalog import adapter_dispatch
    from company_wiki.source_catalog.scanner import (
        ScannerFacadeError,
        scan_root_strategy,
    )

    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    (root_dir / "x.pdf").write_bytes(b"x")
    root = RootSpec(
        root_id="future_lake",
        path=root_dir,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )

    class _BoomAdapter:
        adapter_id = "sidecar_filing_v1"
        version = "1.0.0"

        def enumerate(self, root_path, *, limit=None):
            raise RuntimeError("adapter exploded")

    monkeypatch.setattr(
        adapter_dispatch, "adapter_for", lambda target: _BoomAdapter()
    )
    with pytest.raises(ScannerFacadeError):
        scan_root_strategy(root, (), v2_scan_shadow=True)


def test_ex08_future_root_unknown_adapter_blocks(tmp_path):
    """An unresolvable future root must fail closed in the v2 path."""
    from company_wiki.source_catalog.scanner import (
        ScannerFacadeError,
        scan_root_strategy,
    )

    root_dir = tmp_path / "future_lake"
    root_dir.mkdir()
    root = RootSpec(
        root_id="future_lake",
        path=root_dir,
        kind="directory",
        adapter_id="not_registered_v1",
        read_only=True,
        reusable_for_filing=True,
    )
    with pytest.raises(ScannerFacadeError):
        scan_root_strategy(root, (), v2_scan_shadow=True)
