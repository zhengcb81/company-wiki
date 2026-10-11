"""Public original provenance is owned by import, never by a consumer sidecar reader.

Two shared pages, two issuers and all recovery effects use a self-contained owned
TEMP. No provider/model/network is called; original bytes and config are retained.
"""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import canonical_writer as writer_module
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_source_flow import recover_official_source
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

REPO = Path(__file__).resolve().parents[2]
URL = "https://official.example/api/question_answer/answer_question_page"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def page(number):
    return encoded({
        "success": True, "code": 200,
        "datas": [{"current": number, "size": 2, "pages": 2, "total": 4,
                   "records": [{"id": number * 10 + issuer, "companyId": issuer,
                                "content": "Our new products entered customer qualification.",
                                "questionContent": "What is the customer qualification progress?",
                                "isAnswered": True, "crtTime": "2026-09-01 10:00:00",
                                "updTime": "2026-09-02 10:00:00"}
                               for issuer in (1, 2)]}],
        # A body URL is data, and must never become capture provenance.
        "body_link": "https://body.example/unrelated",
    })


def request(body, *, request_id="public-capture", nested=True):
    observation = {"url": URL, "method": "POST", "status_code": 200,
                   "content_type": "application/json;charset=UTF-8",
                   "response_bytes": len(body), "content_sha256": digest(body),
                   "complete": True,
                   "started_at": "2026-10-09T19:22:51+00:00",
                   "finished_at": "2026-10-09T19:22:54+00:00"}
    capture = {"capture_method": "local_document", "tool_name": "offline-import",
               "tool_call_id": request_id, "captured_at": "2026-10-11T00:00:00Z",
               "response_bytes": len(body), "content_sha256": digest(body),
               "http_requests": 0}
    if nested:
        capture["original_capture_observation"] = observation
    else:
        capture["url"] = URL
    return {"schema_version": "official-source-import-request/2",
            "request_id": request_id, "max_bytes": 1048576,
            "content_sha256": digest(body), "mime_type": "application/json",
            "document_kind": "investor_relations",
            "source_subject": {"kind": "multi_issuer_event",
                               "event_namespace": "official-event", "event_id": "42",
                               "issuer_refs": [], "attribution_status": "partial"},
            "capture_receipt": capture}


@contextmanager
def owned(tmp_path):
    before = {p.relative_to(tmp_path): p.read_bytes()
              for p in tmp_path.rglob("*") if p.is_file()}
    with TemporaryDirectory(prefix="capture-provenance-", dir=tmp_path) as temporary:
        root = Path(temporary)
        (root / "companies").mkdir()
        config = root / "config" / "catalog.json"
        config.parent.mkdir()
        config.write_bytes(encoded({"schema_version": "1.0", "catalog_dir": "catalog",
                                   "roots": [{"root_id": "company_raw", "path": "companies",
                                              "kind": "company_raw"}]}))
        yield SimpleNamespace(root=root, config=config, calls=[])
    assert {p.relative_to(tmp_path): p.read_bytes()
            for p in tmp_path.rglob("*") if p.is_file()} == before


def catalog(state):
    return SourceCatalog(load_catalog_config(state.config, project_root=state.root))


def invoke(state, operation, value, *, original=None):
    path = state.root / (operation + "-" + str(len(state.calls)) + ".json")
    path.write_bytes(encoded(value))
    command = [sys.executable, "-X", "utf8", "-B", "-m",
               "company_wiki.source_catalog.cli", "official", "--config", str(state.config),
               "--project-root", str(state.root), "--operation", operation, "--request", str(path)]
    if original is not None:
        raw = state.root / ("input-" + str(len(state.calls)) + ".raw")
        raw.write_bytes(original)
        command.extend(["--input-file", str(raw)])
    result = subprocess.run(command, cwd=state.root, capture_output=True, timeout=30,
                            env={**os.environ, "PYTHONPATH": str(REPO / "src")})
    state.calls.append((operation, result.returncode))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def export_manifest(state, refs):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", "-m",
         "company_wiki.source_catalog.source_export_v2_cli", "--config", str(state.config)],
        input=encoded({"schema_version": "2.0", "source_refs": refs, "evidence_spans": []}),
        cwd=state.root, env={**os.environ, "PYTHONPATH": str(REPO / "src")},
        capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_public_import_two_parents_two_issuers_persist_export_and_deduplicate(tmp_path):
    with owned(tmp_path) as state:
        original_config = state.config.read_bytes()
        imported = [invoke(state, "import", request(page(n), request_id="page-" + str(n)),
                           original=page(n)) for n in (1, 2)]
        refs = [item["source_ref"] for item in imported]
        projections = [invoke(state, "project", {
            "schema_version": "official-json-projection-request/1", "parent_source_refs": refs,
            "layout_id": "official-paged-qa", "issuer": {"provider_company_id": issuer},
            "as_of_date": "2026-10-08", "projection_version": "1.0.2", "persist": True,
        })["projection"] for issuer in (1, 2)]
        assert projections[0]["projection_id"] != projections[1]["projection_id"]
        for projection in projections:
            assert len(projection["parent_source_refs"]) == 2
            replay = invoke(state, "replay", {"schema_version": "official-json-replay-request/1",
                                              "projection_id": projection["projection_id"]})
            assert replay["verified_records"] == 2
            exported = invoke(state, "export", {"schema_version": "source-projection-export-request/1",
                                                "projection_id": projection["projection_id"]})
            assert exported["source_refs"] == projection["parent_source_refs"]
            selected = [r for r in projection["records"] if r["selected"]]
            issuer = projection["issuer"]["provider_company_id"]
            assert {r["provider_record_id"] for r in selected} == {10 + issuer, 20 + issuer}
        manifest = export_manifest(state, refs)
        assert len(manifest["manifests"]) == 2
        assert {m["source_url"] for m in manifest["manifests"]} == {URL}
        assert all(m["published_date"] is None and m["display_name"] is None
                   for m in manifest["manifests"])
        originals = {p: p.read_bytes() for p in (state.root / "companies").rglob("*") if p.is_file()}
        assert len([p for p in originals if not p.name.endswith(".source.json")]) == 2
        for ref in refs:
            with_catalog = catalog(state)
            try:
                row = with_catalog.reader.exact_source_version(ref["document_id"])
                metadata = json.loads(row["metadata_json"])
                assert metadata["acquisition"]["source_url"] == URL
            finally:
                with_catalog.close()
        changed = request(page(1), request_id="second-observation")
        changed["capture_receipt"]["original_capture_observation"]["url"] = URL + "?next=1"
        duplicate = invoke(state, "import", changed, original=page(1))
        assert duplicate["status"] == "deduplicated" and duplicate["download_events"] == 0
        assert duplicate["source_ref"] == refs[0]
        assert {p: p.read_bytes() for p in originals} == originals
        assert export_manifest(state, refs) == manifest
        assert state.config.read_bytes() == original_config


@pytest.mark.parametrize("observation", ["direct", "absent", "invalid", "other-page", "other-size"])
def test_capture_url_is_data_owned_and_missing_or_unbound_url_stays_unknown(tmp_path, observation):
    body = page(1)
    req = request(body, nested=observation != "direct")
    if observation == "absent":
        del req["capture_receipt"]["original_capture_observation"]
    elif observation == "invalid":
        req["capture_receipt"]["original_capture_observation"]["url"] = "https://user:secret@official.example/private"
    elif observation == "other-page":
        req["capture_receipt"]["original_capture_observation"]["content_sha256"] = digest(page(2))
    elif observation == "other-size":
        req["capture_receipt"]["original_capture_observation"]["response_bytes"] += 1
    with owned(tmp_path) as state:
        imported = invoke(state, "import", req, original=body)
        manifest = export_manifest(state, [imported["source_ref"]])["manifests"][0]
        assert manifest["source_url"] == (URL if observation == "direct" else None)
        assert imported["download_events"] == 0
        assert "body.example" not in str(manifest["source_url"])


def test_failed_commit_retains_capture_and_recovery_publishes_same_true_url(tmp_path, monkeypatch):
    body = page(1)
    req = request(body, request_id="lost-commit")
    original_request = deepcopy(req)
    with owned(tmp_path) as state:
        active = catalog(state)
        try:
            def fail(*_args, **_kwargs):
                raise OSError("owned-copy-fault")
            with monkeypatch.context() as patch:
                patch.setattr(writer_module.CanonicalSourceWriter, "_atomic_copy", fail)
                with pytest.raises(OSError, match="owned-copy-fault") as caught:
                    import_official_json_source(active, original=body, request=req)
            capture_id = caught.value.capture_id
            descriptor = active.config.catalog_dir / "staging" / (capture_id + ".capture.json")
            retained = json.loads(descriptor.read_text(encoding="utf-8"))
            assert retained["request"]["capture_receipt"] == req["capture_receipt"]
            retained_raw = descriptor.parent / retained["staged_name"]
            assert retained_raw.read_bytes() == body
            recovered = recover_official_source(active, capture_id=capture_id)
            assert recovered["download_events"] == 0
            assert recovered["capture_receipt"] == req["capture_receipt"]
            ref = SourceRef(**recovered["source_ref"])
            assert SourceVersionReader(active).open_version(ref, purpose="source_export").data == body
            assert not descriptor.exists() and not retained_raw.exists()
            again = recover_official_source(active, capture_id=capture_id)
            assert again["source_ref"] == recovered["source_ref"]
        finally:
            active.close()
        manifest = export_manifest(state, [recovered["source_ref"]])["manifests"][0]
        assert manifest["source_url"] == URL and manifest["published_date"] is None
        assert req == original_request


def test_legacy_immutable_shared_row_is_not_rewritten_by_a_later_true_capture(tmp_path):
    body = page(1)
    legacy_url = "https://official.invalid/shared-json"
    legacy_request = request(body, request_id="old-capture")
    del legacy_request["capture_receipt"]["original_capture_observation"]
    with owned(tmp_path) as state:
        active = catalog(state)
        try:
            writer = writer_module.CanonicalSourceWriter(active)
            staged = writer.staging_root / "legacy-shared.json"
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(body)
            legacy = writer.import_shared_original_staged(
                request_id="legacy-import", document_kind="investor_relations",
                title="legacy shared JSON page", source_url=legacy_url, publisher="official",
                staged_path=staged, content_sha256=digest(body), byte_size=len(body),
                mime_type="application/json", retrieved_at="2026-10-10T00:00:00Z",
                capture_receipt=legacy_request["capture_receipt"],
                provenance_extensions={"official_capture": legacy_request["capture_receipt"]},
            )
            before = {p: p.read_bytes() for p in (state.root / "companies").rglob("*") if p.is_file()}
            later = import_official_json_source(active, original=body, request=request(body))
            assert later["status"] == "deduplicated" and later["download_events"] == 0
            assert SourceRef(**later["source_ref"]) == legacy.source_ref
            assert SourceVersionReader(active).describe_version(legacy.source_ref)["source_url"] == legacy_url
            assert {p: p.read_bytes() for p in before} == before
        finally:
            active.close()
        assert export_manifest(state, [later["source_ref"]])["manifests"][0]["source_url"] == legacy_url


@pytest.mark.parametrize("character", ["\x7f", "\x85", "\x9f"])
def test_capture_url_control_characters_remain_unknown(character):
    from company_wiki.source_catalog.official_json_import import _captured_source_url

    receipt = request(page(1), nested=False)["capture_receipt"]
    receipt["url"] = URL + character
    assert _captured_source_url(receipt) is None
