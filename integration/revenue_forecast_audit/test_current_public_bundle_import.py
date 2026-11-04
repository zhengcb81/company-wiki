"""ROOT-owned CWP public producer -> AUDIT public importer integration.

The AUDIT checkout is explicit through AUDIT_CODE_ROOT. No test skip can turn a
missing AUDIT participant into a passing D4 result. All source, catalog, bundle,
and importer outputs live below pytest's temporary root.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_official_json import (
    open_verified_projection,
    select_verified_projection,
)
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
    NarrativeArtifactDraft,
    NarrativeArtifactStore,
)
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    build_projection_from_refs,
    persist_projection,
)
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader


ROOT = Path(__file__).resolve().parents[2]
AUDIT_ROOT = Path(os.environ["AUDIT_CODE_ROOT"]).resolve(strict=True)
AUDIT_CLI = AUDIT_ROOT / "skills/revenue-forecast-audit/scripts/summary_review_import.py"
T0 = "2026-10-10T00:00:00Z"
T1 = "2026-10-10T00:00:01Z"


def _encoded(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _run_audit_import(root: Path, body: bytes) -> tuple[dict, dict]:
    run_root = root / "audit-import"
    run_root.mkdir()
    try:
        carrier = run_root / "public-bundle.json"
        carrier.write_bytes(body)
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(AUDIT_CLI),
                "--bundle",
                str(carrier),
                "--run-id",
                "d4-root",
                "--attempt-id",
                "public-producer",
                "--out-root",
                str(run_root / "output"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr + completed.stdout
        receipt = json.loads(completed.stdout)
        mapped = json.loads(Path(receipt["map_file"]).read_text(encoding="utf-8"))
        report = json.loads(Path(receipt["import_report_file"]).read_text(encoding="utf-8"))
        upstream = json.loads(body)
        expected = [
            (claim["claim_id"], claim["text"], claim["evidence_ids"], claim.get("context_evidence_ids", []))
            for claim in upstream["summary"]["draft"]["claims"]
        ]
        actual = [
            (claim["claim_id"], claim["text"], claim["support"], claim["context"])
            for claim in mapped["claims"]
        ]
        assert actual == expected
        by_source = {span["span_id"]: span for span in upstream["evidence_spans"]}
        for fragment in mapped["source_fragments"]:
            span = by_source[fragment["fragment_id"]]
            assert fragment["text"] == (span["raw_text"] or "")
            assert fragment["source_ref"]["source_id"] == span["source_id"]
            assert fragment["source_ref"]["locator"] == span["locator"]
        assert report["input"]["bundle_sha256"] == _digest(body)
        return mapped, report
    finally:
        shutil.rmtree(run_root)


def _page(page: int) -> bytes:
    return _encoded(
        {
            "ok": True,
            "result": {
                "page": page,
                "page_size": 2,
                "page_count": 2,
                "item_total": 4,
                "items": [
                    {
                        "ref": page * 10 + company,
                        "org_id": company,
                        "org_name": f"Company {company}",
                        "q": "When do new product qualification and overseas shipments begin?",
                        "a": "Our new product has completed customer qualification and overseas shipments begin in the fourth quarter.",
                        "answered": True,
                        "created_at": "2026-09-01 10:00:00",
                        "updated_at": "2026-09-01 10:00:00",
                    }
                    for company in (1, 2)
                ],
            },
        }
    )


@contextmanager
def _published_projection(parent: Path):
    baseline = tuple(parent.iterdir())
    root = parent / "owned-source-state"
    root.mkdir()
    (root / "companies").mkdir()
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=root,
            catalog_dir=root / "catalog",
            roots=(RootSpec("company_raw", root / "companies", "company_raw"),),
        )
    )
    refs = []
    originals = []
    try:
        for page in (1, 2):
            body = _page(page)
            digest = _digest(body)
            request = {
                "schema_version": "official-source-import-request/2",
                "request_id": f"d4-audit-page-{page}",
                "max_bytes": 1_048_576,
                "content_sha256": digest,
                "mime_type": "application/json",
                "document_kind": "investor_relations",
                "source_subject": {
                    "kind": "multi_issuer_event",
                    "event_namespace": "fixture",
                    "event_id": "901",
                    "issuer_refs": [],
                    "attribution_status": "partial",
                },
                "capture_receipt": {
                    "capture_method": "local_document",
                    "tool_name": "d4-root-fixture",
                    "tool_call_id": f"page-{page}",
                    "captured_at": T0,
                    "response_bytes": len(body),
                    "content_sha256": digest,
                },
            }
            imported = import_official_json_source(catalog, original=body, request=request)
            refs.append(imported["source_ref"])
            originals.append(body)
        projection = build_projection_from_refs(
            catalog,
            refs=refs,
            layout_id="official-flat-list",
            issuer={"provider_company_id": 1},
            as_of_date="2026-10-08",
        )
        persist_projection(catalog, projection)
        subject = NarrativeSubject.from_projection(projection)
        view = open_verified_projection(
            catalog,
            projection_id=subject.item_key,
            expected_projection_sha256=subject.subject_sha256,
        )
        package = select_verified_projection(view, title="Business development Q&A")
        spans = package.evidence_spans
        assert spans and {span.source_id for span in spans} == {ref["source_id"] for ref in refs}
        answer = next(
            span
            for span in spans
            if span.structured_value["source_role"] in {"management", "company_filing"}
        )
        wire = NarrativeBundle.from_dict(
            {
                "schema_version": "narrative-bundle/3.0",
                "subject_binding": subject.to_dict(),
                "source_metadata": {
                    "source_class": "official_json",
                    "title": "Business development Q&A",
                    "document_kind": "investor_relations",
                    "language": view.language,
                },
                "quality_status": "verified",
                "selection": {
                    "status": package.status,
                    "coverage_complete": package.coverage_complete,
                    "source_units": package.source_units,
                    "candidate_count": package.candidate_count,
                    "selected_count": len(spans),
                    "omitted_candidate_count": package.omitted_candidate_count,
                    "dropped_financial_count": package.dropped_financial_count,
                    "pages_total": 2,
                    "pages_read": 2,
                    "lines_total": len(view.evidence_spans),
                    "tables_total": 0,
                    "tables_scanned": 0,
                },
                "evidence_spans": [span.to_dict() for span in spans],
                "summary": {
                    "status": "completed",
                    "translate": False,
                    "draft": {
                        "subject_id": subject.item_key,
                        "subject_sha256": subject.subject_sha256,
                        "language": view.language,
                        "status": "draft",
                        "claims": [
                            {
                                "claim_id": "business-update",
                                "text": answer.raw_text,
                                "evidence_ids": [answer.span_id],
                                "claim_type": "company_statement",
                                "modality": "planned",
                                "needs_review": False,
                            }
                        ],
                    },
                    "model": {
                        "adapter_id": "synthetic-local-model",
                        "model_id": "synthetic-local",
                        "prompt_version": "official-json/1.0.0",
                        "response_sha256": "a" * 64,
                    },
                },
                "prompt_review": {
                    "status": "not_reviewed",
                    "source_sha256": None,
                    "evidence_sha256": None,
                    "policy_hash": None,
                    "reviewed_at": None,
                },
                "versions": {
                    "parser": spans[0].parser_version,
                    "selector": "1.0.0",
                    "material": None,
                    "model": "synthetic-local",
                    "prompt": "official-json/1.0.0",
                    "bundle_producer": "1.0.0",
                },
                "replay": {"required": True, "locator_count": len(spans)},
            }
        ).to_dict()
        payload = _encoded(wire)
        generation = _digest(b"d4-audit-generation")
        anchor = subject.anchor_ref
        objects = LocalNarrativeObjectStore(catalog.config.catalog_dir)
        artifacts = NarrativeArtifactStore(catalog.store, objects)
        draft = NarrativeArtifactDraft(
            effect_id="d4-audit-producer",
            work_key=_digest(b"d4-audit-producer"),
            document_id=anchor["document_id"],
            source_id=anchor["source_id"],
            source_sha256=anchor["content_sha256"],
            producer_name="fixture.narrative",
            producer_version="3.0",
            policy_sha256=_digest(b"policy"),
            selection_status=wire["selection"]["status"],
            quality_status=wire["quality_status"],
            metadata_json=_encoded(
                {"subject_binding": subject.to_dict(), "generation_sha256": generation}
            ).decode("utf-8"),
            created_at=T0,
        )
        prepared = artifacts.prepare(draft, payload)
        artifacts.activate(
            "d4-audit-producer",
            verified_after_hash=prepared.content_sha256,
            activated_at=T1,
        )
        reader = NarrativeTransportReader(
            artifacts,
            SourceVersionReader(catalog),
            projection_loader=lambda selected: open_verified_projection(
                catalog,
                projection_id=selected.item_key,
                expected_projection_sha256=selected.subject_sha256,
            ),
        )
        reference = reader.reference_subject(subject, generation_sha256=generation)
        request = NarrativeReadRequest.from_dict(
            {
                "schema_version": "narrative-read-request/2",
                "narrative_ref": reference.to_dict(),
                "as_of_date": "2026-10-08",
                "expected_issuer": {"provider_company_id": 1},
            }
        )
        opened = reader.read(request)
        assert opened.data == payload
        assert len(originals) == 2 and all(body for body in originals)
        yield opened.data, subject
    finally:
        catalog.close()
        shutil.rmtree(root)
    assert tuple(parent.iterdir()) == baseline


def test_frozen_public_bundle_v2_contract_reaches_audit_cli(tmp_path: Path) -> None:
    body = (ROOT / "tests/fixtures/narrative_transport_v1/bundle.json").read_bytes()
    NarrativeBundle.from_dict(json.loads(body))
    _mapped, report = _run_audit_import(tmp_path, body)
    assert report["scope"]["selected_evidence_only"] is True


def test_cwp_projected_public_read_v3_reaches_audit_cli_and_cleans_scratch(
    tmp_path: Path,
) -> None:
    before = tuple(tmp_path.iterdir())
    with _published_projection(tmp_path) as (body, subject):
        mapped, _report = _run_audit_import(tmp_path, body)
        assert mapped["source_context"]["subject_binding"] == subject.to_dict()
        assert len({row["source_ref"]["source_id"] for row in mapped["source_fragments"]}) > 1
    assert tuple(tmp_path.iterdir()) == before
