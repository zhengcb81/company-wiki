"""MAIN's final business path: configured batch -> public reads -> committed RF.

The small synthetic framework test is independent of the N6 quality lanes. The
opt-in real test is for the final combined node, never ordinary CI or a vendor
benchmark. Real company bytes carry explicitly isolated Acme identity metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from benchmarks.narrative_document_types.evaluator import match_negative, match_positive
from company_wiki.source_contract import EvidenceSpan
from integration import test_narrative_batch_cli_e2e as cli_fixtures
from integration.test_narrative_runtime_e2e import (
    _E6_REAL_SAMPLES, _e6_source_paths, _pdf_bytes,
)
from support import narrative_batch_fixtures as batch_fixtures
from support.narrative_batch_fixtures import (
    KEY, assert_originals_and_foreign_jobs_untouched, isolated_batch_directory,
)
from tools.n4c_live_preflight import consumer_bootstrap


REPO = Path(__file__).resolve().parents[2]
RF_HEAD = "6e6b817a1a6e4567293a4dcb835815f3be508a03"
loopback_model_server = batch_fixtures.loopback_model_server
protected_inputs = cli_fixtures.r6_protected_inputs


def _original_byte_probe(point, raw, context, spans):
    """Map a raw TXT oracle through verified material bindings, not line guesses."""
    location = point["locator"]
    start, end = location["byte_start"], location["byte_end"]
    assert raw[start:end].decode("utf-8") == point["quote"]
    assert hashlib.sha256(raw[start:end]).hexdigest() == point["quote_sha256"]
    bindings = [binding for binding in context["transcript_byte_bindings"]
                if any(part["start"] < end and part["end"] > start
                       for part in binding["source_byte_ranges"])]
    assert bindings, "business quote has no final span bound to original bytes"
    cursor = start
    ranges = sorted((part["start"], part["end"])
                    for binding in bindings for part in binding["source_byte_ranges"])
    for left, right in ranges:
        if left <= cursor < right:
            cursor = max(cursor, min(right, end))
    assert cursor == end, "selected bindings do not cover the whole original quote"
    ids = {binding["evidence_id"] for binding in bindings}
    mapped = {**point, "locator": {
        "line_start": min(binding["material_line_start"] for binding in bindings),
        "line_end": max(binding["material_line_end"] for binding in bindings),
    }}
    return match_positive(mapped, [span for span in spans if span.span_id in ids])


def _sources(real):
    if not real:
        return [
            ("en", "annual.pdf", "Acme annual report", "annual_report",
             _pdf_bytes("Company launched a new product and expanded overseas capacity for customers.")),
            ("en", "ir.pdf", "Acme investor relations record", "investor_relations",
             _pdf_bytes("Company launched a new product after customer validation and added overseas capacity.")),
            ("en", "call.txt", "Acme earnings call transcript", "investor_call_transcript",
             b"Full Conference Call Transcript\nCEO: We added 31 new data centers across 5 continents.\n"),
        ], [], {}
    _, paths = _e6_source_paths()
    wanted = {"P01": "S01", "P07": "S07", "T01": "S09"}
    sources, originals, raw_by_sample = [], [], {}
    for sample in _E6_REAL_SAMPLES:
        sid = sample["sample_id"]
        if sid not in wanted:
            continue
        path = paths[sid]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == sample["sha256"]
        sample_id = wanted[sid]
        sources.append((sample["language"], sample_id + path.suffix, sample["title"],
                        sample["document_kind"], data))
        originals.append(path)
        raw_by_sample[sample_id] = data
    assert len(sources) == 3
    return sources, originals, raw_by_sample


def _exercise(tmp_path_factory, server, monkeypatch, capture, *, real, probes=None, queries=None,
              negative_probes=None):
    rf_value = os.environ.get("CWP_RF_PROJECT_ROOT")
    if not rf_value:
        pytest.skip("requires explicit read-only committed RF checkout")
    rf_root = Path(rf_value)
    actual_head = subprocess.run(["git", "-C", str(rf_root), "rev-parse", "HEAD"],
                                 check=True, capture_output=True, text=True, timeout=20).stdout.strip()
    assert actual_head == RF_HEAD, "review changed RF main before running this node"
    sources, originals, raw_by_sample = _sources(real)
    capture([*originals, *(rf_root / "assurance/runs" / name for name in
                         ("daily_alert.jsonl", "weekly_alert.jsonl", "weekly_manifest.json"))])
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    monkeypatch.setattr(batch_fixtures, "source_documents", lambda **_kwargs: sources)
    original_response = batch_fixtures.response_draft

    def selected_business_response(data):
        # Choose only an existing selected row; no new facts or selectors here.
        rows = data["evidence"]
        preferred = next((row for row in rows if any(needle in row[1] for needle in
                         ("EPI", "中试线", "available capacity", "data centers"))), rows[0])
        return original_response({**data, "evidence": [preferred]})

    monkeypatch.setattr(batch_fixtures, "response_draft", selected_business_response)
    with isolated_batch_directory(tmp_path_factory) as root:
        state = cli_fixtures._prepare(root, server.endpoint, include_policy=False)
        try:
            public_config = root / "config/catalog.json"
            public_config.parent.mkdir()
            public_config.write_bytes(state.config_path.read_bytes())
            state.config_path = public_config
            llm_config = root / "llm.yaml"
            llm_config.write_text(
                "llm:\n  provider: deepseek\n  model: stub-model\n  base_url: "
                + server.endpoint.removesuffix("/chat/completions")
                + "\n  max_tokens: 8192\n  temperature: 1.0\n", encoding="utf-8",
            )
            before_config = llm_config.read_bytes()
            if real:
                request = json.loads(state.request_path.read_text(encoding="utf-8"))
                request["max_seconds"] = 180
                state.request_path.write_text(json.dumps(request), encoding="utf-8")
            copies_before = cli_fixtures._originals(state)
            process, result = cli_fixtures._invoke(
                state, llm_config=llm_config, timeout_seconds=240 if real else 60,
            )
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert server.errors == [] and len(server.requests) == 3
            assert result["budget"]["unknown_reservations"] == 0
            assert result["budget"]["unsettled_reservations"] == 0
            assert len(result["documents"]) == 3
            assert all(document["artifact_ref"] is not None for document in result["documents"])
            exported = root / "rf-consumer"
            exported.mkdir()
            assert len(consumer_bootstrap(rf_root, RF_HEAD, exported)) == 6
            env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONUTF8="1",
                       PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")

            def invoke(command, request):
                call = subprocess.run(command, input=json.dumps(request).encode(), env=env,
                                      cwd=root, capture_output=True, timeout=90 if real else 40)
                assert call.returncode == 0, call.stderr.decode(errors="replace")
                assert KEY.encode() not in call.stdout + call.stderr
                return call

            golden = json.loads((REPO / "benchmarks/narrative_document_types/golden.json").read_text(encoding="utf-8"))
            if probes is None:
                probes = {"S01": {"G-S01-02"}, "S07": {"G-S07-01", "G-S07-02"}, "S09": {"G-S09-05"}}
            for ref, language, kind in state.indexed.values():
                name = next(source[1] for source in sources
                            if hashlib.sha256(source[4]).hexdigest() == ref.content_sha256)
                sample_id = Path(name).stem
                source_ref = {"schema_version": ref.schema_version, "document_id": ref.document_id,
                              "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                              "byte_size": ref.byte_size, "mime_type": ref.mime_type}
                transport = [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
                             "--config", str(state.config_path)]
                rf_command = [sys.executable, "-B", str(exported / "narrative_source_preparation.py"),
                              "--company-wiki-catalog-config", str(state.config_path)]
                reference = json.loads(invoke(rf_command + ["--operation", "reference"], {
                    "schema_version": "narrative-reference-request/1", "source_ref": source_ref,
                }).stdout)
                request = {"schema_version": "narrative-read-request/1", "narrative_ref": reference,
                           "as_of_date": "2026-10-06", "expected_source": {
                               "canonical_entity_id": "ent-acme", "market": "US", "security_id": "ACME",
                               "document_kind": kind, "fiscal_year": 2026,
                               "fiscal_period": "FY" if kind == "annual_report" else "Q1"}}
                context = json.loads(invoke(rf_command, request).stdout)
                assert context["summary"]["translate"] is False
                assert context["summary"]["draft"]["language"] == language
                spans = [EvidenceSpan.from_dict(span) for span in context["evidence_spans"]]
                assert spans and context["read_receipt"]["locator_count"] == len(spans)
                assert context["read_receipt"]["replay_status"] == "verified"
                bundle = None
                if kind == "investor_call_transcript":
                    # RF verifies bindings but deliberately omits them from its
                    # projection. Read the exact same artifact through CWP.
                    read = invoke(transport + ["--operation", "read"], request)
                    assert hashlib.sha256(read.stdout).hexdigest() == reference["artifact_sha256"]
                    assert json.loads(read.stderr)["replay_status"] == "verified"
                    bundle = json.loads(read.stdout)
                    assert bundle["evidence_spans"] == context["evidence_spans"]
                    if not real:
                        raw = next(source[4] for source in sources if source[1] == name)
                        quote = "We added 31 new data centers across 5 continents."
                        start = raw.index(quote.encode())
                        point = {"quote": quote, "quote_sha256": hashlib.sha256(quote.encode()).hexdigest(),
                                 "locator": {"byte_start": start, "byte_end": start + len(quote.encode())}}
                        assert _original_byte_probe(point, raw, bundle, spans)["result"] == "full"
                if real:
                    for point in golden["samples"][sample_id]["points"]:
                        if negative_probes and point["golden_id"] in negative_probes.get(sample_id, set()):
                            match = match_negative(point, spans)
                            assert match["result"] == "clean", (point["golden_id"], match)
                        if point["golden_id"] not in probes[sample_id]:
                            continue
                        match = (_original_byte_probe(point, raw_by_sample[sample_id], bundle, spans)
                                 if sample_id == "S09" else match_positive(point, spans))
                        assert match["result"] == "full", (point["golden_id"], match)
                query = ("EPI" if kind == "annual_report" else "中试线" if kind == "investor_relations"
                         else "available capacity") if real else "new product" if kind != "investor_call_transcript" else "data centers"
                if queries is not None:
                    query = queries[sample_id]
                    assert any(query.casefold() in (span.raw_text or '').casefold() for span in spans), (
                        sample_id, query, 'quality probe must query actual source wording'
                    )
                searched = invoke(transport + ["--operation", "evidence-search", "--query", query], request)
                view, receipt = json.loads(searched.stdout), json.loads(searched.stderr)
                assert view["items"] and receipt["locator_count"] == len(spans), (sample_id, query, view)
                found = json.loads(invoke(transport + ["--operation", "evidence-lookup", "--span-id", spans[0].span_id], request).stdout)
                assert found["items"] == [spans[0].to_dict()]
            again, resumed = cli_fixtures._invoke(
                state, llm_config=llm_config, timeout_seconds=240 if real else 60,
            )
            assert again.returncode == 0 and resumed["documents"] == result["documents"]
            assert resumed["budget"] == result["budget"] and len(server.requests) == 3
            assert llm_config.read_bytes() == before_config
            assert_originals_and_foreign_jobs_untouched(
                state, copies_before, output=process.stdout + process.stderr + again.stdout + again.stderr,
            )
        finally:
            state.catalog.close()


def test_synthetic_business_cli_framework(tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs):
    _exercise(tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs, real=False)


@pytest.mark.real_data
@pytest.mark.e2e
def test_real_business_cli_combined_quality_node(tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs):
    if os.environ.get("CWP_N6_RUN_REAL_E2E") != "1":
        pytest.skip("only run at the combined N6 quality node after main wiring")
    _exercise(tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs, real=True)
