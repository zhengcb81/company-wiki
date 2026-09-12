"""R4 phase-B step B01 acceptance: one owner per field, and one reuse rule.

Design §B01 asks for two things this file pins:

* **one owner per semantic area** — physical location belongs to the storage
  layer (`config.py` → `models.RootSpec`), business identity to the catalog
  layer, reuse qualification to the policy layer, egress to the action
  boundary (out of this phase's scope);
* **one admission/reuse rule** — an explicit ``reusable_for_filing: false``
  must actually take effect (owner R-2 / design P-7), and the resolver must
  not maintain a second, kind-only copy of that rule: it calls the same
  ``policy._effective_reusable`` the cross-repo policy export uses, so the
  resolver and the exported containment policy cannot disagree.

The last case freezes the shipped policy hash: B01 may not change the export
(its bytes are filing-fetch's FC-501 containment source), so a change here is
supposed to fail loudly and demand a synchronized cross-repo migration.

Product code is NOT modified by this file (file-scope F10: new tests only).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.policy import (  # noqa: E402
    _effective_reusable,
    export_policy,
    policy_authorizes_root,
)
from company_wiki.source_catalog.resolver import (  # noqa: E402
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIPPED_CONFIG = REPO_ROOT / "config" / "source_catalog.yaml"
# The export is a CROSS-REPO artifact (filing-fetch pins this value); B01 is not
# allowed to move it silently.
SHIPPED_POLICY_SHA256 = (
    "cf0ac2adf9714fe003eb1d1497d678877840e35a6a6c32bc65aa7e5d0c0e1626"
)

BODY = b"%PDF-1.4 r4b01-field-owner"
DIGEST = hashlib.sha256(BODY).hexdigest()


def _sidecar() -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": DIGEST,
    }


def _write_copy(directory: Path, name: str = "2025.pdf") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(_sidecar(), ensure_ascii=False), encoding="utf-8"
    )


def _root(root_id: str, path: Path, kind: str, *, flag, priority: int) -> RootSpec:
    return RootSpec(
        root_id,
        path,
        kind,
        priority=priority,
        adapter_id="sidecar_filing_v1" if kind == "directory" else "company_raw_v1",
        read_only=kind != "company_raw",
        reusable_for_filing=flag,
        canonical_write_target="companies" if kind == "company_raw" else None,
    )


def _scan(tmp_path: Path, roots: list[RootSpec]):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=tuple(roots),
        )
    )
    catalog.scan()
    return catalog


def _request() -> SourceRequest:
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        form_type="10-K",
        fiscal_year=2025,
        provider="sec",
        provider_document_id="doc-1",
        as_of_date="2026-08-10",
        mode="exact",
    )


def _resolve(catalog):
    return SourceResolver(catalog).resolve(_request())


# ---------------------------------------------------------------------------
# The explicit flag wins, and it wins the SAME way the export says
# ---------------------------------------------------------------------------


def test_r4b01_explicit_false_is_not_reusable(tmp_path):
    """`reusable_for_filing: false` on a kind that is otherwise reusable: the
    copy must NOT be offered for reuse, so the request is answered MISSING."""
    root = tmp_path / "companies"
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = _scan(
        tmp_path, [_root("company_raw", root, "company_raw", flag=False, priority=10)]
    )
    result = _resolve(catalog)
    assert result.matches == (), result.debug_trace
    assert result.status is ResolutionStatus.MISSING, result.debug_trace
    assert any("no_reusable_root_location" in item for item in result.debug_trace), (
        result.debug_trace
    )


def test_r4b01_unset_flag_still_follows_the_kind(tmp_path):
    """`None` is not `False`: an unset flag keeps following the kind allowance."""
    root = tmp_path / "companies"
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = _scan(
        tmp_path, [_root("company_raw", root, "company_raw", flag=None, priority=10)]
    )
    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace


def test_r4b01_explicit_true_wins_over_the_kind_list(tmp_path):
    """An explicit `true` on a kind the config does NOT list as reusable is
    reusable — the same answer the exported policy gives, because both sides
    call one function."""
    root = tmp_path / "Dropbox" / "Stock"
    _write_copy(root)
    catalog = _scan(
        tmp_path,
        [
            RootSpec(
                "dropbox_stock",
                root,
                "directory",
                priority=10,
                adapter_id="sidecar_filing_v1",
                read_only=True,
                reusable_for_filing=True,
            )
        ],
    )
    # the config deliberately does not list `directory` as reusable
    catalog.config = type(catalog.config)(
        project_root=catalog.config.project_root,
        catalog_dir=catalog.config.catalog_dir,
        reusable_root_kinds=("company_raw",),
        roots=tuple(catalog.config.roots),
    )
    result = _resolve(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    sha, policy = export_policy(catalog.config)
    assert policy_authorizes_root(policy, "dropbox_stock") is True, policy
    assert sha  # the export and the resolver agree on this root


def test_r4b01_resolver_set_matches_the_exported_policy(tmp_path):
    """Agreement property: the set of roots the resolver treats as reusable is
    exactly the set the exported policy marks reusable."""
    root = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    future = tmp_path / "future_lake"
    for directory in (
        root / "Acme" / "raw" / "financial_reports" / "annual",
        dropbox,
        future,
    ):
        _write_copy(directory)
    catalog = _scan(
        tmp_path,
        [
            _root("company_raw", root, "company_raw", flag=False, priority=10),
            _root("dropbox_stock", dropbox, "directory", flag=None, priority=20),
            _root("future_lake", future, "directory", flag=True, priority=30),
        ],
    )
    _, policy = export_policy(catalog.config)
    exported = {
        item["root_id"]
        for item in policy["roots"]
        if item["reusable_for_filing"]
    }
    computed = {
        spec.root_id
        for spec in catalog.config.roots
        if _effective_reusable(spec, catalog.config)
    }
    assert computed == exported == {"dropbox_stock", "future_lake"}
    # and the resolver refuses the excluded copy even though it is a healthy one
    result = _resolve(catalog)
    assert result.matches[0].canonical_path != str(
        root / "Acme" / "raw" / "financial_reports" / "annual" / "2025.pdf"
    )


# ---------------------------------------------------------------------------
# Ownership boundaries that this step must not break
# ---------------------------------------------------------------------------


def test_r4b01_unknown_root_field_is_rejected_by_the_single_admission_point(tmp_path):
    """Physical-location fields have ONE owner (`config.py`): a root field the
    admission point does not know is refused there, not silently accepted."""
    from company_wiki.source_catalog.config import CatalogConfigError, load_catalog_config

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "bad.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                'catalog_dir: "${PROJECT_ROOT}/.source_catalog"',
                "reusable_root_kinds: [company_raw]",
                "roots:",
                "  - root_id: company_raw",
                "    kind: company_raw",
                '    path: "${PROJECT_ROOT}/companies"',
                "    adapter_id: company_raw_v1",
                "    canonical_write_target: companies",  # not an admitted field
                "    priority: 10",
            ]
        ),
        encoding="utf-8",
    )
    try:
        load_catalog_config(config_dir / "bad.yaml")
    except CatalogConfigError as exc:
        assert "unknown fields" in str(exc), exc
        assert "canonical_write_target" in str(exc), exc
    else:  # pragma: no cover - the admission point must refuse this
        raise AssertionError("an unknown root field was accepted")


def test_r4b01_shipped_policy_hash_is_frozen(tmp_path):
    """B01 must not move the cross-repo policy hash: filing-fetch pins it as its
    FC-501 containment source, so a change here requires a synchronized
    migration and has to fail loudly instead."""
    catalog = _scan(
        tmp_path,
        [_root("company_raw", tmp_path / "companies", "company_raw", flag=True, priority=10)],
    )
    assert catalog is not None  # the fixture itself is not the point here
    config = load_catalog_config(SHIPPED_CONFIG)
    sha, policy = export_policy(config)
    assert sha == SHIPPED_POLICY_SHA256, (
        "the shipped policy export changed - filing-fetch's FC-501 containment "
        "expects this hash; migrate it in the same change or revert"
    )
    assert policy["reusable_root_kinds"] == [
        "company_raw",
        "dayu_portfolio",
        "directory",
    ]
    assert {
        item["root_id"] for item in policy["roots"] if item["reusable_for_filing"]
    } == {"company_raw", "dayu_portfolio", "dropbox_stock", "future_lake"}
