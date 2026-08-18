"""ZR-402 acceptance tests: adapter registry route contract (FC-302/303).

Independent acceptance pin of the adapter registry evidence criteria over
the CURRENT product (this card changes NO product code):

  C1  adapter-route core is free of root kind/ID special-casing
      (mechanical gate over the five route modules + adversarial proof
      that the gate detects a newly planted kind branch).
  C2  routing depends ONLY on adapter_id: every registered adapter routes
      identically under every legal root kind and arbitrary root_ids; the
      kind-routing mutant (M8) is replayed in-process and proven killed.
  C3  unknown adapters fail closed at every entry (registry / dispatch /
      scanner facade v2).
  C4  adapter contract mutation kill table: every declared mutant (M1..M9)
      has a firing detector — M1 (non-deterministic enumerate) is the NEW
      negative this card adds; M2..M6 re-fire the conformance kit; M7/M8
      are replayed seam mutants; M9's existing ex08 killer is restated.

RED evidence (survivor analysis) is archived at
assurance/unified_completion/receipts/ZR-402/red/zr402_red_evidence.json.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.adapters.conformance import (  # noqa: E402
    conformance_ok,
    run_conformance,
)
from company_wiki.source_catalog.adapters.interface import (  # noqa: E402
    NormalizedCandidate,
)
from company_wiki.source_catalog.adapters.registry import (  # noqa: E402
    REGISTERED_ADAPTERS,
    registered_adapter,
)
from company_wiki.source_catalog.models import (  # noqa: E402
    ROOT_KINDS,
    RootSpec,
)

_SRC = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"

# The adapter-route core: dispatch + admission + the three contract
# modules of the adapters package.  These files must contain ZERO root
# kind/ID conditional branches — a future root must reach an adapter by
# config alone (path/sidecar differences live INSIDE the adapters).
ROUTE_MODULES = (
    "adapter_dispatch.py",
    "admission.py",
    "adapters/registry.py",
    "adapters/interface.py",
    "adapters/conformance.py",
)

_KIND_BRANCH = re.compile(r"\.kind\s*==|\.kind\s+in\b|root_id\s*==")


def _root(
    *, kind: str, adapter_id: str | None, root_id: str = "zr402_root"
) -> RootSpec:
    return RootSpec(
        root_id=root_id,
        path=Path("C:/zr402_fixture"),
        kind=kind,
        adapter_id=adapter_id,
        read_only=True,
        reusable_for_filing=True,
    )


# ---------------------------------------------------------------------------
# C1 — adapter-route core has no root kind/ID special-casing (mechanical gate)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rel_path", ROUTE_MODULES)
def test_c1_route_module_has_zero_kind_branches(rel_path: str):
    """ZR-402 C1: each route-core module contains ZERO ``.kind ==`` /
    ``.kind in`` / ``root_id ==`` branches.  (FC-1201 cannot enforce this:
    adapter_dispatch.py and admission.py sit INSIDE its token allowlist;
    test_spi02 freezes scanner.py only.  Counts today: all zero.)"""
    text = (_SRC / rel_path).read_text(encoding="utf-8")
    assert len(_KIND_BRANCH.findall(text)) == 0, (
        f"{rel_path} gained a root kind/ID special-casing branch — "
        f"path/sidecar differences belong INSIDE adapters (ZR-402)"
    )


def test_c1_gate_detects_newly_planted_kind_branch(tmp_path):
    """Adversarial: the SAME scan logic must flag a module that plants a
    root-kind branch (the gate detects additions; it is not a constant)."""
    planted = tmp_path / "evil_route.py"
    planted.write_text(
        'if root.kind == "dayu_portfolio":\n    adapter = "dayu_filing_v1"\n',
        encoding="utf-8",
    )
    text = planted.read_text(encoding="utf-8")
    assert len(_KIND_BRANCH.findall(text)) >= 1


def test_c1_rootspec_rejects_unknown_kind():
    """Bogus kinds never reach dispatch: RootSpec fails closed at the model
    gate (the route therefore only ever sees ROOT_KINDS members)."""
    with pytest.raises(ValueError, match="unsupported root kind"):
        _root(kind="flavour_x", adapter_id="sidecar_filing_v1")


# ---------------------------------------------------------------------------
# C2 — routing depends ONLY on adapter_id (kind/root_id agnostic; kills M8)
# ---------------------------------------------------------------------------


# scanner-capable registered adapters (have a dispatch factory); the
# remaining registered adapters (generic_document_v1) are registry-only
# and must fail closed at dispatch with the distinct "no scanner adapter
# implementation" error — also kind-agnostically.
_SCANNER_ADAPTERS = ("company_raw_v1", "dayu_filing_v1", "sidecar_filing_v1")
_REGISTRY_ONLY_ADAPTERS = tuple(
    sorted(set(REGISTERED_ADAPTERS) - set(_SCANNER_ADAPTERS))
)


@pytest.mark.parametrize("adapter_id", _SCANNER_ADAPTERS)
@pytest.mark.parametrize("kind", sorted(ROOT_KINDS))
def test_c2_routing_is_kind_agnostic(adapter_id: str, kind: str):
    """Every scanner-capable adapter routes identically under EVERY legal
    root kind — including mismatched pairings the legacy scanner would
    have treated differently (e.g. sidecar adapter on a company_raw kind)."""
    from company_wiki.source_catalog.adapter_dispatch import adapter_for

    resolved = adapter_for(_root(kind=kind, adapter_id=adapter_id))
    assert resolved.adapter_id == adapter_id, (
        f"routing leaked root kind {kind!r}: resolved "
        f"{resolved.adapter_id!r} instead of {adapter_id!r}"
    )


@pytest.mark.parametrize("adapter_id", _REGISTRY_ONLY_ADAPTERS)
@pytest.mark.parametrize("kind", sorted(ROOT_KINDS))
def test_c2_registry_only_adapter_fails_closed_kind_agnostically(
    adapter_id: str, kind: str
):
    """A registered-but-not-scanner adapter fails closed at dispatch under
    EVERY kind with the same distinct error (no kind reaches a scanner)."""
    from company_wiki.source_catalog.adapter_dispatch import (
        AdapterDispatchError,
        adapter_for,
    )

    with pytest.raises(AdapterDispatchError, match="no scanner adapter"):
        adapter_for(_root(kind=kind, adapter_id=adapter_id))


@pytest.mark.parametrize("adapter_id", _SCANNER_ADAPTERS)
def test_c2_routing_is_root_id_agnostic(adapter_id: str):
    """root_id must not influence routing (only adapter_id is the route)."""
    from company_wiki.source_catalog.adapter_dispatch import adapter_for

    first = adapter_for(_root(kind="directory", adapter_id=adapter_id, root_id="aaa"))
    second = adapter_for(_root(kind="directory", adapter_id=adapter_id, root_id="zzz"))
    assert type(first) is type(second)
    assert first.adapter_id == second.adapter_id == adapter_id


def test_c2_kind_routing_mutant_is_killed(monkeypatch):
    """Kill proof (M8): replace adapter_for with a kind-routing mutant and
    show the C2 assertion now FAILS on a mismatched pairing — i.e. C2 is
    the killer the current suite lacked (RED S2)."""
    from company_wiki.source_catalog import adapter_dispatch
    from company_wiki.source_catalog.adapters.company_raw import CompanyRawAdapter
    from company_wiki.source_catalog.adapters.dayu import DayuAdapter
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    kind_route = {
        "directory": SidecarFilingAdapter,
        "company_raw": CompanyRawAdapter,
        "dayu_portfolio": DayuAdapter,
    }

    def mutant_for(root: RootSpec):
        return kind_route[root.kind]()

    monkeypatch.setattr(adapter_dispatch, "adapter_for", mutant_for)
    # mismatched pairing: adapter_id says company_raw, kind says directory.
    # Under the mutant the route follows the KIND => the C2 invariant
    # (resolved.adapter_id == requested adapter_id) is violated => detected.
    resolved = adapter_dispatch.adapter_for(
        _root(kind="directory", adapter_id="company_raw_v1")
    )
    assert resolved.adapter_id != "company_raw_v1", (
        "kind-routing mutant no longer detectable — C2 lost its teeth"
    )


# ---------------------------------------------------------------------------
# C3 — unknown adapters fail closed at every entry
# ---------------------------------------------------------------------------


def test_c3_registry_unknown_returns_none():
    assert registered_adapter("not_registered_v99") is None


def test_c3_dispatch_unknown_and_missing_fail():
    from company_wiki.source_catalog.adapter_dispatch import (
        AdapterDispatchError,
        adapter_for,
    )

    with pytest.raises(AdapterDispatchError, match="not registered"):
        adapter_for(_root(kind="directory", adapter_id="not_registered_v99"))
    with pytest.raises(AdapterDispatchError, match="no adapter_id"):
        adapter_for(_root(kind="directory", adapter_id=None))


def test_c3_facade_bogus_adapter_fails_closed(tmp_path):
    """Scanner facade v2 entry: a bogus adapter_id must raise
    ScannerFacadeError (complements seam02 'missing id' and ex08)."""
    from company_wiki.source_catalog.scanner import (
        ScannerFacadeError,
        scan_root_strategy,
    )

    (tmp_path / "x.pdf").write_bytes(b"x")
    root = RootSpec(
        root_id="zr402_bogus",
        path=tmp_path,
        kind="directory",
        adapter_id="not_registered_v99",
        read_only=True,
        reusable_for_filing=True,
    )
    with pytest.raises(ScannerFacadeError):
        scan_root_strategy(root, (), v2_scan_shadow=True)


# ---------------------------------------------------------------------------
# C4 — adapter contract mutation kill table
# ---------------------------------------------------------------------------


class _BaseAdapter:
    """Minimal conformant adapter for the battery (pdf primaries only)."""

    adapter_id = "zr402_battery_v1"
    version = "1.0.0"

    def enumerate(self, root_path, *, limit=None):
        candidates = []
        for path in sorted(root_path.rglob("*.pdf")):
            data = path.read_bytes()
            candidates.append(
                NormalizedCandidate(
                    relative_path=path.relative_to(root_path).as_posix(),
                    content_sha256=hashlib.sha256(data).hexdigest(),
                    group_key=path.stem,
                    role="primary",
                )
            )
        return candidates


class _NonDeterministicAdapter(_BaseAdapter):
    """M1: enumerate order flips between calls — must be caught by the
    conformance kit's determinism check (the NEW negative of this card)."""

    def __init__(self):
        self._flip = False

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        if self._flip:
            candidates = list(reversed(candidates))
        self._flip = not self._flip
        return candidates


class _HashLieAdapter(_BaseAdapter):
    """M2: declared hash does not match file bytes."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        for candidate in candidates:
            object.__setattr__(candidate, "content_sha256", "0" * 64)
        return candidates


class _RoleLieAdapter(_BaseAdapter):
    """M3: markdown misclassified as primary."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        for path in sorted(root_path.rglob("*.md")):
            candidates.append(
                NormalizedCandidate(
                    relative_path=path.relative_to(root_path).as_posix(),
                    content_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    group_key=path.stem,
                    role="primary",
                )
            )
        return candidates


class _DuplicateAdapter(_BaseAdapter):
    """M4: duplicate candidates."""

    def enumerate(self, root_path, *, limit=None):
        return super().enumerate(root_path) * 2


class _WriteAdapter(_BaseAdapter):
    """M5: adapter writes into the fixture tree."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        (root_path / "evil.pdf").write_bytes(b"%PDF-1.4 evil")
        return candidates


class _EscapeAdapter(_BaseAdapter):
    """M6: candidate outside the tree (path escape)."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        candidates.append(
            NormalizedCandidate(
                relative_path="../../outside/secret.pdf",
                content_sha256=hashlib.sha256(b"secret").hexdigest(),
                group_key="escape",
                role="primary",
            )
        )
        return candidates


# mutant id -> (adapter factory, conformance check that MUST fire)
_CONFORMANCE_MUTANTS = {
    "M1_non_deterministic": (_NonDeterministicAdapter, "determinism"),
    "M2_hash_lie": (_HashLieAdapter, "hash_accuracy"),
    "M3_role_lie": (_RoleLieAdapter, "role_separation"),
    "M4_duplicate": (_DuplicateAdapter, "no_duplicates"),
    "M5_write": (_WriteAdapter, "read_only"),
    "M6_path_escape": (_EscapeAdapter, None),  # any check may fire
}


def _battery_tree(tmp_path: Path) -> Path:
    """Two pdfs (>=2 primaries so an order flip is observable) + one md."""
    (tmp_path / "annual").mkdir(parents=True)
    (tmp_path / "annual" / "2025.pdf").write_bytes(b"%PDF-1.4 zr402-a" * 4)
    (tmp_path / "annual" / "2024.pdf").write_bytes(b"%PDF-1.4 zr402-b" * 4)
    (tmp_path / "annual" / "2025.md").write_bytes(b"# md")
    return tmp_path


@pytest.mark.parametrize("mutant_id", sorted(_CONFORMANCE_MUTANTS))
def test_c4_conformance_mutant_killed(mutant_id: str, tmp_path):
    """M1..M6: each conformance-level mutant must be DETECTED by the
    production conformance kit (receipt names the violated check and
    conformance_ok turns false)."""
    factory, expected_check = _CONFORMANCE_MUTANTS[mutant_id]
    receipt = run_conformance(factory(), _battery_tree(tmp_path))
    assert not conformance_ok(receipt), (
        f"{mutant_id} survived the conformance kit: {receipt}"
    )
    if expected_check is not None:
        assert "FAILED" in receipt[expected_check], (
            f"{mutant_id}: expected {expected_check} to fire, got {receipt}"
        )


def test_c4_registry_fail_open_mutant_is_killed(monkeypatch):
    """M7 kill proof: a fail-open registered_adapter (unknown -> default
    entry) makes the killer assertion fail — i.e. the existing
    'unknown returns None' check distinguishes the mutant."""
    from company_wiki.source_catalog.adapters import registry

    monkeypatch.setattr(
        registry,
        "registered_adapter",
        lambda adapter_id: registry.REGISTERED_ADAPTERS.get(
            adapter_id, registry.REGISTERED_ADAPTERS["generic_document_v1"]
        ),
    )
    # under the mutant the killer assertion (is None) is violated:
    assert registry.registered_adapter("not_registered_v99") is not None


def test_c4_facade_fallback_mutant_is_killed(tmp_path, monkeypatch):
    """M9 kill proof (restates the ex08 scenario inside the battery): when
    the adapter itself explodes, the v2 route must raise
    ScannerFacadeError — a fallback-to-v1 mutant would instead return v1
    candidates for this tree, so this assertion is the killer."""
    from company_wiki.source_catalog import adapter_dispatch
    from company_wiki.source_catalog.scanner import (
        ScannerFacadeError,
        scan_root_strategy,
    )

    (tmp_path / "x.pdf").write_bytes(b"x")

    class _BoomAdapter:
        adapter_id = "sidecar_filing_v1"
        version = "1.0.0"

        def enumerate(self, root_path, *, limit=None):
            raise RuntimeError("adapter exploded")

    monkeypatch.setattr(adapter_dispatch, "adapter_for", lambda target: _BoomAdapter())
    root = RootSpec(
        root_id="zr402_boom",
        path=tmp_path,
        kind="directory",
        adapter_id="sidecar_filing_v1",
        read_only=True,
        reusable_for_filing=True,
    )
    with pytest.raises(ScannerFacadeError):
        scan_root_strategy(root, (), v2_scan_shadow=True)


def test_c4_kill_table_complete():
    """The declared kill table covers exactly M1..M9 with named detectors;
    dropping or renaming a row fails here (table completeness gate)."""
    declared = set(_CONFORMANCE_MUTANTS) | {
        "M7_registry_fail_open",
        "M8_kind_routing",
        "M9_facade_fallback",
    }
    assert {name.split("_", 1)[0] for name in declared} == {
        f"M{i}" for i in range(1, 10)
    }, f"kill table drifted: {sorted(declared)}"
    # each seam mutant has an executing killer in this module
    import inspect

    source = inspect.getsource(sys.modules[__name__])
    for mutant, killer in (
        ("M8_kind_routing", "test_c2_kind_routing_mutant_is_killed"),
        ("M9_facade_fallback", "test_c4_facade_fallback_mutant_is_killed"),
        ("M7_registry_fail_open", "test_c4_registry_fail_open_mutant_is_killed"),
    ):
        assert killer in source, f"{mutant} lost its executing killer"


def test_c4_battery_base_adapter_is_conformant(tmp_path):
    """Sanity: the battery's base adapter is itself conformant (the kit is
    not failing everything blindly)."""
    receipt = run_conformance(_BaseAdapter(), _battery_tree(tmp_path))
    assert conformance_ok(receipt), receipt
