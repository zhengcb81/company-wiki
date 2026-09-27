"""Contract tests for a pathless, exact-version SourceExport v2.

The exporter receives catalog-issued SourceRef values and existing evidence
spans. It must obtain source metadata and verify bytes through SourceVersionReader;
callers cannot supply a trusted manifest or a physical source path.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tracemalloc

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.source_catalog import (  # noqa: E402
    CatalogConfig,
    RootSpec,
    SourceCatalog,
    SourceReadError,
    SourceVersionReader,
)
from company_wiki.source_contract import (  # noqa: E402
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    SourceExportError,
    source_id_for_sha256,
)


BODY = b"%PDF-1.4\npathless export fixture\n"
TXT_PREFIX = "正文🙂 "
TXT_QUOTE = "Revenue increased."
TXT_TEXT = TXT_PREFIX + TXT_QUOTE + " End"
TXT_BODY = TXT_TEXT.encode("utf-8")
TITLE = "Acme 2025 annual report"
RETRIEVED_AT = "2026-02-21T00:00:00Z"
SOURCE_URL = "https://sec.gov/x/2025"


def _sha256_json(value: object) -> str:
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _v2_module():
    return importlib.import_module("company_wiki.source_contract.source_export_v2")


def _fixture(
    tmp_path: Path, *, text_mode: bool = False, body_override: bytes | None = None
):
    body = (
        body_override if body_override is not None
        else TXT_BODY if text_mode else BODY
    )
    digest = hashlib.sha256(body).hexdigest()
    file_name = "filing.txt" if text_mode else "filing.pdf"
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    raw_path = raw_root / file_name
    raw_path.write_bytes(body)
    sidecar = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "source_title": TITLE,
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-1",
        "source_url": SOURCE_URL,
        "content_sha256": digest,
        "retrieved_at": RETRIEVED_AT,
        "collector_name": "sec_edgar",
        "collector_version": "1.0",
    }
    (raw_root / f"{file_name}.source.json").write_text(
        json.dumps(sidecar), encoding="utf-8"
    )
    root = RootSpec(
        "future_lake", raw_root, "directory", priority=10,
        adapter_id="sidecar_filing_v1", read_only=True,
        reusable_for_filing=True,
    )
    config = CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(root,),
        reusable_root_kinds=("directory",),
    )
    catalog = SourceCatalog(config)
    catalog.scan()
    row = catalog.reader.fetchone(
        """SELECT d.document_id, d.primary_source_id AS source_id,
                  s.content_sha256
           FROM documents d JOIN sources s
             ON s.source_id=d.primary_source_id
           WHERE d.source_status='active' AND s.content_sha256=?""",
        (digest,),
    )
    assert row is not None
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(row["document_id"], row["source_id"], digest)
    span = EvidenceSpan.create(
        source_id=ref.source_id,
        coordinates=(
            EvidenceCoordinates(
                char_start=len(TXT_PREFIX),
                char_end=len(TXT_PREFIX) + len(TXT_QUOTE),
            )
            if text_mode else EvidenceCoordinates(page_number=1)
        ),
        raw_text=TXT_QUOTE,
        structured_value=None,
        parser_name="fixture-parser",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )
    return catalog, root, raw_path, ref, span


def _build(reader: SourceVersionReader, ref, span):
    return _v2_module().SourceExportBundleV2.build(
        source_reader=reader,
        refs=(ref,),
        evidence_spans=(span,),
    )


def test_v2_rejects_caller_supplied_pdf_span_without_parser_registry(tmp_path):
    catalog, _, _, ref, forged = _fixture(tmp_path)
    with pytest.raises(SourceExportError, match="unverified evidence span"):
        _build(SourceVersionReader(catalog), ref, forged)

    manifest_only = _v2_module().SourceExportBundleV2.build(
        source_reader=SourceVersionReader(catalog),
        refs=(ref,),
        evidence_spans=(),
    ).to_dict()
    assert manifest_only["counts"] == {"source_manifests": 1, "evidence_spans": 0}
    assert manifest_only["manifests"][0]["mime_type"] == "application/pdf"


def test_manifest_only_pdf_export_has_bounded_peak_memory(tmp_path):
    body = b"%PDF-1.4\n" + b"x" * (16 * 1024 * 1024)
    catalog, _, _, ref, _ = _fixture(tmp_path, body_override=body)
    reader = SourceVersionReader(catalog)
    tracemalloc.start()
    try:
        wire = _v2_module().SourceExportBundleV2.build(
            source_reader=reader,
            refs=(ref,),
            evidence_spans=(),
        ).to_dict()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert wire["counts"] == {"source_manifests": 1, "evidence_spans": 0}
    assert peak < 8 * 1024 * 1024


def test_v2_grounds_utf8_text_span_at_unicode_character_offsets(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    wire = _build(SourceVersionReader(catalog), ref, span).to_dict()
    assert wire["manifests"][0]["mime_type"] == "text/plain"
    assert wire["evidence_spans"] == [span.to_dict()]
    assert span.coordinates.char_start != len(TXT_PREFIX.encode("utf-8"))


def test_v2_rejects_text_span_when_original_is_not_utf8(tmp_path):
    catalog, _, _, ref, span = _fixture(
        tmp_path, text_mode=True, body_override=b"\xff" + TXT_BODY
    )
    with pytest.raises(SourceExportError, match="unverified evidence span"):
        _build(SourceVersionReader(catalog), ref, span)


def test_v2_loader_rejects_pdf_span_even_with_recomputed_bundle_hash(tmp_path):
    catalog, _, _, ref, forged = _fixture(tmp_path)
    wire = _v2_module().SourceExportBundleV2.build(
        source_reader=SourceVersionReader(catalog),
        refs=(ref,),
        evidence_spans=(),
    ).to_dict()
    wire["evidence_spans"] = [forged.to_dict()]
    wire["counts"]["evidence_spans"] = 1
    _rehash_wire(wire)
    with pytest.raises(SourceExportError, match="unverified evidence span"):
        _v2_module().SourceExportBundleV2.from_dict(wire)


@pytest.mark.parametrize(
    "tamper",
    (
        "mismatched_text", "byte_offsets", "structured_value",
        "missing_offsets", "unverified_page",
    ),
)
def test_v2_rejects_text_span_without_exact_grounding(tmp_path, tamper):
    catalog, _, _, ref, original = _fixture(tmp_path, text_mode=True)
    coordinates = original.coordinates
    raw_text = original.raw_text
    structured_value = None
    if tamper == "mismatched_text":
        raw_text = "Revenue declined."
    elif tamper == "byte_offsets":
        coordinates = EvidenceCoordinates(
            char_start=len(TXT_PREFIX.encode("utf-8")),
            char_end=len(TXT_PREFIX.encode("utf-8")) + len(TXT_QUOTE),
        )
    elif tamper == "structured_value":
        structured_value = {"growth": 0.1}
    elif tamper == "missing_offsets":
        coordinates = EvidenceCoordinates(page_number=1)
    elif tamper == "unverified_page":
        coordinates = replace(coordinates, page_number=1)
    span = EvidenceSpan.create(
        source_id=ref.source_id,
        coordinates=coordinates,
        raw_text=raw_text,
        structured_value=structured_value,
        parser_name="fixture-parser",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )
    with pytest.raises(SourceExportError, match="unverified evidence span"):
        _build(SourceVersionReader(catalog), ref, span)


def test_v2_bundle_reads_any_configured_root_label(tmp_path):
    catalog, root, _, ref, span = _fixture(tmp_path, text_mode=True)
    labeled_catalog = SourceCatalog(replace(
        catalog.config,
        roots=(replace(root, privacy_class="private_user"),),
    ))
    wire = _build(SourceVersionReader(labeled_catalog), ref, span).to_dict()
    assert wire["manifests"][0]["source_id"] == ref.source_id
    assert wire["evidence_spans"] == [span.to_dict()]


def test_v2_bundle_blocks_conflicting_sidecars_regardless_of_root_labels(tmp_path):
    catalog, public_root, raw_path, ref, span = _fixture(tmp_path, text_mode=True)
    private_path = tmp_path / "other" / raw_path.name
    private_path.parent.mkdir()
    private_path.write_bytes(raw_path.read_bytes())
    private_sidecar = json.loads(
        (raw_path.parent / f"{raw_path.name}.source.json").read_text(encoding="utf-8")
    )
    private_sidecar["source_title"] = "Conflicting title about Acme"
    private_sidecar["source_url"] = "https://other.example/filing"
    (private_path.parent / f"{raw_path.name}.source.json").write_text(
        json.dumps(private_sidecar), encoding="utf-8"
    )
    other_root = RootSpec(
        "other_root", private_path.parent, "directory", priority=20,
        adapter_id="sidecar_filing_v1", read_only=True,
        reusable_for_filing=False, privacy_class="private_user",
    )
    mixed_catalog = SourceCatalog(replace(
        catalog.config, roots=(public_root, other_root),
    ))
    mixed_catalog.scan()
    with pytest.raises(SourceReadError) as error:
        _build(SourceVersionReader(mixed_catalog), ref, span)
    assert error.value.status == "blocked"
    assert error.value.reason == "metadata_conflict"


def test_v2_bundle_is_available_from_public_source_contract():
    import company_wiki.source_contract as public_api

    assert public_api.SourceExportBundleV2 is _v2_module().SourceExportBundleV2


def _rehash_wire(wire: dict) -> None:
    payload = {
        key: value for key, value in wire.items()
        if key not in {"bundle_sha256", "export_id"}
    }
    digest = _sha256_json(payload)
    wire["bundle_sha256"] = digest
    wire["export_id"] = "urn:company-wiki:source-export:sha256:" + digest


def test_v2_bundle_has_verified_identity_title_provenance_and_span_without_paths(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    bundle = _build(SourceVersionReader(catalog), ref, span)
    wire = bundle.to_dict()

    assert wire["schema_version"] == "2.0.0"
    assert wire["source_manifest_schema_version"] == "2.0.0"
    assert wire["evidence_span_schema_version"] == "1.0.0"
    assert wire["counts"] == {"source_manifests": 1, "evidence_spans": 1}
    manifest = wire["manifests"][0]
    assert manifest["document_id"] == ref.document_id
    assert manifest["source_id"] == ref.source_id
    assert manifest["content_sha256"] == hashlib.sha256(TXT_BODY).hexdigest()
    assert manifest["byte_size"] == len(TXT_BODY)
    assert manifest["title"] == TITLE
    assert manifest["fiscal_year"] == 2025
    assert manifest["period_end"] == "2025-12-31"
    assert manifest["source_url"] == SOURCE_URL
    assert manifest["retrieved_at"] == RETRIEVED_AT
    assert manifest["collector_name"] == "sec_edgar"
    assert manifest["collector_version"] == "1.0"
    assert wire["evidence_spans"][0]["span_id"] == span.span_id
    assert wire["evidence_spans"][0]["source_id"] == ref.source_id

    serialized = json.dumps(wire, ensure_ascii=False, sort_keys=True)
    assert str(tmp_path) not in serialized
    assert tmp_path.as_posix() not in serialized
    assert not any(
        token in key.lower()
        for key in manifest
        for token in ("path", "root", "location")
    )
    payload = {key: value for key, value in wire.items()
               if key not in {"bundle_sha256", "export_id"}}
    expected_sha = _sha256_json(payload)
    assert wire["bundle_sha256"] == expected_sha
    assert wire["export_id"] == "urn:company-wiki:source-export:sha256:" + expected_sha


def test_v2_bundle_identity_survives_configured_root_move(tmp_path):
    catalog, root, _, ref, span = _fixture(tmp_path, text_mode=True)
    first = _build(SourceVersionReader(catalog), ref, span).to_dict()

    moved_root = tmp_path / "relocated"
    root.path.rename(moved_root)
    relocated = SourceCatalog(
        replace(catalog.config, roots=(replace(root, path=moved_root),))
    )
    second = _build(SourceVersionReader(relocated), ref, span).to_dict()
    assert second == first


def test_v2_bundle_rejects_orphan_span_and_same_size_corrupted_bytes(tmp_path):
    catalog, _, raw_path, ref, span = _fixture(tmp_path)
    reader = SourceVersionReader(catalog)
    alien_span = EvidenceSpan.create(
        source_id=source_id_for_sha256("0" * 64),
        coordinates=EvidenceCoordinates(page_number=1),
        raw_text="Unrelated source.",
        structured_value=None,
        parser_name="fixture-parser",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )
    with pytest.raises((SourceReadError, ValueError)):
        _build(reader, ref, alien_span)

    raw_path.write_bytes(BODY[:-1] + b"X")
    assert raw_path.stat().st_size == len(BODY)
    with pytest.raises((SourceReadError, ValueError)):
        _build(reader, ref, span)


def test_v2_consumer_round_trips_a_verified_bundle(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    wire = _build(SourceVersionReader(catalog), ref, span).to_dict()

    loaded = _v2_module().SourceExportBundleV2.from_dict(wire)
    assert loaded.to_dict() == wire
    from_json = _v2_module().SourceExportBundleV2.from_json(
        json.dumps(wire, ensure_ascii=False).encode("utf-8")
    )
    assert from_json.to_dict() == wire


def test_v2_json_loader_rejects_duplicate_keys_before_hash_validation(tmp_path):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    wire = _build(SourceVersionReader(catalog), ref, span).to_dict()
    encoded = json.dumps(wire, ensure_ascii=False, separators=(",", ":"))
    duplicated = encoded.replace(
        '"schema_version":"2.0.0",',
        '"schema_version":"2.0.0","schema_version":"2.0.0",',
        1,
    )
    assert duplicated != encoded
    with pytest.raises((TypeError, ValueError)):
        _v2_module().SourceExportBundleV2.from_json(duplicated.encode("utf-8"))


@pytest.mark.parametrize(
    "tamper",
    (
        "bundle_hash",
        "counts",
        "unknown_field",
        "absolute_path_field",
        "orphan_span",
        "duplicate_source_id",
    ),
)
def test_v2_consumer_rejects_tampered_or_noncanonical_bundle(tmp_path, tamper):
    catalog, _, _, ref, span = _fixture(tmp_path, text_mode=True)
    wire = deepcopy(_build(SourceVersionReader(catalog), ref, span).to_dict())

    if tamper == "bundle_hash":
        wire["bundle_sha256"] = "0" * 64
    elif tamper == "counts":
        wire["counts"]["source_manifests"] += 1
        _rehash_wire(wire)
    elif tamper == "unknown_field":
        wire["unexpected"] = "must fail closed"
        _rehash_wire(wire)
    elif tamper == "absolute_path_field":
        wire["manifests"][0]["original_path"] = str(tmp_path / "raw" / "filing.pdf")
        _rehash_wire(wire)
    elif tamper == "orphan_span":
        alien = EvidenceSpan.create(
            source_id=source_id_for_sha256("0" * 64),
            coordinates=EvidenceCoordinates(page_number=1),
            raw_text="Unrelated source.",
            structured_value=None,
            parser_name="fixture-parser",
            parser_version="1.0.0",
            parse_status=ParseStatus.PARSED,
            quality_flags=(),
        )
        wire["evidence_spans"] = [alien.to_dict()]
        _rehash_wire(wire)
    elif tamper == "duplicate_source_id":
        wire["manifests"].append(deepcopy(wire["manifests"][0]))
        wire["counts"]["source_manifests"] = 2
        _rehash_wire(wire)

    with pytest.raises((TypeError, ValueError)):
        _v2_module().SourceExportBundleV2.from_dict(wire)
