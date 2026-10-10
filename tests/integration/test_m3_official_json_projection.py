"""M3-JSON public chain: import/2, shared raw, projections, replay, export.

Everything runs inside an owned temporary catalog.  The four representative
sealed pages are imported as copies through the public flow; the sealed run
itself is only read.  No network, no model calls.
"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import (
    SourceRef,
    SourceVersionReader,
)


_REVENUE_FORECAST_AUDIT_RUN = (
    Path.home() / "Projects" / "revenue-forecast-audit"
    / "runs" / "m3-20261009T184946-cn-688012")
SEALED_RUN = Path(os.environ.get(
    "M3_SEALED_RUN", str(_REVENUE_FORECAST_AUDIT_RUN)))
SEALED_SOURCES = SEALED_RUN / "execution" / "sources"
SEALED_AVAILABLE = SEALED_SOURCES.is_dir()
requires_sealed = pytest.mark.skipif(not SEALED_AVAILABLE, reason="sealed run not present")

LATEST_01 = "qa-latest-form-01.raw"
LATEST_18 = "qa-latest-form-18.raw"
QUESTIONS_01 = "qa-questions-form-01.raw"
PRECOLLECT_10 = "qa-precollect-form-10.raw"
LATEST_01_SHA = "416542b0c8f72400800edf69832df1bd3b48e50cf19c0019c647af445b97760b"


@contextmanager
def owned_catalog(tmp_path: Path):
    root = tmp_path / "m3json"
    (root / "companies").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=root,
            catalog_dir=root / "catalog",
            roots=(RootSpec("company_raw", root / "companies", "company_raw"),),
        )
    )
    try:
        yield root, catalog
    finally:
        catalog.close()


def import_v2_request(data: bytes, *, request_id="m3-it-1", subject=None):
    return {
        "schema_version": "official-source-import-request/2",
        "request_id": request_id,
        "max_bytes": 1048576,
        "content_sha256": hashlib.sha256(data).hexdigest(),
        "mime_type": "application/json",
        "document_kind": "investor_relations",
        "source_subject": subject or {
            "kind": "multi_issuer_event",
            "event_namespace": "official-provider-event",
            "event_id": "40766",
            "issuer_refs": [],
            "attribution_status": "partial",
        },
        "capture_receipt": {
            "capture_method": "local_document",
            "tool_name": "m3-fixture",
            "tool_call_id": request_id,
            "captured_at": "2026-10-10T00:00:00Z",
            "response_bytes": len(data),
            "content_sha256": hashlib.sha256(data).hexdigest(),
        },
    }


def _import_v2(catalog, data: bytes, **kwargs):
    from company_wiki.source_catalog.official_json_import import (
        import_official_json_source,
    )
    return import_official_json_source(
        catalog, original=data, request=import_v2_request(data, **kwargs))


@requires_sealed
def test_import_v2_registers_shared_raw_and_exact_read_roundtrip(tmp_path):
    data = (SEALED_SOURCES / LATEST_01).read_bytes()
    with owned_catalog(tmp_path) as (root, catalog):
        result = _import_v2(catalog, data)
        assert result["schema_version"] == "official-source-import-result/2"
        assert result["status"] == "imported_new"
        assert result["layout"]["layout_id"] == "official-paged-qa"
        assert result["layout"]["parse_status"] == "parsed"
        ref = SourceRef(**result["source_ref"])
        opened = SourceVersionReader(catalog).open_version(ref, purpose="source_export")
        assert opened.data == data
        # One shared copy only: nothing lands inside a per-company directory.
        files = sorted(str(p.relative_to(root)) for p in (root / "companies").rglob("*")
                       if p.is_file() and not p.name.endswith(".source.json"))
        assert len([name for name in files if name.endswith(".json")]) == 1
        assert "/_shared/" in files[0].replace("\\", "/")
        # The page has no display owner: it is not a single company document.
        manifest = SourceVersionReader(catalog).describe_version(ref)
        assert manifest["display_name"] is None


@requires_sealed
def test_import_v2_is_idempotent_and_same_sha_reuses_one_copy(tmp_path):
    data = (SEALED_SOURCES / LATEST_18).read_bytes()
    with owned_catalog(tmp_path) as (root, catalog):
        first = _import_v2(catalog, data, request_id="one")
        second = _import_v2(catalog, data, request_id="two")
        assert second["status"] == "deduplicated"
        assert first["source_ref"] == second["source_ref"]
        json_files = [p for p in (root / "companies").rglob("*.json")
                      if not p.name.endswith(".source.json")]
        assert len(json_files) == 1


@requires_sealed
def test_one_raw_two_issuer_projections_do_not_recopy_or_conflict(tmp_path):
    data = (SEALED_SOURCES / LATEST_01).read_bytes()
    with owned_catalog(tmp_path) as (_, catalog):
        imported = _import_v2(catalog, data)
        from company_wiki.source_catalog.official_json_projection import (
            build_projection_from_refs,
            persist_projection,
        )
        zhongwei = build_projection_from_refs(
            catalog, refs=[SourceRef(**imported["source_ref"])],
            layout_id="official-paged-qa",
            issuer={"market": "CN", "security_id": "688012",
                    "provider_company_id": 145565,
                    "provider_activity_company_id": 57790},
            as_of_date="2026-09-10")
        qingyi = build_projection_from_refs(
            catalog, refs=[SourceRef(**imported["source_ref"])],
            layout_id="official-paged-qa",
            issuer={"market": "CN", "security_id": "688038",
                    "provider_company_id": 152341,
                    "provider_activity_company_id": 57808},
            as_of_date="2026-09-10")
        assert zhongwei.projection_id != qingyi.projection_id
        zhongwei_ids = {r.provider_record_id for r in zhongwei.records if r.selected}
        qingyi_ids = {r.provider_record_id for r in qingyi.records if r.selected}
        assert zhongwei_ids == {2508406}
        assert qingyi_ids == {2508409}
        assert zhongwei.parent_source_refs == qingyi.parent_source_refs
        persist_projection(catalog, zhongwei)
        persist_projection(catalog, qingyi)
        again = persist_projection(catalog, zhongwei)
        assert again == zhongwei.projection_id
        raws = [p for p in (catalog.config.catalog_dir.parent / "companies").rglob("*.json")
                if not p.name.endswith(".source.json")]
        assert len(raws) == 1


@requires_sealed
def test_replay_verifies_parent_bytes_pointers_and_roles(tmp_path):
    data = (SEALED_SOURCES / LATEST_18).read_bytes()
    with owned_catalog(tmp_path) as (root, catalog):
        imported = _import_v2(catalog, data)
        from company_wiki.source_catalog.official_json_projection import (
            ProjectionError,
            build_projection_from_refs,
            replay_projection,
        )
        ref = SourceRef(**imported["source_ref"])
        projection = build_projection_from_refs(
            catalog, refs=[ref], layout_id="official-paged-qa",
            issuer={"market": "CN", "security_id": "688012",
                    "provider_company_id": 145565,
                    "provider_activity_company_id": 57790},
            as_of_date="2026-09-10")
        replayed = replay_projection(catalog, projection)
        assert replayed["verified_records"] == 1
        record = next(item for item in replayed["records"] if item["selected"])
        fields = {item["field"]: item for item in record["fields"]}
        assert fields["content"]["role"] == "management_answer"
        assert fields["content"]["text"] == json.loads(data)["datas"][0]["records"][2]["content"]
        # A tampered projection pointer is refused, not displayed.
        payload = projection.to_dict()
        payload["records"][0]["record_pointer"] = "/datas/0/records/9"
        from company_wiki.source_catalog.official_json_projection import (
            projection_from_dict,
        )
        with pytest.raises(ProjectionError):
            replay_projection(catalog, projection_from_dict(payload))
        # Parent bytes changed on disk: the public reader refuses the open.
        target = next((root / "companies").rglob("*.json"))
        original_bytes = target.read_bytes()
        target.write_bytes(original_bytes.replace(b"200", b"201", 1))
        with pytest.raises(Exception):
            replay_projection(catalog, projection)
        target.write_bytes(original_bytes)
        assert replay_projection(catalog, projection)["verified_records"] == 1


@requires_sealed
def test_projection_export_bundle_carries_refs_and_spans(tmp_path):
    data = (SEALED_SOURCES / QUESTIONS_01).read_bytes()
    with owned_catalog(tmp_path) as (_, catalog):
        imported = _import_v2(catalog, data)
        from company_wiki.source_catalog.official_json_projection import (
            build_projection_export,
            build_projection_from_refs,
        )
        projection = build_projection_from_refs(
            catalog, refs=[SourceRef(**imported["source_ref"])],
            layout_id="official-paged-qa",
            issuer={"market": "CN", "security_id": "688012",
                    "provider_company_id": 145565,
                    "provider_activity_company_id": 57790},
            as_of_date="2026-09-10")
        bundle = build_projection_export(catalog, projection)
        assert bundle["schema_version"] == "source-projection-export/1"
        assert bundle["projection"]["projection_id"] == projection.projection_id
        spans = bundle["evidence_spans"]
        assert spans and all(span["schema_version"] == "1.0.0" for span in spans)
        investor = [span for span in spans
                    if span["structured_value"]["role"] == "investor_question"]
        assert investor, "unanswered question stays an investor question"
        assert not [span for span in spans
                    if span["structured_value"]["role"] == "management_answer"]
        # Recompute the bundle identity from the payload.
        payload = {k: v for k, v in bundle.items()
                   if k not in {"bundle_sha256", "export_id"}}
        digest = hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        assert bundle["bundle_sha256"] == digest


def test_invalid_json_is_retained_but_not_indexed(tmp_path):
    from company_wiki.source_catalog.official_json_import import (
        import_official_json_source,
    )
    from company_wiki.source_catalog.official_source_flow import OfficialSourceError
    bad = b'{"success": true, "datas": [{'  # truncated
    with owned_catalog(tmp_path) as (_, catalog):
        with pytest.raises(OfficialSourceError) as raised:
            import_official_json_source(
                catalog, original=bad, request=import_v2_request(bad))
        assert str(raised.value) in {"invalid_json_syntax", "invalid_json_encoding"}
        # The refused page is still retained as recovery material.
        from company_wiki.source_catalog.official_source_flow import (
            list_retained_official_captures,
        )
        retained = [row for row in list_retained_official_captures(catalog)
                    if row.get("status") == "retained"]
        assert retained


def test_unknown_layout_registers_raw_and_refuses_projection(tmp_path):
    from company_wiki.source_catalog.official_json_import import (
        import_official_json_source,
    )
    from company_wiki.source_catalog.official_json_projection import (
        ProjectionError,
        build_projection_from_refs,
    )
    unseen = json.dumps({
        "status": "ok", "payload": {"rows": [{"key": "v"}]},
    }).encode("utf-8")
    with owned_catalog(tmp_path) as (_, catalog):
        result = import_official_json_source(
            catalog, original=unseen, request=import_v2_request(unseen))
        assert result["layout"]["parse_status"] == "unsupported_layout"
        assert result["layout"]["layout_id"] is None
        assert result["status"] == "imported_new"
        with pytest.raises(ProjectionError) as raised:
            build_projection_from_refs(
                catalog, refs=[SourceRef(**result["source_ref"])],
                layout_id="official-paged-qa",
                issuer={"provider_company_id": 1}, as_of_date="2026-09-10")
        assert raised.value.code in {
            "layout_pointer_not_found", "unsupported_json_layout"}


def test_import_v1_text_and_single_content_json_still_work(tmp_path):
    from company_wiki.source_catalog.official_source_flow import (
        import_official_source,
    )
    text = "Speaker A: hello\nSpeaker B: hi".encode("utf-8")
    golden = json.dumps({"content": "line one\nline two"}).encode("utf-8")
    with owned_catalog(tmp_path) as (_, catalog):
        def v1(data, mime, entity="Acme", kind="investor_call_transcript"):
            return {
                "schema_version": "official-source-import-request/1",
                "request_id": "legacy-" + mime,
                "source": {
                    "entity": entity, "market": "US", "security_id": "ACME",
                    "document_kind": kind, "title": "legacy doc",
                    "publisher": entity,
                    "source_url": "https://official.example/legacy",
                    "published_date": "2026-01-01",
                },
                "content_sha256": hashlib.sha256(data).hexdigest(),
                "mime_type": mime, "max_bytes": 1048576,
                "capture_receipt": {
                    "capture_method": "local_document", "tool_name": "legacy",
                    "tool_call_id": "legacy-1",
                    "captured_at": "2026-10-10T00:00:00Z",
                    "response_bytes": len(data),
                    "content_sha256": hashlib.sha256(data).hexdigest(),
                },
            }
        text_result = import_official_source(catalog, original=text, request=v1(text, "text/plain"))
        assert text_result["schema_version"] == "official-source-import-result/1"
        golden_result = import_official_source(catalog, original=golden, request=v1(golden, "application/json"))
        assert golden_result["status"] == "imported_new"
        # Legacy imports still land in the per-company directory.
        base = catalog.config.roots[0].path
        assert (base / "Acme").is_dir()


@requires_sealed
def test_import_v2_failure_retains_capture_and_recovers(tmp_path, monkeypatch):
    from company_wiki.source_catalog import canonical_writer as writer_module
    from company_wiki.source_catalog.official_json_import import (
        import_official_json_source,
    )
    from company_wiki.source_catalog.official_source_flow import (
        recover_official_source,
    )
    data = (SEALED_SOURCES / PRECOLLECT_10).read_bytes()
    with owned_catalog(tmp_path) as (_, catalog):
        def fail(*_args, **_kwargs):
            raise OSError("fixture-copy-primary")
        with monkeypatch.context() as patch:
            patch.setattr(writer_module.shutil, "copyfile", fail)
            with pytest.raises(OSError):
                import_official_json_source(
                    catalog, original=data, request=import_v2_request(data))
        # The failed import left a retained capture that recovery can finish.
        from company_wiki.source_catalog.official_source_flow import (
            list_retained_official_captures,
        )
        retained = [row for row in list_retained_official_captures(catalog)
                    if row.get("status") == "retained"]
        assert retained, "failed /2 import retained its capture"
        out = recover_official_source(catalog, capture_id=retained[0]["capture_id"])
        assert out["source_ref"]["content_sha256"] == hashlib.sha256(data).hexdigest()
        assert out["schema_version"] == "official-source-import-result/2"


def _cli(root: Path, request: dict, *, operation, input_file: Path | None = None):
    config = root / "config/catalog.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": "catalog",
        "roots": [{"root_id": "company_raw", "path": "companies", "kind": "company_raw"}],
    }), encoding="utf-8")
    path = root / f"{operation}-request.json"
    path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    repo = Path(__file__).resolve().parents[2]
    argv = [sys.executable, "-X", "utf8", "-B", "-m",
            "company_wiki.source_catalog.official_source_cli",
            "--operation", operation, "--config", str(config),
            "--project-root", str(root), "--request", str(path)]
    if input_file is not None:
        argv += ["--input-file", str(input_file)]
    return subprocess.run(argv, cwd=root,
                           env={**os.environ, "PYTHONPATH": str(repo / "src")},
                           capture_output=True, timeout=120)


@requires_sealed
def test_public_cli_import_project_read_replay_export(tmp_path):
    data = (SEALED_SOURCES / LATEST_18).read_bytes()
    with owned_catalog(tmp_path) as (root, catalog):
        staged_input = root / "page18.raw"
        staged_input.write_bytes(data)
        imported = _cli(root, import_v2_request(data), operation="import",
                        input_file=staged_input)
        assert imported.returncode == 0, imported.stderr
        source_ref = json.loads(imported.stdout)["source_ref"]

        project_request = {
            "schema_version": "official-json-projection-request/1",
            "parent_source_refs": [source_ref],
            "layout_id": "official-paged-qa",
            "issuer": {"market": "CN", "security_id": "688012",
                       "provider_company_id": 145565,
                       "provider_activity_company_id": 57790},
            "as_of_date": "2026-09-10",
            "persist": True,
        }
        projected = _cli(root, project_request, operation="project")
        assert projected.returncode == 0, projected.stderr
        projection = json.loads(projected.stdout)["projection"]
        assert projection["projection_id"].startswith(
            "urn:company-wiki:source-projection:sha256:")

        read = _cli(root, {"schema_version": "official-source-read-request/1",
                           "source_ref": source_ref}, operation="read")
        assert read.returncode == 0, read.stderr
        assert read.stdout == data  # exact original bytes, nothing else
        replayed = _cli(root, {
            "schema_version": "official-json-replay-request/1",
            "projection": projection,
        }, operation="replay")
        assert replayed.returncode == 0, replayed.stderr
        replay = json.loads(replayed.stdout)
        assert replay["verified_records"] == 1

        exported = _cli(root, {
            "schema_version": "source-projection-export-request/1",
            "projection": projection,
        }, operation="export")
        assert exported.returncode == 0, exported.stderr
        bundle = json.loads(exported.stdout)
        assert bundle["schema_version"] == "source-projection-export/1"

        # A tampered parent page refuses the public read before replay.
        catalog.close()
        target = next((root / "companies").rglob("*.json"))
        keep = target.read_bytes()
        target.write_bytes(keep.replace(b"200", b"201", 1))
        refused = _cli(root, {
            "schema_version": "official-json-replay-request/1",
            "projection": projection,
        }, operation="replay")
        assert refused.returncode == 2
        assert b"failure" in refused.stderr
        target.write_bytes(keep)


@requires_sealed
def test_multi_page_projection_reports_partial_pagination_honestly(tmp_path):
    page1 = (SEALED_SOURCES / LATEST_01).read_bytes()
    page18 = (SEALED_SOURCES / LATEST_18).read_bytes()
    with owned_catalog(tmp_path) as (_, catalog):
        first = _import_v2(catalog, page1, request_id="p1")
        second = _import_v2(catalog, page18, request_id="p18")
        assert first["source_ref"] != second["source_ref"]
        from company_wiki.source_catalog.official_json_projection import (
            build_projection_from_refs,
        )
        from company_wiki.source_catalog.source_reader import SourceRef
        projection = build_projection_from_refs(
            catalog,
            refs=[SourceRef(**first["source_ref"]), SourceRef(**second["source_ref"])],
            layout_id="official-paged-qa",
            issuer={"market": "CN", "security_id": "688012",
                    "provider_company_id": 145565,
                    "provider_activity_company_id": 57790},
            as_of_date="2026-09-10")
        selected = sorted(r.provider_record_id for r in projection.records if r.selected)
        # 2508406 on page 1 (closing remark) and 2508385 on page 18 (answered QA).
        assert selected == [2508385, 2508406]
        coverage = projection.coverage
        assert coverage["pagination_complete"] is False  # 2 of 65 pages only
        assert coverage["page_envelope_complete"] is True
        assert len(coverage["pages"]) == 2
        assert coverage["total_records"] == 6
        assert coverage["other_issuer_records"] == 3
        assert coverage["unattributed_records"] == 1
