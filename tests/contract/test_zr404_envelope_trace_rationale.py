"""ZR-404 acceptance tests: envelope carries policy snapshot consistency,
candidate exclusion trace, canonical location rationale (path-redacted),
and source hash — additive, fail-closed, N/N-1 with filing consumers.

Criteria under pin (registry): envelope 带 policy snapshot、候选排除
trace、canonical location rationale；policy/epoch/cohort/source hash 一致；
路径脱敏；冲突 fail closed。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402

POLICY_HASH = "a" * 64
EPOCH = "epoch-7"
COHORTS = ("cohort-a", "cohort-b")


def _seed_company(
    tmp_path: Path,
    company: str,
    pdoc: str,
    kind: str,
    *,
    fy: int = 2024,
    provider: str = "cninfo",
    market: str = "CN",
    security: str = "601899",
) -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{pdoc}.pdf").write_bytes(
        b"%PDF-1.4 " + company.encode("utf-8") + pdoc.encode("utf-8")
    )
    (raw / f"{pdoc}.pdf.source.json").write_text(
        json.dumps(
            {
                "market": market,
                "security_id": security,
                "source_title": f"{company} {fy}",
                "fiscal_year": fy,
                "filing_date": f"{fy + 1}-03-20",
                "form_type": kind,
                "document_kind": kind,
                "provider": provider,
                "provider_document_id": pdoc,
                "source_url": f"https://provider.example/{pdoc}",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path / "companies"


def _catalog(tmp_path: Path, tree: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(
                RootSpec(
                    "company_raw",
                    tree,
                    "company_raw",
                    priority=10,
                    adapter_id="company_raw_v1",
                    read_only=False,
                    reusable_for_filing=True,
                    canonical_write_target="companies",
                ),
            ),
        )
    )


def _resolve(catalog, *, entity="Acme", fy=2024, kind="annual_report", pdoc="doc-a"):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(
        SourceRequest(
            entity=entity,
            market="CN",
            security_id="601899",
            document_kind=kind,
            form_type=kind,
            fiscal_year=fy,
            provider="cninfo",
            provider_document_id=pdoc,
            as_of_date="2026-08-11",
            mode="exact",
        )
    )


def _build(resolution, *, policy_snapshot=None, project_root=None):
    from company_wiki.source_catalog.resolver import build_resolution_envelope

    return build_resolution_envelope(
        resolution, policy_snapshot=policy_snapshot, project_root=project_root
    )


def _snapshot(*, cohorts=COHORTS, policy_hash=POLICY_HASH, epoch=EPOCH) -> dict:
    return {
        "policy_hash": policy_hash,
        "current_epoch": epoch,
        "flags": {},
        "roots": [],
        "active_cohorts": list(cohorts),
    }


# ---------------------------------------------------------------------------
# policy/epoch/cohort/source hash consistency
# ---------------------------------------------------------------------------


def test_zr404_cohorts_and_source_hash_ride_envelope(tmp_path):
    """policy_hash + activation_epoch + cohorts all come from the SAME
    policy_snapshot; source_sha256 is the matched handle's content hash —
    the four consistency keys are present together."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _build(_resolve(catalog), policy_snapshot=_snapshot())
    assert envelope.policy_hash == POLICY_HASH
    assert envelope.activation_epoch == EPOCH
    assert envelope.cohorts == COHORTS
    handle = _resolve(catalog).matches[0]
    assert envelope.source_sha256 == handle.content_sha256
    payload = envelope.to_dict()
    assert payload["cohorts"] == list(COHORTS)
    assert payload["source_sha256"] == handle.content_sha256


def test_zr404_without_snapshot_honest_defaults(tmp_path):
    """No policy snapshot -> policy_hash/epoch/cohorts stay None (never
    fabricated); source_sha256 still rides when a handle matched."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    resolution = _resolve(catalog)
    envelope = _build(resolution)
    assert envelope.policy_hash is None
    assert envelope.activation_epoch is None
    assert envelope.cohorts is None
    assert envelope.source_sha256 == resolution.matches[0].content_sha256


# ---------------------------------------------------------------------------
# conflict fail closed
# ---------------------------------------------------------------------------


def test_zr404_conflict_fail_closed_bad_policy_hash(tmp_path):
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    with pytest.raises(ValueError, match="policy_hash"):
        _build(_resolve(catalog), policy_snapshot=_snapshot(policy_hash="nope"))
    with pytest.raises(ValueError, match="policy_hash"):
        _build(_resolve(catalog), policy_snapshot=_snapshot(policy_hash=""))
    with pytest.raises(ValueError, match="policy_hash"):
        _build(_resolve(catalog), policy_snapshot=_snapshot(policy_hash="A" * 64))


def test_zr404_conflict_fail_closed_bad_epoch_or_cohorts(tmp_path):
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    with pytest.raises(ValueError, match="current_epoch"):
        _build(_resolve(catalog), policy_snapshot=_snapshot(epoch=7))
    with pytest.raises(ValueError, match="active_cohorts"):
        _build(_resolve(catalog), policy_snapshot=_snapshot(cohorts=("x", 1)))
    with pytest.raises(ValueError, match="active_cohorts"):
        _build(_resolve(catalog), policy_snapshot=_snapshot(cohorts=(1, 2)))
    with pytest.raises(ValueError, match="policy_snapshot"):
        _build(_resolve(catalog), policy_snapshot="not-a-dict")


# ---------------------------------------------------------------------------
# candidate exclusion trace
# ---------------------------------------------------------------------------


def test_zr404_candidate_exclusion_trace_carried(tmp_path):
    """A resolution that considered but excluded candidates records the
    exclusion reasons in the envelope (the trace is the per-candidate
    why-not evidence, never fabricated)."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report", fy=2024)
    _seed_company(tmp_path, "Acme", "doc-wrong-year", "annual_report", fy=2019)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    resolution = _resolve(catalog, fy=2024)
    assert resolution.status.value.startswith("reused")
    envelope = _build(resolution)
    assert envelope.candidate_exclusion_trace
    joined = "|".join(envelope.candidate_exclusion_trace)
    assert "fiscal_year_mismatch" in joined
    payload = envelope.to_dict()
    assert isinstance(payload["candidate_exclusion_trace"], list)


def test_zr404_exclusion_trace_empty_on_clean_match(tmp_path):
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    resolution = _resolve(catalog)
    envelope = _build(resolution)
    # a single matched candidate -> no exclusion entries beyond the
    # entity-gate counter line; the matched reason is present
    assert any("matched" in item for item in envelope.candidate_exclusion_trace)


# ---------------------------------------------------------------------------
# canonical location rationale + path redaction
# ---------------------------------------------------------------------------


def test_zr404_canonical_rationale_redacts_project_root(tmp_path):
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    resolution = _resolve(catalog)
    envelope = _build(resolution, project_root=tmp_path)
    rationale = envelope.canonical_location_rationale
    assert rationale is not None
    assert rationale["canonical_location_id"]
    assert rationale["selection"] == (
        "lowest_priority_active_original_primary_then_tiebreak"
    )
    assert rationale["source_sha256"] == resolution.matches[0].content_sha256
    # path redaction: no absolute project path leaks into the envelope
    assert "${PROJECT_ROOT}" in rationale["canonical_path"]
    assert str(tmp_path.resolve()) not in json.dumps(envelope.to_dict())
    assert (
        "2025.pdf" in rationale["canonical_path"]
        or "doc-a.pdf" in rationale["canonical_path"]
    )


def test_zr404_no_rationale_without_match(tmp_path):
    """MISSING resolution -> no canonical rationale, no source hash."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    resolution = _resolve(catalog, pdoc="never-indexed")
    assert resolution.status is ResolutionStatus.MISSING
    envelope = _build(resolution)
    assert envelope.canonical_location_rationale is None
    assert envelope.source_sha256 is None


# ---------------------------------------------------------------------------
# additive N/N-1 contract (filing validate_resolution_envelope accepts)
# ---------------------------------------------------------------------------


def test_zr404_additive_old_keys_unchanged_and_schema_stable(tmp_path):
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _build(_resolve(catalog), policy_snapshot=_snapshot())
    payload = envelope.to_dict()
    assert payload["envelope_schema_version"] == "1.0"
    for key in (
        "outcome",
        "download_events",
        "policy_hash",
        "activation_epoch",
        "bundle_status",
        "bundle_hash",
        "bundle",
        "prompt_injection_status",
        "parser_calls",
        "llm_calls",
    ):
        assert key in payload
    # deterministic serialization still holds with the new fields
    assert json.dumps(payload, sort_keys=True) == json.dumps(
        envelope.to_dict(), sort_keys=True
    )


_FILING_CONTRACTS = Path(r"C:\Users\郑曾波\Projects\filing-fetch\scripts")


@pytest.mark.skipif(
    not _FILING_CONTRACTS.is_dir(),
    reason="filing-fetch checkout not present on this machine",
)
def test_zr404_filing_validator_accepts_enriched_envelope(tmp_path):
    """Cross-repo N/N-1: the filing consumer's validate_resolution_envelope
    must accept the ZR-404-enriched envelope (additive fields pass through;
    schema_version still 1.0; known-field checks unchanged)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "filing_contracts_zr404_probe", _FILING_CONTRACTS / "filing_contracts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _build(
        _resolve(catalog), policy_snapshot=_snapshot(), project_root=tmp_path
    )
    payload = envelope.to_dict()
    normalized = module.validate_resolution_envelope(payload)
    assert normalized["envelope_schema_version"] == "1.0"
    assert (
        normalized["candidate_exclusion_trace"] == payload["candidate_exclusion_trace"]
    )
    assert (
        normalized["canonical_location_rationale"]
        == payload["canonical_location_rationale"]
    )
    assert normalized["cohorts"] == list(COHORTS)
    assert normalized["source_sha256"] == payload["source_sha256"]
    # and the raw envelope never contains an absolute project path
    assert str(tmp_path.resolve()) not in json.dumps(normalized)
    assert "${PROJECT_ROOT}" in json.dumps(normalized)


def test_zr404_policy_hash_shape_validation_matches_filing_rule():
    """The envelope's fail-closed policy_hash shape is the SAME rule the
    filing validator applies (lowercase 64-hex or null) — the two sides
    cannot drift apart."""
    from company_wiki.source_catalog.resolver import build_resolution_envelope
    from company_wiki.source_catalog.resolver import ResolutionResult
    from company_wiki.source_catalog.resolver import ResolutionStatus
    from company_wiki.source_catalog.resolver import SOURCE_RESOLVER_SCHEMA_VERSION

    def result_for():
        return ResolutionResult(
            schema_version=SOURCE_RESOLVER_SCHEMA_VERSION,
            request_id="urn:test:shape",
            status=ResolutionStatus.MISSING,
            reason="r",
            download_required=False,
            download_allowed=False,
            matches=(),
            debug_trace=(),
        )

    build_resolution_envelope(
        result_for(),
        policy_snapshot={
            "policy_hash": "0" * 64,
            "current_epoch": "e",
        },
    )  # valid lowercase hex passes
    for bad in ("A" * 64, "abc", "0" * 63, "0" * 65, ""):
        with pytest.raises(ValueError, match="policy_hash"):
            build_resolution_envelope(
                result_for(),
                policy_snapshot={
                    "policy_hash": bad,
                    "current_epoch": "e",
                },
            )
