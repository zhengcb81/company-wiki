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

The last cases freeze BOTH exported policy hashes with their real roles - the
resolver-side `policy.export_policy` and, separately, the cross-repo artifact
filing-fetch actually pins (what `cli._policy_export_payload` returns, i.e.
`policy_2x.export_policy_2x`) - and assert that the consumer payload's reusable
set equals the resolver's, on configs where an explicit flag contradicts the
kind list.  B01's first version froze only the resolver-side hash and called it
cross-repo, which review B-VR01-01 falsified.

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
# BOTH exported policy hashes are frozen, with their real roles (B-VR01-01):
# SHIPPED_POLICY_SHA256 is `policy.export_policy` (the resolver-side export),
# while the CROSS-REPO artifact filing-fetch pins for FC-501 containment is what
# `cli._policy_export_payload` returns, i.e. `policy_2x.export_policy_2x`.
SHIPPED_POLICY_SHA256 = (
    "cf0ac2adf9714fe003eb1d1497d678877840e35a6a6c32bc65aa7e5d0c0e1626"
)
# The consumer payload's hash is NOT pinned: it embeds each root's absolute
# `path_ref`, so it is machine-dependent (this host: c773099b...; CI on Linux:
# ca3b7f5d...).  Its schema version and reusable-root set are pinned instead.
CONSUMER_PAYLOAD_SCHEMA_VERSION = "2.0"

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


def _write_copy(directory: Path, name: str = "2025.pdf") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(_sidecar(), ensure_ascii=False), encoding="utf-8"
    )
    return target


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


def _scan(tmp_path: Path, roots: list[RootSpec], kinds=("company_raw", "directory")):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=tuple(kinds),
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
    """Two exports, two roles - and only ONE of them is portable enough to pin.

    The artifact filing-fetch pins for FC-501 containment is what
    ``cli._policy_export_payload`` produces, i.e. ``policy_2x.export_policy_2x``
    (the ZR-405 payload); ``policy.export_policy`` is the resolver-side export.
    B01 originally froze the second and called it cross-repo, which was wrong
    (review B-VR01-01).

    Measured while fixing the review: the CONSUMER payload embeds each root's
    absolute ``path_ref``, so its hash is MACHINE-DEPENDENT - this host computes
    c773099b... while CI (Linux) computes ca3b7f5d... for the same config, and
    the first version of this case therefore failed in CI.  So the portable
    assertions are pinned here (the resolver-side hash, which is path-redacted,
    plus the consumer payload's STRUCTURE and its agreement with the resolver),
    and the consumer hash is deliberately NOT pinned: it can only be asserted
    per machine, which is exactly why pinning it in a repository test is wrong.
    """
    config = load_catalog_config(SHIPPED_CONFIG)
    sha, policy = export_policy(config)
    assert sha == SHIPPED_POLICY_SHA256, (
        "the resolver-side policy export changed - migrate or revert"
    )
    assert policy["reusable_root_kinds"] == [
        "company_raw",
        "dayu_portfolio",
        "directory",
    ]
    assert {
        item["root_id"] for item in policy["roots"] if item["reusable_for_filing"]
    } == {"company_raw", "dayu_portfolio", "dropbox_stock", "future_lake"}

    from company_wiki.source_catalog.cli import _policy_export_payload

    consumer = _policy_export_payload(config)
    assert consumer["schema_version"] == CONSUMER_PAYLOAD_SCHEMA_VERSION, consumer
    assert consumer["reusable_root_kinds"] == [
        "company_raw",
        "dayu_portfolio",
        "directory",
    ], consumer
    assert {
        item["root_id"] for item in consumer["roots"] if item["reusable_for_filing"]
    } == {
        spec.root_id
        for spec in config.roots
        if _effective_reusable(spec, config)
    }
    # ... and the hash is a function of the payload, not a constant of the repo
    assert consumer["policy_hash"] != SHIPPED_POLICY_SHA256, (
        "the two exports are distinct artifacts; if they ever coincide, the "
        "roles in this file and in the run directory need re-checking"
    )


def _observed_reusable(tmp_path: Path, *, kind: str, flag, kinds) -> bool:
    """Does the resolver OFFER this root's copy for reuse?

    Derived from the resolver's answer - served, or refused with
    ``no_reusable_root_location`` - rather than from the rule function under
    test, so the comparison below is not circular.

    The copy sits where that root kind derives its identity from: a
    ``company_raw`` document is keyed by its ``companies/<entity>/...`` path,
    while a ``directory`` root takes identity from the sidecar.  A copy in the
    wrong place is never a candidate at all, and the trace would then be empty
    for a reason that has nothing to do with reusability.
    """
    root = tmp_path / f"copy-{kind}"
    target = (
        root / "Acme" / "raw" / "financial_reports" / "annual"
        if kind == "company_raw"
        else root
    )
    _write_copy(target)
    catalog = _scan(
        tmp_path,
        [_root("probe", root, kind, flag=flag, priority=10)],
        kinds=kinds,
    )
    result = _resolve(catalog)
    if result.matches:
        return True
    return not any(
        "no_reusable_root_location" in item for item in result.debug_trace
    )


def test_r4b01_consumer_export_agrees_with_the_resolver_on_contradicting_flags(tmp_path):
    """Agreement property, on the configs where the two rules CAN disagree.

    The shipped config cannot show a divergence - every shipped root is
    reusable under both a kind-only rule and the effective rule - so the matrix
    below uses configs where an explicit flag contradicts the kind list.  It
    compares the CONSUMER payload (the ``policy_2x`` copy filing-fetch pins)
    with the resolver's observable behaviour; a one-line revert of that copy to
    the kind-only rule makes the two disagree (review B-VR01-01)."""
    from company_wiki.source_catalog.cli import _policy_export_payload

    cases = [
        (("company_raw", "directory"), "company_raw", False),
        (("company_raw", "directory"), "company_raw", True),
        (("company_raw", "directory"), "company_raw", None),
        (("directory",), "company_raw", True),  # explicit true, kind NOT listed
        (("company_raw",), "directory", False),  # explicit false, kind listed
        (("company_raw",), "directory", None),
    ]
    for index, (kinds, kind, flag) in enumerate(cases):
        case_dir = tmp_path / f"case-{index}"
        case_dir.mkdir()
        root = case_dir / "copy"
        if kind == "company_raw":
            _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual")
        else:
            _write_copy(root)
        catalog = _scan(
            case_dir,
            [_root("probe", root, kind, flag=flag, priority=10)],
            kinds=kinds,
        )
        consumer = {
            item["root_id"]: bool(item["reusable_for_filing"])
            for item in _policy_export_payload(catalog.config)["roots"]
        }["probe"]
        observed = _observed_reusable(case_dir, kind=kind, flag=flag, kinds=kinds)
        assert consumer == observed, (kinds, kind, flag, consumer, observed)


def test_r4b01_empty_reusable_set_serves_nothing(tmp_path):
    """B-VR01-05: the candidate filter has no empty-set escape.  An omitted or
    empty set has to mean "nothing qualifies" - if it meant "no filtering", a
    future direct caller would silently get the fail-open behaviour back."""
    from company_wiki.source_catalog.resolver import SourceResolver, _ReadBudget

    path = _write_copy(
        tmp_path / "companies" / "Acme" / "raw" / "financial_reports" / "annual"
    )
    source_id = "urn:company-wiki:source:sha256:" + DIGEST
    document = {
        "document_id": "urn:company-wiki:document:sha256:" + DIGEST,
        "source_id": source_id,
        "content_sha256": DIGEST,
        "locations": [
            {
                "location_id": "loc-1",
                "root_id": "company_raw",
                "source_id": source_id,
                "candidate_rank": 1,
                "role": "original_primary",
                "location_status": "active",
                "relative_path": "2025.pdf",
                "absolute_path": str(path),
                "is_canonical": True,
            }
        ],
    }
    refused = SourceResolver._select_candidate(
        document, budget=_ReadBudget(), reusable_root_ids=frozenset()
    )
    assert refused[0] is None, refused
    assert refused[1] == "placeholder_no_handle", refused
    served = SourceResolver._select_candidate(
        document, budget=_ReadBudget(), reusable_root_ids=frozenset({"company_raw"})
    )
    assert served[0] is not None and served[0]["root_id"] == "company_raw", served


def test_r4b01_quoted_boolean_is_refused_by_the_admission_point(tmp_path):
    """B-VR01-04: a quoted boolean is a silent trap - `bool("false")` is True
    (the declared false would be REUSED) and `"true" is not True` skips the
    CFG-05/CFG-07 checks.  The single admission point refuses it."""
    from company_wiki.source_catalog.config import CatalogConfigError, load_catalog_config

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    for field_name, literal in (("reusable_for_filing", '"false"'), ("read_only", '"true"')):
        path = config_dir / f"{field_name}.yaml"
        path.write_text(
            "\n".join(
                [
                    'schema_version: "1.0"',
                    'catalog_dir: "${PROJECT_ROOT}/.source_catalog"',
                    "reusable_root_kinds: [directory]",
                    "roots:",
                    "  - root_id: probe",
                    "    kind: directory",
                    '    path: "${PROJECT_ROOT}"',
                    f"    {field_name}: {literal}",
                ]
            ),
            encoding="utf-8",
        )
        try:
            load_catalog_config(path)
        except CatalogConfigError as exc:
            assert "CFG-08" in str(exc), exc
            assert field_name in str(exc), exc
        else:  # pragma: no cover - the admission point must refuse this
            raise AssertionError(f"a quoted {field_name} was accepted")

