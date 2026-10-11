"""One public W03 semantic/version node; synthetic HTTP, immutable real TXT.

Policy bootstrap changes the parent producer's actual execution version, never
saved results. Spawned workers must execute that frozen version themselves.
"""
import pytest

from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_batch import _thaw_generations
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_SELECTOR_NAME, NARRATIVE_SELECTOR_VERSION, parse_transcript_text, select_narrative_evidence,
)
from company_wiki.source_catalog.narrative_retrieval import (
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
    NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
    NarrativeEvidenceResolver,
)
from company_wiki.source_contract import source_id_for_sha256
from support import narrative_batch_fixtures as raw_fixtures
from support import official_json_batch_fixture as fixtures
from support.narrative_transport_fixture import published_fixture
from company_wiki.automation.narrative_transport import NarrativeTransportReader


official_json_loopback_model = fixtures.official_json_loopback_model
INDUSTRY_EN = "Recent export licensing restrictions have tightened across the semiconductor industry."
INDUSTRY_ZH = "行业出口许可政策近期收紧，出口审批周期延长。"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "narrative_real_transcript" / "MSFT_Q4_2026_earnings_call.txt"
FIXTURE_SHA = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
LEGACY_SHA = "11ad9c7f21c92d10847861f387a16ce1035f94da6a47a50128b354d0594b6d9f"


def _semantic_fixture(monkeypatch):
    documents = raw_fixtures.source_documents
    encode = fixtures.encoded

    def source_documents(**kwargs):
        rows = documents(**kwargs)
        return [(*row[:4], row[4] + ("CEO: " + INDUSTRY_EN + "\n").encode())
                if row[1] == "call-en.txt" else row for row in rows]

    def encoded(value):
        if isinstance(value, dict) and isinstance(value.get("datas"), list):
            value = deepcopy(value)
            for page in value["datas"]:
                if page["current"] == 2:
                    for record in page["records"]:
                        record["content"] = INDUSTRY_ZH if record["companyId"] == 1 else INDUSTRY_EN
        return encode(value)

    # Change synthetic inputs before their actual SHA/import/scan, preserving
    # all source/projection/Worker checks and the existing model's 400 cap.
    monkeypatch.setattr(raw_fixtures, "source_documents", source_documents)
    monkeypatch.setattr(fixtures, "encoded", encoded)


def _invoke(state, path, run_id, *, policy=None):
    if policy is None:
        return fixtures.invoke_batch(state, path, run_id)
    bootstrap = (
        "import sys; from company_wiki.source_catalog import narrative_evidence as n; "
        "from company_wiki.automation import narrative_batch_request as r; "
        "v=sys.argv.pop(1); n.NARRATIVE_SELECTOR_VERSION=v; "
        "r.NARRATIVE_SELECTOR_VERSION=v; "
        "from company_wiki.automation.narrative_batch_cli import main; "
        "raise SystemExit(main())"
    )
    command = [sys.executable, "-B", "-c", bootstrap, policy,
               "--project-root", str(state.root), "--catalog-config", str(state.config_path),
               "--automation-db", str(state.automation_db),
               "--work-dir", str(state.root / ("work-" + run_id)), "--request", str(path)]
    process = subprocess.run(command, cwd=state.root, env=fixtures.subprocess_env(),
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert fixtures.KEY not in process.stdout + process.stderr
    result = json.loads(process.stdout)
    assert result["schema_version"] == "narrative-batch-result/2"
    state.calls.append({"command": command, "exit_code": process.returncode,
                        "receipt": result, "stderr": process.stderr})
    return process, result


def _dump(path):
    with closing(sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True)) as db:
        return tuple(db.iterdump())


def _reads(state, receipt, version, *, industry):
    assert receipt["status"] == "completed", receipt
    assert len(receipt["items"]) == 3
    refs = {}
    for item in receipt["items"]:
        assert item["status"] == "completed" and item["errors"] == []
        ref = item["artifact_ref"]
        wire, replay = fixtures.invoke_read(state, ref)
        bundle = NarrativeBundle.from_dict(wire)
        assert bundle.versions.selector == version
        assert replay["replay_status"] == "verified" and bundle.summary.translate is False
        native = {span.raw_text for span in bundle.evidence_spans}
        expected = INDUSTRY_ZH if item["kind"] == "official_json" and (
            ref["subject_binding"]["issuer"]["provider_company_id"] == 1) else INDUSTRY_EN
        assert (expected in native) is industry, (version, expected, native)
        if industry:
            matching = [span for span in bundle.evidence_spans if span.raw_text == expected]
            assert all(span.structured_value["source_role"] == "management" for span in matching)
            assert all("current_industry_context" in span.structured_value["selection_reasons"]
                       for span in matching)
        if item["kind"] == "official_json":
            assert bundle.subject.to_dict() == ref["subject_binding"]
            expected_parents = {parent["source_id"] for parent in state.parent_refs} if industry else {
                state.parent_refs[0]["source_id"]}
            assert {span.source_id for span in bundle.evidence_spans} == expected_parents
            assert all("translation" not in span.structured_value["role"]
                       for span in bundle.evidence_spans)
        else:
            assert bundle.source_ref.to_dict() == state.raw_ref
        refs[item["item_key"]] = ref
    return refs


def _frozen(state, run_id, version):
    run = NarrativeRunStore(state.automation_db).get_run(run_id)
    assert run is not None
    binding = json.loads(run.binding_json)
    assert binding["execution_versions"]["selector"] == version
    manifests = _thaw_generations(binding)
    assert len(manifests) == 3
    assert all(manifest["execution_versions"]["selector"] == version
               for manifest in manifests.values())
    return binding


def _prompt_industry(server, state, *, offset):
    records = server.requests[offset:]
    assert len(records) == 3
    issuer_by_subject = {subject.item_key: subject.issuer["provider_company_id"]
                         for subject in state.subjects}
    for request in records:
        projected = "subject" in request
        key = request["subject"]["subject_id"] if projected else request["source"]["source_id"]
        expected = INDUSTRY_ZH if projected and issuer_by_subject[key] == 1 else INDUSTRY_EN
        matching = [row for row in request["evidence"] if expected in row[1]]
        assert matching, request["schema_version"]
        assert all((row[2] if len(row) > 2 else request["default_source_role"]) == "management"
                   for row in matching)


def _trace(state, receipt, post_count):
    print("W03-PUBLIC-NODE " + json.dumps({
        "run_id": receipt["run_id"], "status": receipt["status"], "budget": receipt["budget"],
        "loopback_posts": post_count,
        "actual_cli_calls": [{"argv": call["command"], "exit_code": call["exit_code"]}
                             for call in state.calls],
        "original_sha256": sorted(fixtures.sha(data) for data in state.originals.values()),
        "config_sha256": fixtures.sha(state.config_bytes),
        "artifacts": [{"item_key": item["item_key"], "status": item["status"],
                       "artifact_sha256": item["artifact_ref"]["artifact_sha256"],
                       "artifact_version_id": item["artifact_ref"]["artifact_version_id"],
                       "byte_size": item["artifact_ref"]["byte_size"]}
                      for item in receipt["items"]],
    }, sort_keys=True))


def test_new_default_public_mixed_selects_actual_industry_then_resume_reuse_is_free(
    tmp_path, monkeypatch, official_json_loopback_model,
):
    server = official_json_loopback_model
    _semantic_fixture(monkeypatch)
    with fixtures.official_batch_state(tmp_path) as state:
        path = fixtures.request_for(state, server.endpoint, "w03-current")
        process, first = _invoke(state, path, "w03-current")
        assert process.returncode == 0, (first, process.stderr)
        refs = _reads(state, first, NARRATIVE_SELECTOR_VERSION, industry=True)
        _frozen(state, "w03-current", NARRATIVE_SELECTOR_VERSION)
        assert len(server.requests) == 3 and server.errors == []
        _prompt_industry(server, state, offset=0)
        assert json.loads(path.read_bytes())["model"]["max_output_tokens"] == 400
        assert first["budget"]["tokens"] == 276
        before_auto, before_source = _dump(state.automation_db), _dump(state.catalog.config.database_path)
        process, resumed = _invoke(state, path, "w03-current")
        assert process.returncode == 0 and resumed["items"] == first["items"]
        assert resumed["budget"] == first["budget"]
        assert _dump(state.automation_db) == before_auto
        assert _dump(state.catalog.config.database_path) == before_source
        reuse_path = fixtures.request_for(state, server.endpoint, "w03-reuse")
        process, reused = _invoke(state, reuse_path, "w03-reuse")
        assert process.returncode == 0
        assert _reads(state, reused, NARRATIVE_SELECTOR_VERSION, industry=True) == refs
        assert reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
        assert len(server.requests) == 3 and server.errors == []
        _trace(state, first, len(server.requests))


@pytest.mark.parametrize("old_version", ["0.6.0", "0.7.0"])
def test_real_frozen_old_mixed_is_read_only_under_new_policy_and_not_new_cache(
    tmp_path, monkeypatch, official_json_loopback_model, old_version,
):
    server = official_json_loopback_model
    _semantic_fixture(monkeypatch)
    with fixtures.official_batch_state(tmp_path) as state:
        path = fixtures.request_for(state, server.endpoint, "w03-history")
        process, old = _invoke(state, path, "w03-history", policy=old_version)
        assert process.returncode == 0, (old, process.stderr)
        old_refs = _reads(state, old, old_version, industry=old_version != "0.6.0")
        original_binding = _frozen(state, "w03-history", old_version)
        before_auto, before_source = _dump(state.automation_db), _dump(state.catalog.config.database_path)
        process, resumed = _invoke(state, path, "w03-history", policy=NARRATIVE_SELECTOR_VERSION)
        assert process.returncode == 0 and resumed["items"] == old["items"], resumed
        assert resumed["budget"] == old["budget"]
        assert _frozen(state, "w03-history", old_version) == original_binding
        assert _reads(state, resumed, old_version, industry=old_version != "0.6.0") == old_refs
        assert _dump(state.automation_db) == before_auto
        assert _dump(state.catalog.config.database_path) == before_source
        assert len(server.requests) == 3
        new_path = fixtures.request_for(state, server.endpoint, "w03-after-upgrade")
        process, current = _invoke(state, new_path, "w03-after-upgrade", policy=NARRATIVE_SELECTOR_VERSION)
        assert process.returncode == 0, (current, process.stderr)
        new_refs = _reads(state, current, NARRATIVE_SELECTOR_VERSION, industry=True)
        _frozen(state, "w03-after-upgrade", NARRATIVE_SELECTOR_VERSION)
        assert all(new_refs[key]["artifact_version_id"] != old_refs[key]["artifact_version_id"]
                   for key in old_refs)
        assert len(server.requests) == 6 and server.errors == []
        _prompt_industry(server, state, offset=3)
        assert current["budget"]["tokens"] == 276
        _trace(state, current, len(server.requests))


def _fingerprint(package):
    value = {"fixture_sha256": FIXTURE_SHA, "document_kind": package.document_kind,
             "status": package.status, "selection_limit": package.selection_limit,
             "candidate_count": package.candidate_count,
             "dropped_financial_count": package.dropped_financial_count,
             "source_units": package.source_units,
             "omitted_candidate_count": package.omitted_candidate_count,
             "coverage_complete": package.coverage_complete,
             "spans": [span.to_dict() for span in package.evidence_spans]}
    return hashlib.sha256(fixtures.encoded(value)).hexdigest()


def test_full_true_txt_both_saved_policies_resolve_every_original_group(tmp_path):
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA
    source_id = source_id_for_sha256(FIXTURE_SHA)
    parsed = parse_transcript_text(raw.decode(), source_id=source_id,
                                  source_sha256=FIXTURE_SHA, language="en", parser_version="0.3.1")
    packages = {version: select_narrative_evidence(
        parsed, title=FIXTURE.name, existing_kind="investor_call_transcript", selector_version=version)
        for version in ("0.6.0", "0.7.0")}
    assert _fingerprint(packages["0.6.0"]) == LEGACY_SHA
    assert _fingerprint(packages["0.7.0"]) == "c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478"
    default = select_narrative_evidence(parsed, title=FIXTURE.name,
                                       existing_kind="investor_call_transcript")
    assert NARRATIVE_SELECTOR_VERSION == "0.7.1"
    assert _fingerprint(default) == _fingerprint(packages["0.7.0"])
    business = [span for span in default.evidence_spans
                if span.structured_value["source_role"] == "management"]
    for anchor in ("what we launched with Perception", "50% less cost", "90% of the tasks",
                   "if a given model goes away", "still continue your cyber operations",
                   "my math has changed", "price performance on silicon", "token usage",
                   "mix of the portfolio"):
        assert any(anchor in span.raw_text for span in business), anchor
    assert packages["0.7.0"].candidate_count == 103
    assert len(packages["0.7.0"].evidence_spans) == 96
    assert packages["0.7.0"].omitted_candidate_count == 7
    assert packages["0.7.0"].status == "partial"
    before = {path.relative_to(tmp_path): path.read_bytes()
              for path in tmp_path.rglob("*") if path.is_file()}
    path = tmp_path / "owned-real-transcript.txt"
    assert not path.exists()
    path.write_bytes(raw)
    try:
        for version, package in packages.items():
            record = {"title": FIXTURE.name, "selection_status": package.status,
                      "coverage_complete": package.coverage_complete,
                      "replay_contract": {
                          "schema_version": NARRATIVE_REPLAY_CONTRACT_SCHEMA_VERSION,
                          "source_format": "transcript_txt", "language": "en",
                          "existing_kind": "investor_call_transcript",
                          "parser_name": parsed.units[0].parser_name, "parser_version": "0.3.1",
                          "parser_options": {}, "selector_name": NARRATIVE_SELECTOR_NAME,
                          "selector_version": version, "max_selected": package.selection_limit},
                      "summary_input": package.summary_input()}
            resolver = NarrativeEvidenceResolver(
                {"schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION, "sources": [record]},
                raw_paths_by_source_id={source_id: path})
            for row in record["summary_input"]["evidence"]:
                resolved = resolver.resolve_group(
                    source_id=source_id, evidence_group_id=row.get("context_group_id") or row["evidence_id"])
                assert resolved.raw_text == row["raw_text"]
                assert resolved.locators == tuple(row["locators"])
                assert resolved.raw_text_sha256 == row["raw_text_sha256"]
        assert path.read_bytes() == raw and FIXTURE.read_bytes() == raw
    finally:
        path.unlink()
    assert {path.relative_to(tmp_path): path.read_bytes()
            for path in tmp_path.rglob("*") if path.is_file()} == before

    _public_true_txt_new_anchor(tmp_path, raw)


def _public_true_txt_new_anchor(tmp_path, raw):
    with published_fixture(tmp_path, source_spec={
        "data": raw, "title": FIXTURE.name, "language": "en",
        "sidecar_overrides": {
            "canonical_entity_id": "ent-msft", "display_name": "Microsoft",
            "market": "US", "security_id": "MSFT", "fiscal_year": 2026,
            "fiscal_period": "Q4", "period_end": "2026-06-30", "filing_date": "2026-07-30",
        },
    }) as fixture:
        reference = NarrativeTransportReader(fixture.artifacts, fixture.reader).reference(fixture.source_ref)
        request = fixture.read_request(reference, as_of_date="2026-10-08")
        wire = json.loads(fixture.payload)
        assert wire["versions"]["selector"] == NARRATIVE_SELECTOR_VERSION
        spans = {span["span_id"]: span for span in wire["evidence_spans"]}
        assert len(spans) == 96 and wire["selection"]["status"] == "partial"

        def cli(operation, *options):
            process = subprocess.run([
                sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
                "--config", str(fixture.config_path), "--operation", operation, *options,
            ], cwd=fixture.root, env=fixtures.subprocess_env(), input=fixtures.encoded(request),
                capture_output=True, timeout=40)
            assert process.returncode == 0, process.stderr.decode(errors="replace")
            result, receipt = json.loads(process.stdout), json.loads(process.stderr)
            assert receipt["status"] == "ok" and receipt["replay_status"] == "verified"
            assert receipt["view_sha256"] == hashlib.sha256(process.stdout).hexdigest()
            assert receipt["byte_size"] == len(process.stdout) and receipt["locator_count"] == 96
            assert result["versions"]["selector"] == NARRATIVE_SELECTOR_VERSION
            return result

        hits = cli("evidence-search", "--query", "90% of the tasks", "--limit", "2")["items"]
        assert hits
        assert any("90% of the tasks" in spans[eid]["raw_text"]
                   for hit in hits for eid in hit["evidence_ids"])
        for hit in hits:
            for eid, locator in zip(hit["evidence_ids"], hit["locators"], strict=True):
                found = cli("evidence-lookup", "--span-id", eid)
                assert found["items"] == [spans[eid]]
                assert found["items"][0]["locator"] == locator
                assert found["items"][0]["structured_value"]["source_role"] == "management"
        assert fixture.raw_path.read_bytes() == raw
