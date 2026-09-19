"""F-BAR-11 regression: a `reusable_for_filing: false` root binds the BYTE entry point too.

Measured defect (independent reviews `B.VR-r3` F-R3-01 and `B.VR-r4`, 2026-09-18): the deny a
root carries was honoured by the resolver's DECISION (`resolve` -> `missing` /
`no_reusable_root_location`) but NOT by the byte primitive.  A caller that built its own
handle - the review did exactly that - was still served 59 bytes with `status="verified"`
from a root whose policy says "do not reuse me for filings", because
`SourceResolver.read_verified_bytes` gated on root CONTAINMENT only.

The fix reuses `policy._effective_reusable` (the same function the decision path and the
cross-repo policy export use) and the already-registered reason code `policy_denied`
("root policy does not authorize reuse", observability.py:51), so the three layers cannot
disagree and no new taxonomy entry is invented.

Cases:
  * the denied root's bytes are REFUSED (not_found / policy_denied, zero bytes);
  * the same handle pointed at the REUSABLE root still verifies (no over-restriction);
  * a path outside every root keeps its own pre-existing reason
    (`artifact_path_outside_allowed_root`) - the new gate must not shadow it;
  * the deny is read from the CONFIG, so flipping `reusable_for_filing` to True on the same
    tree turns the refusal back into `verified` (the gate keys on policy, not on the path).
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import CatalogConfig, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.resolver import (  # noqa: E402
    B03_BYTES_SOURCE_HANDLE,
    SourceRequest,
    SourceResolver,
)

BODY = b"%PDF-1.4 r4bar11-policy-denied-bytes"
DIGEST = hashlib.sha256(BODY).hexdigest()


def _sidecar(entity: str, provider_document_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": f"ent-{entity.lower()}",
        "display_name": entity,
        "market": "US",
        "security_id": entity.upper(),
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "published_at": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": provider_document_id,
        "source_url": f"https://sec.gov/{provider_document_id}",
        "content_sha256": DIGEST,
    }


def _write_filing(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "2025.pdf"
    target.write_bytes(BODY)
    (directory / "2025.pdf.source.json").write_text(
        json.dumps(_sidecar("Acme", "doc-1"), ensure_ascii=False), encoding="utf-8")
    return target


def _catalog(tmp_path: Path, *, denied: bool) -> SourceCatalog:
    """Two roots holding the SAME filing: one reusable, one explicitly denied."""
    reusable_dir = tmp_path / "roots" / "reusable"
    denied_dir = tmp_path / "roots" / "denied"
    _write_filing(reusable_dir)
    _write_filing(denied_dir)
    roots = (
        RootSpec("reusable_root", reusable_dir, "directory", priority=10,
                 adapter_id="sidecar_filing_v1", read_only=True, reusable_for_filing=True),
        RootSpec("denied_root", denied_dir, "directory", priority=20,
                 adapter_id="sidecar_filing_v1", read_only=True,
                 reusable_for_filing=not denied),
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=roots,
        )
    )
    catalog.scan()
    return catalog


def _handle(catalog: SourceCatalog, root_id: str):
    """Resolve the filing (it comes from the reusable root) and point it at `root_id`.

    No `form_type` in the request.  The historical reason was that the adapter did not map
    that key (the request came back `form_type_mismatch`); F-BAR-14 fixed that, so the reason
    now is simply that this test is about the byte entry point, not about form matching - and
    the request stays as it was so the case remains comparable with the recorded evidence.
    """
    resolver = SourceResolver(catalog)
    resolution = resolver.resolve(SourceRequest(
        entity="Acme", market="US", security_id="ACME", document_kind="annual_report",
        fiscal_year=2025, as_of_date="2026-07-18", mode="exact",
    ))
    handle = resolution.matches[0]
    location = next(
        row for row in catalog.reader.fetchall(
            "SELECT location_id,absolute_path FROM locations WHERE root_id=?", (root_id,))
    )
    return resolver, replace(
        handle,
        canonical_location_id=location["location_id"],
        canonical_path=location["absolute_path"],
    )


def test_denied_root_bytes_are_refused(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path, denied=True)
    resolver, denied_handle = _handle(catalog, "denied_root")
    result = resolver.read_verified_bytes(denied_handle)
    assert result.ok is False
    assert result.data is None
    assert result.byte_size == 0
    assert result.status == "not_found"
    assert result.reason == "policy_denied"
    assert result.detail == "denied_root"
    assert result.bytes_source != B03_BYTES_SOURCE_HANDLE


def test_reusable_root_still_verifies(tmp_path: Path) -> None:
    """No over-restriction: the same request keeps working where reuse is authorized."""
    catalog = _catalog(tmp_path, denied=True)
    resolver, reusable_handle = _handle(catalog, "reusable_root")
    result = resolver.read_verified_bytes(reusable_handle)
    assert result.ok is True
    assert result.status == "verified"
    assert result.data == BODY
    assert result.content_sha256 == DIGEST


def test_policy_flip_turns_the_refusal_back_into_bytes(tmp_path: Path) -> None:
    """The gate keys on POLICY, not on a path: the same tree, `reusable_for_filing: true`."""
    catalog = _catalog(tmp_path, denied=False)
    resolver, handle = _handle(catalog, "denied_root")
    result = resolver.read_verified_bytes(handle)
    assert result.ok is True, (result.status, result.reason)
    assert result.data == BODY


def test_path_outside_every_root_keeps_its_own_reason(tmp_path: Path) -> None:
    """The new gate must not shadow the containment refusal that preceded it."""
    catalog = _catalog(tmp_path, denied=True)
    resolver, handle = _handle(catalog, "reusable_root")
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(BODY)
    result = resolver.read_verified_bytes(replace(handle, canonical_path=str(outside)))
    assert result.ok is False
    assert result.reason == "artifact_path_outside_allowed_root"
