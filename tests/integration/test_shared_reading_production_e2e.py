"""Shared reading strategies cross the real configured production boundaries.

The public request selects supported 0.9.0 in this independent lake. Bootstrap
contains only optional IO observations. No selector, parser or worker is faked.
HTTP is an explicit local fixture; supplier/LLM credentials are never used.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3

import pytest

from company_wiki.automation.models import canonical_json_hash, require_sha256
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_model_runtime import resolve_model_boundary
from company_wiki.automation.narrative_selection_generation import reading_material_sha256
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from integration import test_narrative_generation_reuse as reuse
from support import official_json_batch_fixture as official_json_fixtures


loopback_model_server = reuse.loopback_model_server

official_json_loopback_model = official_json_fixtures.official_json_loopback_model


def _launcher(root, *, hold_activation=False, count_source_opens=False):
    bootstrap = root / "reading-bootstrap"
    bootstrap.mkdir(exist_ok=True)
    bootstrap_source = '"""Isolated observers; selector version comes from the public request."""\n'
    if count_source_opens:
        bootstrap_source += """from pathlib import Path
import json
from company_wiki.source_catalog.source_reader import SourceVersionReader
if not getattr(SourceVersionReader._verified_version, '_reading_test_observer', False):
    # Both open_version and open_described_version delegate actual byte
    # verification here; observing just one public entry point misses the other.
    _reading_original_open = SourceVersionReader._verified_version
    def _reading_counted_open(self, ref, *args, **kwargs):
        with (Path(__file__).parent.parent / 'source-open-count.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'document_id': ref.document_id, 'source_id': ref.source_id}) + '\\n')
        return _reading_original_open(self, ref, *args, **kwargs)
    _reading_counted_open._reading_test_observer = True
    SourceVersionReader._verified_version = _reading_counted_open
"""
    (bootstrap / "sitecustomize.py").write_text(bootstrap_source, encoding="utf-8")
    launcher = root / ("reading-hold.py" if hold_activation else "reading-run.py")
    source = """import os
from pathlib import Path
import sys
import runpy
bootstrap = str(Path(__file__).parent / 'reading-bootstrap')
sys.path.insert(0, bootstrap)
os.environ['PYTHONPATH'] = bootstrap + os.pathsep + os.environ['PYTHONPATH']
runpy.run_path(str(Path(bootstrap) / 'sitecustomize.py'))
from narrative_batch_configured import main
"""
    if hold_activation:
        source += """from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore
from company_wiki.source_catalog.lock import CatalogOperationLockedError
def hold(*args, **kwargs):
    print('reading_fixture_activation_held=1', file=sys.stderr)
    raise CatalogOperationLockedError('independent activation boundary fixture')
NarrativeArtifactStore.activate = hold
"""
    source += "if __name__ == '__main__':\n    raise SystemExit(main())\n"
    launcher.write_text(source, encoding="utf-8")
    return launcher


def _protected(root, config, llm):
    sentinel = root / "preexisting-test-sentinel.txt"
    sentinel.write_bytes(b"preserve exact original fixture contents")
    originals = [path for path in (root / "companies").rglob("*") if path.is_file()]
    return {path: path.read_bytes() for path in originals + [config, llm, sentinel]}


def _assert_protected(root, protected):
    assert all(path.is_file() and path.read_bytes() == value for path, value in protected.items())
    assert {path for path in (root / "companies").rglob("*") if path.is_file()} == {
        path for path in protected if (root / "companies") in path.parents
    }


def _assert_formal_generation(root, catalog, imported, run_id, reference, bundle, data):
    runs = NarrativeRunStore(root / "AUTO.sqlite")
    item_key = imported["source_ref"]["document_id"]
    final = runs.final_generations(run_id)[item_key]
    assert final["source_ref"] == imported["source_ref"] == bundle["source_ref"]
    assert final["source_metadata"] == bundle["source_metadata"]
    assert final["execution_versions"]["selector"] == bundle["versions"]["selector"] == "0.9.0"
    context = bundle["reading_context"]
    assert context["reading_policies"], "formal bundle lost actual reading policies"
    part = final["selection_generation"]
    assert part["schema_version"] == "narrative-selection-generation/1"
    assert part["reading_policy_version"] == context["reading_policy_version"]
    assert part["evidence_sha256"] == canonical_json_hash(bundle["evidence_spans"])
    # The whole select result also contains select-only parser/review/dependency
    # fields. Its exact audit hash is tested at Store commit; a public bundle
    # can truthfully recompute its shared material rather than invent those fields.
    require_sha256(part["select_result_sha256"], field_name="select_result_sha256")
    assert part["material_sha256"] == reading_material_sha256(NarrativeBundle.from_dict(bundle))
    row = catalog.reader.fetchone(
        "SELECT status,metadata_json FROM narrative_artifact_versions WHERE artifact_version_id=?",
        (reference["artifact_version_id"],),
    )
    assert row["status"] == "visible"
    metadata = json.loads(row["metadata_json"])
    assert metadata["generation_manifest"] == final, "publication retained an obsolete base generation"
    assert metadata["generation_sha256"] == canonical_json_hash(final)
    strategy = data["reading_strategy"]
    assert final["reading_model_projection"] == strategy["schema_version"] == "reading-model-input/5"
    assert data["schema_version"] == "narrative-model-request/6"
    assert final["execution_versions"]["prompt"] == resolve_model_boundary("reading-model-input/5").prompt_version
    assert final["reading_model_boundary"]["prompt_version"] == final["execution_versions"]["prompt"]
    assert final["summary_validation"]["language_observer"]["py3langid"]["model"]["status"] == "available"
    assert context["schema_version"] == "du-production-reading/2"
    # Public context is the full source audit view, bound by material_sha256
    # above; the model retains every actual semantic instruction independently.
    assert all("profile_version" in row and "policy_components" in row
               for row in context["reading_policies"])
    for policy in context["reading_policies"]:
        assert any(all(row.get(key) == policy.get(key) for key in (
            "family", "summary_focus", "reading_questions", "context_requirements", "negative_hints",
        )) for row in strategy["reading_policies"])
    for facet in context["business_facets"]:
        assert any(all(row.get(key) == facet.get(key) for key in (
            "id", "summary_focus", "business_questions", "required_context", "absence_rules",
            "confusion_checks", "applicable_mechanisms",
        )) for row in strategy["business_facets"])
    assert strategy["constraints"] == context["constraints"]
    assert all("selection_basis" not in row for row in strategy["business_facets"])
    assert all("family_policy" not in row for row in strategy["reading_policies"])
    material = data['material']
    rows = material['shared_fragments'] + [part for task in material['tasks']
                                         for part in task['parts'] if 'text' in part]
    rows.sort(key=lambda row: int(row['source_key'][1:]))
    aliases = [row['source_key'] for row in rows]
    assert len(aliases) == len(set(aliases)) == len(bundle["evidence_spans"])
    assert [row['text'] for row in rows] == [span["raw_text"] for span in bundle["evidence_spans"]]
    assert "evidence_groups" not in data and "evidence_group_columns" not in data
    units = {task['key']: [part.get('shared_ref', part.get('source_key')) for part in task['parts']]
             for task in material['tasks']}
    assert len(units) == len(material['tasks'])
    assert all(members and len(members) == len(set(members)) and set(members) <= set(aliases)
               for members in units.values())
    assert set().union(*(set(members) for members in units.values())) == set(aliases)
    alias_by_span = {span["span_id"]: alias for span, alias in zip(bundle["evidence_spans"], aliases, strict=True)}
    native_groups = {tuple(alias_by_span[sid] for sid in group["evidence_ids"])
                     for group in context["groups"]}
    assert native_groups <= {tuple(members) for members in units.values()}
    assert 'groups' not in strategy  # Native scopes are carried once by material.tasks.
    by_span = {span['span_id']: span['raw_text'] for span in bundle['evidence_spans']}
    for claim in bundle['summary']['draft']['claims']:
        assert claim['text'] == '\n'.join(by_span[sid] for sid in claim['evidence_ids'])
        assert claim['modality'] in {'question', 'uncertain'}
    assert "raw_text" not in json.dumps(data["reading_strategy"]), "strategy duplicated original quote bodies"
    assert "wrong_assertion" not in json.dumps(data["reading_strategy"])
    run = runs.get_run(run_id)
    assert len(run.job_ids) == 3
    assert all(runs.final_generation_for_job(job_id) == final for job_id in run.job_ids)
    return final


@pytest.mark.parametrize("mime", ["text/html", "application/pdf", "text/plain"])
def test_configured_shared_reading_reaches_summary_public_transport_and_same_run_restart(
    loopback_model_server, monkeypatch, mime,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", reuse.official.batch_fixtures.KEY)
    with reuse.setup_source(loopback_model_server.endpoint, mime) as (
        root, catalog, config, llm, imported, kind,
    ):
        protected = _protected(root, config, llm)
        try:
            launcher = _launcher(root)
            request = reuse.request_path(root, imported, loopback_model_server.endpoint, "reading-a", selector_version="0.9.0")
            process, first = reuse.invoke(root, config, request, llm, "reading-a", launcher=launcher)
            assert process.returncode == 0 and first["status"] == "completed", first
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            reference, bundle, receipt = reuse.public_read(root, config, imported, kind)
            assert receipt["replay_status"] == "verified"
            final = _assert_formal_generation(
                root, catalog, imported, "reading-a", reference, bundle, loopback_model_server.requests[0][0],
            )
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            old_usage = tuple(asdict(record) for record in runs.reservations_for_run("reading-a"))
            assert len(old_usage) == 1 and old_usage[0]["usage_status"] == "known"
            process, resumed = reuse.invoke(root, config, request, llm, "reading-a", launcher=launcher)
            assert process.returncode == 0 and resumed["status"] == "completed", resumed
            assert resumed["documents"] == first["documents"] and resumed["budget"] == first["budget"]
            assert len(loopback_model_server.requests) == 1
            assert tuple(asdict(record) for record in runs.reservations_for_run("reading-a")) == old_usage
            assert runs.final_generations("reading-a")[imported["source_ref"]["document_id"]] == final
            assert reuse.public_read(root, config, imported, kind)[0] == reference
            next_request = reuse.request_path(root, imported, loopback_model_server.endpoint, "reading-b", selector_version="0.9.0")
            process, next_result = reuse.invoke(root, config, next_request, llm, "reading-b", launcher=launcher)
            assert process.returncode == 0 and next_result["status"] == "completed", next_result
            dependencies = final.get("reading_dependencies")
            assert dependencies and dependencies["status"] == "complete", dependencies
            if len(loopback_model_server.requests) != 1:
                from company_wiki.document_understanding.decision_inventory import current_decision_trace
                from company_wiki.document_understanding.decision_dependencies import compare_decision_dependencies
                next_final = runs.final_generations("reading-b")[imported["source_ref"]["document_id"]]
                diagnostic = {
                    "changed_generation_fields": [key for key in final if final[key] != next_final.get(key)],
                    "dependency_comparison": compare_decision_dependencies(
                        final["reading_dependencies"], current_decision_trace(final["reading_dependencies"])),
                }
                pytest.fail("a new run did not reuse its exact causal material: " + json.dumps(diagnostic))
            assert next_result["budget"]["tokens"] == 0
            assert not runs.reservations_for_run("reading-b")
        finally:
            _assert_protected(root, protected)
    assert not root.exists(), "owned test lake was not removed"


def test_paid_shared_reading_owner_resumes_held_activation_without_second_model_post(
    loopback_model_server, monkeypatch,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", reuse.official.batch_fixtures.KEY)
    with reuse.setup_source(loopback_model_server.endpoint) as (
        root, catalog, config, llm, imported, kind,
    ):
        protected = _protected(root, config, llm)
        try:
            request = reuse.request_path(root, imported, loopback_model_server.endpoint, "reading-outbox", selector_version="0.9.0")
            process, held = reuse.invoke(root, config, request, llm, "reading-outbox",
                                        launcher=_launcher(root, hold_activation=True))
            assert process.returncode == 2 and held["status"] == "partial", held
            assert "reading_fixture_activation_held=1" in process.stderr
            assert held["documents"][0]["status"] == "activation_pending"
            assert len(loopback_model_server.requests) == 1
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            final_before = runs.final_generations("reading-outbox")
            usage = runs.reservations_for_run("reading-outbox")
            assert len(usage) == 1 and usage[0].usage_status == "known"
            assert usage[0].output_bytes is None
            row = catalog.reader.fetchone("SELECT status FROM narrative_artifact_versions")
            assert row["status"] == "prepared"
            process, completed = reuse.invoke(root, config, request, llm, "reading-outbox", launcher=_launcher(root))
            assert process.returncode == 0 and completed["status"] == "completed", completed
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            assert runs.final_generations("reading-outbox") == final_before
            after = runs.reservations_for_run("reading-outbox")
            assert len(after) == 1 and after[0].charged_tokens == usage[0].charged_tokens
            assert after[0].charged_micro_usd == usage[0].charged_micro_usd
            reference, bundle, _ = reuse.public_read(root, config, imported, kind)
            _assert_formal_generation(root, catalog, imported, "reading-outbox", reference, bundle,
                                      loopback_model_server.requests[0][0])
            assert after[0].output_bytes == reference["byte_size"]
        finally:
            _assert_protected(root, protected)
    assert not root.exists(), "owned activation test lake was not removed"


def test_completed_raw_resume_freshly_checks_original_once_and_refuses_changed_bytes(
    loopback_model_server, monkeypatch,
):
    """Removing coordinator preflight must retain one owner byte/replay check."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", reuse.official.batch_fixtures.KEY)
    with reuse.setup_source(loopback_model_server.endpoint, "text/plain") as (
        root, catalog, config, llm, imported, kind,
    ):
        protected = _protected(root, config, llm)
        raw = next((root / "companies").rglob("*.txt"))
        original = raw.read_bytes()
        try:
            launcher = _launcher(root, count_source_opens=True)
            request = reuse.request_path(root, imported, loopback_model_server.endpoint, "reading-byte-owner", selector_version="0.9.0")
            process, first = reuse.invoke(root, config, request, llm, "reading-byte-owner", launcher=launcher)
            assert process.returncode == 0 and first["status"] == "completed", first
            assert len(loopback_model_server.requests) == 1
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            usage = tuple(asdict(record) for record in runs.reservations_for_run("reading-byte-owner"))
            counter = root / "source-open-count.jsonl"
            before_reads = len(counter.read_text(encoding="utf-8").splitlines())
            process, resumed = reuse.invoke(root, config, request, llm, "reading-byte-owner", launcher=launcher)
            assert process.returncode == 0 and resumed["status"] == "completed", resumed
            assert resumed["documents"] == first["documents"]
            assert len(counter.read_text(encoding="utf-8").splitlines()) - before_reads == 1, (
                "completed-history operation must have one fresh original byte and locator owner"
            )
            raw.write_bytes(b"X" + original[1:])
            before_reads = len(counter.read_text(encoding="utf-8").splitlines())
            process, damaged = reuse.invoke(root, config, request, llm, "reading-byte-owner", launcher=launcher)
            assert process.returncode != 0 and damaged["status"] == "failed", damaged
            assert len(counter.read_text(encoding="utf-8").splitlines()) - before_reads == 1
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            assert tuple(asdict(record) for record in runs.reservations_for_run("reading-byte-owner")) == usage
        finally:
            raw.write_bytes(original)
            _assert_protected(root, protected)
    assert not root.exists()


def test_real_legacy_v5_auto_run_resumes_through_additive_upgrade_without_new_post(
    loopback_model_server, monkeypatch,
):
    """A real old run reaches the coordinator before new Store construction."""
    from company_wiki.automation import migrations
    monkeypatch.setenv("DEEPSEEK_API_KEY", reuse.official.batch_fixtures.KEY)
    with reuse.setup_source(loopback_model_server.endpoint, "text/plain") as (
        root, catalog, config, llm, imported, kind,
    ):
        protected = _protected(root, config, llm)
        try:
            request = reuse.request_path(root, imported, loopback_model_server.endpoint, "reading-legacy-v5",
                                         selector_version="0.8.0")
            process, original = reuse.invoke(root, config, request, llm, "reading-legacy-v5")
            assert process.returncode == 0 and original["status"] == "completed", original
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            db = root / "AUTO.sqlite"
            runs = NarrativeRunStore(db)
            old_run = asdict(runs.get_run("reading-legacy-v5"))
            old_usage = tuple(asdict(record) for record in runs.reservations_for_run("reading-legacy-v5"))
            old_reference, old_bundle, _ = reuse.public_read(root, config, imported, kind)
            assert old_bundle["versions"]["selector"] == "0.8.0"
            connection = sqlite3.connect(db)
            try:
                assert connection.execute("SELECT 1 FROM narrative_run_jobs WHERE final_generation_json IS NOT NULL LIMIT 1").fetchone() is None
                # Construct a truthful historical v5 shape from its frozen DDL.
                # New additive nullable columns must not remain under an old
                # PRAGMA label, and no nonempty future field may be discarded.
                expected = migrations._expected_structure(5)
                for table, definition in expected.items():
                    names = {column[1] for column in definition['columns']}
                    actual = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
                    for name in actual:
                        if name not in names:
                            assert connection.execute(
                                f'SELECT 1 FROM "{table}" WHERE "{name}" IS NOT NULL LIMIT 1').fetchone() is None
                            connection.execute(f'ALTER TABLE "{table}" DROP COLUMN "{name}"')
                connection.execute("PRAGMA user_version=5")
                connection.commit()
            finally:
                connection.close()
            assert migrations.inspect_schema(db).user_version == 5
            process, resumed = reuse.invoke(root, config, request, llm, "reading-legacy-v5")
            assert process.returncode == 0 and resumed["status"] == "completed", resumed
            assert resumed["documents"] == original["documents"] and resumed["budget"] == original["budget"]
            assert migrations.inspect_schema(db).user_version == migrations.SCHEMA_VERSION
            runs = NarrativeRunStore(db)
            assert asdict(runs.get_run("reading-legacy-v5")) == old_run
            assert tuple(asdict(record) for record in runs.reservations_for_run("reading-legacy-v5")) == old_usage
            current_reference, current_bundle, _ = reuse.public_read(root, config, imported, kind)
            assert current_reference == old_reference and current_bundle == old_bundle
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
        finally:
            _assert_protected(root, protected)
    assert not root.exists()
