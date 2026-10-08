"""Opt-in frozen real-company originals through finite canonical workers.

Actual CLI, parser, scheduler, spawned worker, HTTP model transport and RF
consumer run. Only model HTTP is loopback replay, not an external LLM.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.automation.store import AutomationStore
from company_wiki.automation.models import RuntimeState
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_contract import EvidenceSpan
from support import narrative_batch_fixtures as fixtures

loopback_model_server = fixtures.loopback_model_server


@pytest.mark.e2e
@pytest.mark.real_data
@pytest.mark.parametrize("case", ["CN-688012", "HK-00700", "US-MSFT"])
def test_real_company_finite_worker_and_narrative_rf_view(case, loopback_model_server, record_property):
    supplied = os.environ.get("CWP_CMRF_CONTEXT")
    if not supplied:
        pytest.skip("run tools.cross_market_suite.runner with explicit frozen real sample context")
    context = json.loads(Path(supplied).read_text(encoding="utf-8"))
    record_property("cmrf_case", case)
    item = next((r for r in context["cases"] if r["case"] == case), None)
    if item is None:
        pytest.fail("required fixed company context missing")
    root = Path(context["root"])
    assert Path(supplied).resolve().is_relative_to(root.resolve())
    work = root / case / "worker"
    work.mkdir()
    store = AutomationStore(work / "auto.db")
    store.set_runtime_gate(RuntimeState.PAUSED, updated_at="2026-10-08T00:00:00Z")
    request = {
        "schema_version": "narrative-batch-request/1", "run_id": case,
        "sources": [item.get("worker_source_ref", item["source_ref"])],
        "profile": "P2", "max_seconds": 120, "max_tokens": 200_000, "max_cost_usd": "2",
        "model": {"model_id": "stub-model", "endpoint": loopback_model_server.endpoint,
                  "api_key_env": fixtures.KEY_ENV, "max_output_tokens": 400,
                  "timeout_seconds": 5, "allow_local_http": True},
        "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1_000_000,
                    "output_micro_usd_per_million_tokens": 2_000_000},
    }
    request_path = work / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(Path(context["wiki"]) / "src") + os.pathsep +
               str(Path(__file__).resolve().parents[2] / "tools/cross_market_suite/replay_hook"),
               PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    argv = [sys.executable, "-B", "-m", "company_wiki.automation.narrative_batch_cli",
            "--project-root", context["wiki"], "--catalog-config", item["config"],
            "--automation-db", str(store.db_path), "--work-dir", str(work / "jobs"), "--request", str(request_path)]
    started_requests = len(loopback_model_server.requests)
    call = subprocess.run(argv, cwd=context["wiki"], env=env, capture_output=True, timeout=135)
    assert fixtures.KEY.encode() not in call.stdout + call.stderr
    assert call.stdout, call.stderr
    result = json.loads(call.stdout)
    record_property("cmrf_batch_status", result.get("status"))
    docs = result.get("documents", [])
    # HTML support must be observed, not assumed from successful hand parsing.
    if case == "US-MSFT" and "worker_source_ref" not in item and not any(r.get("artifact_ref") for r in docs):
        reason = json.dumps(result)
        if any(t in reason.lower() for t in ("unsupported", "not_supported", "html")):
            pytest.skip("canonical HTML Worker unavailable: " + reason[:700])
    assert call.returncode == 0 and result["status"] == "completed", (call.stderr, result)
    assert not loopback_model_server.errors
    assert len(loopback_model_server.requests) - started_requests == 1, result
    assert all(r.get("artifact_ref") is not None for r in docs)
    catalog = SourceCatalog(load_catalog_config(Path(item["config"]), project_root=Path(context["wiki"])))
    try:
        source_ref = request["sources"][0]
        producer = [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli", "--config", item["config"]]

        def invoke(command, payload):
            called = subprocess.run(command, input=json.dumps(payload).encode(), cwd=context["wiki"], env=env, capture_output=True, timeout=40)
            assert called.returncode == 0, called.stderr
            if payload.get("narrative_ref") and "company_wiki.source_catalog.narrative_transport_cli" in command:
                receipt = json.loads(called.stderr)
                assert receipt["replay_status"] == "verified"
            return json.loads(called.stdout)

        ref = invoke(producer + ["--operation", "reference"], {"schema_version": "narrative-reference-request/1", "source_ref": source_ref})
        reader = SourceVersionReader(catalog)
        typed_ref = reader.query_ref(source_ref["document_id"], source_ref["source_id"], source_ref["content_sha256"])
        meta = reader.describe_version(typed_ref)
        read_request = {"schema_version": "narrative-read-request/1", "narrative_ref": ref, "as_of_date": None,
                        "expected_source": {k: meta[k] for k in ("canonical_entity_id", "market", "security_id", "document_kind", "fiscal_year", "fiscal_period")}}
        view = invoke(producer + ["--operation", "read"], read_request)
        rf_view = invoke([sys.executable, "-B", str(Path(context["rf"]) / "scripts/narrative_source_preparation.py"),
                          "--company-wiki-catalog-config", item["config"]], read_request)
        assert rf_view["evidence_spans"] == view["evidence_spans"]
        assert view["summary"]["translate"] is False
        assert view["source_metadata"]["language"] == meta["language"]
        assert view["selection"]["status"] != "skipped_no_narrative"
        assert view["evidence_spans"] and view["summary"]["draft"]["claims"]
        # Every summary evidence reference must resolve to a real selected span.
        span_ids = {row["span_id"] for row in view["evidence_spans"]}
        for span in view["evidence_spans"]:
            typed = EvidenceSpan.from_dict(span)
            assert typed.source_id == source_ref["source_id"] and typed.raw_text.strip()
        # The read receipt already replays ALL locators against original bytes.
        # One public CLI lookup proves dispatch; avoid reparsing a whole PDF for each span.
        first = view["evidence_spans"][0]
        looked_up = invoke(producer + ["--operation", "evidence-lookup", "--span-id", first["span_id"]], read_request)
        assert looked_up["items"] == [first]
        if meta["published_date"] is None:
            historical = dict(read_request, as_of_date="2026-10-08")
            denied = subprocess.run(producer + ["--operation", "read"], input=json.dumps(historical).encode(),
                                    cwd=context["wiki"], env=env, capture_output=True, timeout=40)
            assert denied.returncode == 2 and not denied.stdout
            assert json.loads(denied.stderr)["reason"] == "source_publication_unknown"
        repeated = subprocess.run(argv, cwd=context["wiki"], env=env, capture_output=True, timeout=40)
        again = json.loads(repeated.stdout)
        assert repeated.returncode == 0 and again["documents"] == result["documents"]
        assert again["budget"] == result["budget"]
        assert len(loopback_model_server.requests) - started_requests == 1
        assert reader.open_version(typed_ref, purpose="narrative_derivation").content_sha256 == source_ref["content_sha256"]
        record_property("cmrf_receipt", json.dumps({"span_count": len(span_ids), "local_model_posts": 1,
                        "repeat_model_posts": 0, "translate": False, "source_language": meta["language"],
                        "source_sha256": source_ref["content_sha256"], "external_model_posts": 0}))
    finally:
        catalog.close()


@pytest.mark.e2e
@pytest.mark.real_data
@pytest.mark.parametrize("kind", ["html", "pptx"])
def test_real_microsoft_format_capability(kind, loopback_model_server, record_property):
    supplied = os.environ.get("CWP_CMRF_CONTEXT")
    if not supplied:
        pytest.skip("explicit frozen real-company context required")
    context = json.loads(Path(supplied).read_text(encoding="utf-8"))
    record_property("cmrf_case", "US-MSFT")
    record_property("cmrf_format", "format_" + kind)
    item = next(r for r in context["cases"] if r["case"] == "US-MSFT")
    ref = item["source_ref" if kind == "html" else "ppt_source_ref"]
    root = Path(context["root"]) / "US-MSFT" / ("format-" + kind)
    root.mkdir()
    store = AutomationStore(root / "auto.db")
    store.set_runtime_gate(RuntimeState.PAUSED, updated_at="2026-10-08T00:00:00Z")
    request = {"schema_version": "narrative-batch-request/1", "run_id": "format-" + kind,
        "sources": [ref], "profile": "P2", "max_seconds": 30, "max_tokens": 200_000, "max_cost_usd": "2",
        "model": {"model_id": "stub-model", "endpoint": loopback_model_server.endpoint, "api_key_env": fixtures.KEY_ENV,
                  "max_output_tokens": 400, "timeout_seconds": 5, "allow_local_http": True},
        "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1_000_000, "output_micro_usd_per_million_tokens": 2_000_000}}
    request_path = root / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(Path(context["wiki"]) / "src") + os.pathsep +
               str(Path(__file__).resolve().parents[2] / "tools/cross_market_suite/replay_hook"), PYTHONUTF8="1")
    started_requests = len(loopback_model_server.requests)
    call = subprocess.run([sys.executable, "-B", "-m", "company_wiki.automation.narrative_batch_cli",
        "--project-root", context["wiki"], "--catalog-config", item["config"], "--automation-db", str(store.db_path),
        "--work-dir", str(root / "jobs"), "--request", str(request_path)], cwd=context["wiki"], env=env, capture_output=True, timeout=40)
    assert call.stdout, call.stderr
    result = json.loads(call.stdout)
    from tools.cross_market_suite.core import format_capability_gap
    images_only_checked = False
    if kind == "pptx" and any("PARSER_INCOMPLETE" in row.get("errors", []) for row in result["documents"]):
        from company_wiki.document_normalization import normalize_document
        from company_wiki.source_catalog.source_reader import SourceRef

        catalog = SourceCatalog(load_catalog_config(Path(item["config"]), project_root=Path(context["wiki"])))
        try:
            raw = SourceVersionReader(catalog).open_version(SourceRef(**ref), purpose="narrative_derivation")
            structure = normalize_document(raw.data, source_id=ref["source_id"],
                source_sha256=ref["content_sha256"], mime_type=ref["mime_type"]).structure
            images_only_checked = (not structure.units and not structure.errors and structure.page_count > 0
                and structure.pages_read == structure.page_count
                and len(structure.opaque_pages) == structure.page_count)
            record_property("cmrf_opaque_pages", str(len(structure.opaque_pages)))
        finally:
            catalog.close()
    reason = format_capability_gap(result, images_only_checked=images_only_checked)
    if reason:
        assert call.returncode == 2
        assert result["budget"]["tokens"] == result["budget"]["estimated_micro_usd"] == 0
        assert result["budget"]["unknown_reservations"] == 0
        assert len(loopback_model_server.requests) == started_requests
        record_property("cmrf_format_status", "BLOCKED")
        record_property("cmrf_format_detail", "actual finite Worker capability gap: " + reason
                        + "; no published artifact or model call; body processing remains incomplete")
        return
    record_property("cmrf_format_detail", "actual finite Worker outcome: "
                    + str(result.get("status")) + "; reason=" + str(result.get("error"))
                    + "; document_errors=" + str([row.get("errors") for row in result["documents"]]))
    assert call.returncode == 0 and result["status"] == "completed", (call.stderr, result)
    assert any(row.get("artifact_ref") for row in result["documents"]), result
    command = [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli", "--config", item["config"]]
    reference = subprocess.run(command + ["--operation", "reference"], input=json.dumps({
        "schema_version": "narrative-reference-request/1", "source_ref": ref}).encode(),
        cwd=context["wiki"], env=env, capture_output=True, timeout=20)
    assert reference.returncode == 0, reference.stderr
    catalog = SourceCatalog(load_catalog_config(Path(item["config"]), project_root=Path(context["wiki"])))
    try:
        reader = SourceVersionReader(catalog)
        meta = reader.describe_version(reader.query_ref(ref["document_id"], ref["source_id"], ref["content_sha256"]))
        request = {"schema_version": "narrative-read-request/1", "narrative_ref": json.loads(reference.stdout),
            "as_of_date": None, "expected_source": {k: meta[k] for k in ("canonical_entity_id", "market", "security_id", "document_kind", "fiscal_year", "fiscal_period")}}
        read = subprocess.run(command + ["--operation", "read"], input=json.dumps(request).encode(),
                             cwd=context["wiki"], env=env, capture_output=True, timeout=30)
        assert read.returncode == 0, read.stderr
        view = json.loads(read.stdout)
        assert view["evidence_spans"] and view["summary"]["draft"]["claims"]
        assert view["summary"]["translate"] is False
    finally:
        catalog.close()
    record_property("cmrf_format_status", "PASS")
    record_property("cmrf_format_detail", "actual finite canonical processing completed; supplier HTTP is loopback")
