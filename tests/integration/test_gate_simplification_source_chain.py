"""Opt-in G2 major node: immutable real bytes and committed consumer CLIs."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from integration import test_narrative_batch_cli_e2e as cli
from support import narrative_batch_fixtures as fixtures
from tools.n4c_live_preflight import consumer_bootstrap


loopback_model_server = fixtures.loopback_model_server
protected_inputs = cli.r6_protected_inputs
REPO = Path(__file__).resolve().parents[2]


def _head(root):
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=15,
    ).strip()


def _export_stockwiki(root, head, target):
    """Only committed package bytes; never execute a consumer owner's WIP."""
    archive = subprocess.check_output(
        ["git", "-C", str(root), "archive", "--format=zip", head,
         "stockwiki", "config/llm_providers.yaml"], timeout=30,
    )
    with zipfile.ZipFile(io.BytesIO(archive)) as package:
        for entry in package.infolist():
            destination = (target / entry.filename).resolve()
            assert destination.is_relative_to(target.resolve())
            if entry.is_dir():
                continue
            assert entry.filename.startswith("stockwiki/") or entry.filename == "config/llm_providers.yaml"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package.read(entry))


def _exercise_real_sources_and_committed_consumers(
    tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs,
    *, current_mode=False,
):
    inputs = {name: os.environ.get(name) for name in (
        "CWP_G2_REAL_SOURCE_ROOT", "CWP_E2E_TRANSCRIPT_PATH",
        "CWP_RF_PROJECT_ROOT", "CWP_STOCKWIKI_PROJECT_ROOT",
    )}
    if not all(inputs.values()):
        pytest.skip("requires explicit read-only real originals and consumer roots")
    source_root = Path(inputs["CWP_G2_REAL_SOURCE_ROOT"])
    rf_root, sw_root = Path(inputs["CWP_RF_PROJECT_ROOT"]), Path(inputs["CWP_STOCKWIKI_PROJECT_ROOT"])
    samples = {row["sample_id"]: row for row in json.loads(
        (REPO / "benchmarks/narrative_document_types/samples.json").read_text(encoding="utf-8")
    )["samples"]}
    specs = [
        (source_root / samples["S07"]["relative_path"], samples["S07"]["sha256"], "zh", "ir.pdf",
         samples["S07"]["title"], "investor_relations"),
        (Path(inputs["CWP_E2E_TRANSCRIPT_PATH"]), samples["S09"]["sha256"], "en", "call.txt",
         samples["S09"]["title"], "investor_call_transcript"),
        (source_root / "companies/中微公司/raw/investor_relations/中微公司：投资者关系管理办法（2025年8月）.pdf",
         "76e146985388c926f2683e24af47e6a1ab0ce8a156864fb16e7df9a2cc99b678", "zh", "policy.pdf",
         "中微公司：投资者关系管理办法（2025年8月）.pdf", "ir_policy"),
        (source_root / "companies/新易盛/raw/research/新易盛：300502新易盛投资者关系管理制度20230703.pdf",
         "e9699886d539afebab6f8aa970d6db2e62b488606dcfc0bf0c486c18a8994380", "zh", "mislabel.pdf",
         "新易盛：300502新易盛投资者关系管理制度20230703.pdf", "investor_relations"),
    ]
    protected_inputs([row[0] for row in specs])
    previous = json.loads((REPO / "docs/plans/narrative-evidence-pilot-2026-09-26/harness_lanes/results/"
                           "g208_real_install_2026-10-07.json").read_text(encoding="utf-8"))
    protected_inputs([Path(path) for path in previous["protected_sha256"]])
    source_documents = []
    for path, digest, language, name, title, kind in specs:
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        source_documents.append((language, name, title, kind, data))
    monkeypatch.setattr(fixtures, "source_documents", lambda **_kwargs: source_documents)
    consumer_heads = {"rf": _head(rf_root), "stockwiki": _head(sw_root)}
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = cli._prepare(root, loopback_model_server.endpoint)
        try:
            # Finite public registration is idempotent and leaves unrelated jobs alone.
            relative_paths = {path.relative_to(root / "companies").as_posix()
                              for path in state.raw_paths.values()}
            state.catalog.register_sources(root_id="company_raw", relative_paths=relative_paths)
            if current_mode:
                # Isolated capture metadata only: unknown never becomes a fake date.
                with state.catalog.store.transaction() as connection:
                    connection.execute("UPDATE documents SET published_date=NULL")
            config = root / "config/catalog.json"
            config.parent.mkdir()
            config.write_bytes(state.config_path.read_bytes())
            state.config_path = config
            originals = cli._originals(state)
            process, result = cli._invoke(state)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert loopback_model_server.errors == []
            assert len(loopback_model_server.requests) == 3
            assert {data["source"]["language"] for data, _ in loopback_model_server.requests} == {"zh", "en"}
            rf_export, sw_export = root / "rf", root / "sw"
            rf_export.mkdir()
            sw_export.mkdir()
            consumer_bootstrap(rf_root, consumer_heads["rf"], rf_export)
            _export_stockwiki(sw_root, consumer_heads["stockwiki"], sw_export)
            env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(REPO / "src"), str(sw_export))),
                   "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHON_DOTENV_DISABLED": "1"}
            producer = [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
                        "--config", str(config)]
            consumer_config = root / "consumer.json"
            consumer_config.write_text(json.dumps({"schema_version": "1.0", "python_executable": sys.executable,
                "argv_prefix": producer, "timeout_s": 30, "max_stdout_bytes": 1_310_720}), encoding="utf-8")

            def invoke(argv, request):
                call = subprocess.run(argv, input=json.dumps(request).encode(), capture_output=True,
                                      env=env, cwd=root, timeout=45)
                assert call.returncode == 0, call.stderr.decode("utf-8", errors="replace")
                assert fixtures.KEY.encode() not in call.stdout + call.stderr
                return json.loads(call.stdout), json.loads(call.stderr) if call.stderr else None

            reports = []
            for document_id, (ref, language, _kind) in state.indexed.items():
                reference, _ = invoke(producer + ["--operation", "reference"], {
                    "schema_version": "narrative-reference-request/1", "source_ref": asdict(ref)})
                manifest = state.reader.describe_version(ref)
                request = {"schema_version": "narrative-read-request/1", "narrative_ref": reference,
                    "as_of_date": None if current_mode else "2026-10-08", "expected_source": {
                        "canonical_entity_id": "ent-acme", "market": "US", "security_id": "ACME",
                        "document_kind": manifest["document_kind"], "fiscal_year": 2026, "fiscal_period": "Q1"}}
                view, receipt = invoke(producer + ["--operation", "read"], request)
                assert receipt["replay_status"] == "verified"
                assert view["summary"]["translate"] is False
                assert view["source_metadata"]["language"] == language
                is_policy = ref.content_sha256 == specs[2][1]
                if is_policy:
                    assert view["selection"]["status"] == "skipped_no_narrative"
                    assert view["summary"]["status"] == "summary_not_needed"
                    assert view["evidence_spans"] == []
                else:
                    assert view["evidence_spans"] and view["summary"]["draft"]["claims"]
                    span = view["evidence_spans"][0]
                    looked_up, exact_receipt = invoke(producer + ["--operation", "evidence-lookup",
                                                               "--span-id", span["span_id"]], request)
                    assert looked_up["items"] == [span]
                    assert exact_receipt["replay_status"] == "verified"
                    searched, search_receipt = invoke(producer + ["--operation", "evidence-search",
                                                               "--query", span["raw_text"][:35]], request)
                    assert searched["items"]
                    assert search_receipt["replay_status"] == "verified"
                rf_view, _ = invoke([sys.executable, "-B", str(rf_export / "narrative_source_preparation.py"),
                                    "--company-wiki-catalog-config", str(config)], request)
                request_file = root / "read.json"
                request_file.write_text(json.dumps(request), encoding="utf-8")
                sw_view, _ = invoke([sys.executable, "-B", "-m", "stockwiki.cli", "source-read-narrative",
                                    "--request", str(request_file), "--reader-config", str(consumer_config)], request)
                assert rf_view["evidence_spans"] == view["evidence_spans"] == sw_view["evidence"]
                if current_mode:
                    assert receipt["as_of_date"] is None
                    assert receipt["manifest"]["published_date"] is None
                    assert rf_view["as_of_date"] is sw_view["as_of_date"] is None
                    assert rf_view["manifest"]["published_date"] is None
                    assert sw_view["manifest"]["published_date"] is None
                    historical = dict(request, as_of_date="2026-10-08")
                    refused = subprocess.run(producer + ["--operation", "read"],
                        input=json.dumps(historical).encode(), capture_output=True,
                        env=env, cwd=root, timeout=45)
                    assert refused.returncode == 2 and refused.stdout == b""
                    assert json.loads(refused.stderr)["reason"] == "source_publication_unknown"
                    refused_rf = subprocess.run([sys.executable, "-B", str(rf_export / "narrative_source_preparation.py"),
                        "--company-wiki-catalog-config", str(config)], input=json.dumps(historical).encode(),
                        capture_output=True, env=env, cwd=root, timeout=45)
                    assert refused_rf.returncode == 2 and refused_rf.stdout == b""
                    assert json.loads(refused_rf.stderr)["reason"] == "source_publication_unknown"
                    request_file.write_text(json.dumps(historical), encoding="utf-8")
                    refused_sw = subprocess.run([sys.executable, "-B", "-m", "stockwiki.cli", "source-read-narrative",
                        "--request", str(request_file), "--reader-config", str(consumer_config)],
                        capture_output=True, env=env, cwd=root, timeout=45)
                    assert refused_sw.returncode == 2 and refused_sw.stdout == b""
                    assert json.loads(refused_sw.stderr)["reason"] == "source_publication_unknown"
                reports.append({"source_sha256": ref.content_sha256, "source_id": ref.source_id,
                                "document_id": document_id, "language": language,
                                "span_count": len(view["evidence_spans"]), "zero_model_skip": is_policy,
                                "current_consumers_match": True, "replay_status": receipt["replay_status"]})
            again, repeated = cli._invoke(state)
            assert again.returncode == 0 and repeated["documents"] == result["documents"]
            assert repeated["budget"] == result["budget"]
            assert len(loopback_model_server.requests) == 3
            fixtures.assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr)
            report = {"schema_version": "r3a-current-material-chain/1" if current_mode else "g2-consolidated-node/1", "status": "passed",
                      "boundary": "real source bytes; fixture identity/publication; loopback model; committed consumer CLIs",
                      "consumer_heads": consumer_heads, "sources": reports,
                      "model_loopback_posts": 3, "resume_new_posts": 0, "live_provider_posts": 0,
                      "paid_calls": 0, "production_writes": 0, "budget": result["budget"]}
            if current_mode:
                report.update(as_of_date=None, publication=None,
                              historical_refusals_per_source=["CWP", "RF", "StockWiki"])
        finally:
            state.catalog.close()
    assert not root.exists()
    report["fixture_root_restored_absent"] = True
    output = os.environ.get("CWP_R3A_NODE_REPORT" if current_mode else "CWP_G2_NODE_REPORT")
    if output:
        path = Path(output).resolve()
        assert path.is_relative_to((REPO / ".planning").resolve()) and not path.exists()
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.mark.real_data
@pytest.mark.e2e
def test_real_ir_txt_procedure_and_misleading_title_current_consumers(
    tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs,
):
    _exercise_real_sources_and_committed_consumers(
        tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs)


@pytest.mark.real_data
@pytest.mark.e2e
def test_current_material_unknown_publication_real_consumers(
    tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs,
):
    _exercise_real_sources_and_committed_consumers(
        tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs, current_mode=True)
