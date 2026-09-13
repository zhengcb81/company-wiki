"""R4 phase-B step B07 acceptance: the wiki-side versioned read contract.

Design §B07 signs FOUR things on the wiki side (the consumer-side adapter
conversion and any consumer `companies` fallback belong to phase C):

  1. a versioned read contract - ``SOURCE_RESOLVER_SCHEMA_VERSION`` is the
     version every produced artifact carries, and the contract states the policy
     next to it;
  2. an unknown version is refused EXPLICITLY (fail closed), never parsed
     leniently - there is no N-1 rule on either side;
  3. no new directory-level fallback, and the absence is DECLARED in the
     contract: a request whose version has no qualified copy answers with an
     explicit failure instead of substituting another revision or reading
     outside the configured roots;
  4. ``B-payload-hash`` (the policy-export payload the resolve output carries)
     is unchanged - made executable by ``evidence/b07_payload_baseline.py`` in
     the phase-B run directory, which compares the payload byte for byte against
     the phase-A frozen revision and reports ``identical``.

Matrix items: L11 (phase-B acceptance map, reverse-coverage
L12 (query zero-write) has NO case here on purpose: its independent
observation belongs to B08 (B-VR07-06), and this file only signs the wiki-side
contract.  section; step B07 claims these, and the cases below are what exercises them).

Product code is NOT modified by this file (file-scope F10: new tests only).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    SOURCE_RESOLVER_SCHEMA_VERSION,
    ResolutionResult,
    ResolutionStatus,
    SourceRequest,
    SourceResolver,
    build_resolution_envelope,
)

SRC = Path(__file__).resolve().parents[2] / "src" / "company_wiki" / "source_catalog"
RESOLVER_SOURCE = SRC / "resolver.py"

BODY = b"%PDF-1.4 r4b07-version-contract"
DIGEST = hashlib.sha256(BODY).hexdigest()


def _sidecar(**overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "source_title": "Acme 2025 Annual Report",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": DIGEST,
        "retrieved_at": "2026-02-21T00:00:00Z",
        "collector_name": "sec_edgar",
        "collector_version": "1.0",
    }
    payload.update(overrides)
    return payload


def _write_copy(directory: Path, name: str = "2025.pdf") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    target.write_bytes(BODY)
    (directory / f"{name}.source.json").write_text(
        json.dumps(_sidecar(), ensure_ascii=False), encoding="utf-8"
    )
    return target


def _root(root_id: str, path: Path, kind: str, priority: int) -> RootSpec:
    return RootSpec(
        root_id,
        path,
        kind,
        priority=priority,
        adapter_id="company_raw_v1" if kind == "company_raw" else "sidecar_filing_v1",
        read_only=kind != "company_raw",
        reusable_for_filing=True,
        canonical_write_target="companies" if kind == "company_raw" else None,
    )


def _catalog(tmp_path: Path, roots: list[RootSpec]):
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


def _request(**overrides) -> SourceRequest:
    fields = dict(
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
    fields.update(overrides)
    return SourceRequest(**fields)


# ---------------------------------------------------------------------------
# 1. the versioned contract
# ---------------------------------------------------------------------------


def test_r4b07_produced_artifacts_carry_the_current_version(tmp_path):
    root = tmp_path / "companies"
    _write_copy(root / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = _catalog(tmp_path, [_root("company_raw", root, "company_raw", 10)])
    resolution = SourceResolver(catalog).resolve(_request())
    assert resolution.matches, resolution.debug_trace
    assert resolution.schema_version == SOURCE_RESOLVER_SCHEMA_VERSION
    assert SOURCE_RESOLVER_SCHEMA_VERSION == "1.0"
    for handle in resolution.matches:
        assert handle.schema_version == SOURCE_RESOLVER_SCHEMA_VERSION
    envelope = build_resolution_envelope(resolution, store=catalog.store)
    assert envelope.envelope_schema_version == "1.0"


# ---------------------------------------------------------------------------
# 2. an unknown version is refused explicitly
# ---------------------------------------------------------------------------


def _result_with_version(version: str) -> ResolutionResult:
    return ResolutionResult(
        schema_version=version,
        request_id="urn:test:version",
        status=ResolutionStatus.MISSING,
        reason="r",
        download_required=False,
        download_allowed=False,
        matches=(),
        debug_trace=(),
    )


def test_r4b07_an_unknown_version_is_refused_explicitly():
    """No lenient parse, no downgrade: the envelope builder refuses a result
    that does not carry the current version."""
    with pytest.raises(ValueError) as exc:
        build_resolution_envelope(_result_with_version("2.0"))
    assert "schema_version" in str(exc.value)
    # ... and the current version still passes
    envelope = build_resolution_envelope(_result_with_version("1.0"))
    assert envelope.envelope_schema_version == "1.0"


def test_r4b07_the_contract_declares_the_version_policy_and_no_fallback():
    """A guard, not a behaviour: the contract statement lives next to the
    version constant, so a later edit cannot silently drop it."""
    source = RESOLVER_SOURCE.read_text(encoding="utf-8")
    assert "accepts EXACTLY this version" in source
    assert "NO directory-level fallback" in source
    assert "not_found / not_indexed / unavailable / blocked / ambiguous" in source
    # the consumer-side pieces are explicitly NOT this repository's contract
    assert "belong to phase C" in source


# ---------------------------------------------------------------------------
# 3. no directory-level fallback
# ---------------------------------------------------------------------------


def test_r4b07_the_read_entry_point_refuses_a_foreign_version_handle(tmp_path):
    """B-VR07-02: the refusal had to reach the READ entry point too.

    `build_resolution_envelope` was the only place checking the version, so a
    handle stamped "2.0" could be handed to `read_verified_bytes` and came back
    `verified` with bytes - verifying against a version semantic this package
    does not implement.  Dataclass construction itself stays unchecked (no
    in-repo producer can stamp a foreign version); the read path no longer
    trusts it."""
    from dataclasses import replace

    companies = tmp_path / "companies"
    _write_copy(companies / "Acme" / "raw" / "financial_reports" / "annual")
    catalog = _catalog(tmp_path, [_root("company_raw", companies, "company_raw", 10)])
    resolution = SourceResolver(catalog).resolve(_request())
    assert resolution.matches, resolution.debug_trace
    handle = resolution.matches[0]

    out = SourceResolver(catalog).read_verified_bytes(
        replace(handle, schema_version="2.0")
    )
    assert out.data is None, out
    assert out.status == "unavailable", out
    assert out.reason == "unsupported_version", out
    assert out.detail == "2.0", out
    # the current version still reads
    ok = SourceResolver(catalog).read_verified_bytes(handle)
    assert ok.ok and ok.data, ok


def test_r4b07_no_substitute_revision_or_directory(tmp_path):
    """The requested version does not exist; the same entity HAS another revision
    under another root.  The answer must be an explicit failure - never the other
    revision, never a path outside the configured roots.

    Boundary, stated because the contract sentence has one exception
    (B-VR07-01): decision S-10 rule 2 lets ONE row be served on the catalog's
    declaration when no copy passes verification, marked with an
    `unverified_<status>_on_pre_b02_canonical` trace entry.  This case is about
    substitute REVISIONS, which are never served; callers that need verified
    bytes must use `read_verified_bytes`."""
    companies = tmp_path / "companies"
    dropbox = tmp_path / "Dropbox" / "Stock"
    _write_copy(companies / "Acme" / "raw" / "financial_reports" / "annual")
    # a DIFFERENT revision (different bytes -> different document) elsewhere
    other = dropbox / "Acme" / "annual"
    other.mkdir(parents=True, exist_ok=True)
    other_body = b"%PDF-1.4 r4b07-other-revision"
    (other / "2024.pdf").write_bytes(other_body)
    (other / "2024.pdf.source.json").write_text(
        json.dumps(
            _sidecar(
                fiscal_year=2024,
                content_sha256=hashlib.sha256(other_body).hexdigest(),
            ),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    catalog = _catalog(
        tmp_path,
        [_root("company_raw", companies, "company_raw", 10),
         _root("dropbox_stock", dropbox, "directory", 20)],
    )
    resolution = SourceResolver(catalog).resolve(_request(fiscal_year=2023))
    assert resolution.matches == (), resolution.debug_trace
    assert resolution.status is ResolutionStatus.MISSING, resolution.debug_trace
    assert resolution.download_required is True
    # The refusal must be EXPLAINED, and the explanation must name a version
    # reason (B-VR07-05: the previous assertion searched the trace for the word
    # "served", which no code path ever writes, so it could never fail).
    assert resolution.debug_trace, "an explicit refusal must be explained"
    assert any(
        "fiscal_year" in item or "no_canonical" in item or "rejected" in item
        for item in resolution.debug_trace
    ), resolution.debug_trace
