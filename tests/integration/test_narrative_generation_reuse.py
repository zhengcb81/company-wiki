"""Configured finite generation reuse preserves public evidence and own usage."""

from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import pytest
from integration import test_official_source_flow as official
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.source_catalog.official_source_flow import (
    prepare_official_narrative_request,
)

loopback_model_server = official.loopback_model_server


@contextmanager
def setup_source(endpoint, mime="text/html"):
    if mime == "application/pdf":
        import fitz

        doc = fitz.open()
        doc.new_page().insert_text(
            (72, 72),
            "CEO: We launched a new product and expanded overseas capacity for customers.",
        )
        original = doc.tobytes()
        doc.close()
    elif mime == "text/plain":
        original = b"Full Conference Call Transcript\nCEO: We launched a new product and expanded overseas capacity for customers.\n"
    else:
        original = b"<html><p>We launched a new product and expanded overseas capacity for customers.</p></html>"
    with official.owned_lake() as (root, catalog):
        (root / "config").mkdir()
        config = root / "config/catalog.json"
        config.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "catalog_dir": "catalog",
                    "roots": [
                        {
                            "root_id": "company_raw",
                            "path": "companies",
                            "kind": "company_raw",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        kind = (
            "investor_relations" if mime == "text/html" else "investor_call_transcript"
        )
        imported = official._public_official_import(
            root, config, original, mime=mime, kind=kind, language="en"
        )
        llm = root / "llm.yaml"
        llm.write_text(
            "llm:\n  provider: deepseek\n  model: stub-model\n  base_url: "
            + endpoint.removesuffix("/chat/completions")
            + "\n  max_tokens: 8192\n  temperature: 0.7\n",
            encoding="utf-8",
        )
        yield root, catalog, config, llm, imported, kind


def request_path(root, imported, endpoint, run_id, **overrides):
    template = {
        "schema_version": "narrative-batch-request/1",
        "run_id": run_id,
        "profile": "P2",
        "max_seconds": 40,
        "max_tokens": 100000,
        "max_cost_usd": "1",
        "model": {
            "model_id": "stub-model",
            "endpoint": endpoint,
            "api_key_env": official.batch_fixtures.KEY_ENV,
            "max_output_tokens": 400,
            "timeout_seconds": 5,
            "allow_local_http": True,
        },
        "pricing": {
            "version": "fixture-price/1",
            "input_micro_usd_per_million_tokens": 1000000,
            "output_micro_usd_per_million_tokens": 2000000,
        },
        **overrides,
    }
    value = prepare_official_narrative_request(
        imported if isinstance(imported, list) else [imported], batch_template=template
    ).to_dict()
    path = root / (run_id + ".json")
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def public_read(root, config, imported, kind, *, exact=None):
    reference, _ = official._public_narrative(
        root,
        config,
        "reference",
        {
            "schema_version": "narrative-reference-request/1",
            "source_ref": imported["source_ref"],
        },
    )
    reference = exact or reference
    bundle, receipt = official._public_narrative(
        root,
        config,
        "read",
        {
            "schema_version": "narrative-read-request/1",
            "narrative_ref": reference,
            "as_of_date": "2026-10-09",
            "expected_source": {
                "canonical_entity_id": None,
                "market": "US",
                "security_id": "ACME",
                "document_kind": kind,
                "fiscal_year": None,
                "fiscal_period": None,
            },
        },
    )
    assert receipt["replay_status"] == "verified" and receipt["locator_count"] > 0
    assert (
        bundle["summary"]["translate"] is False
        and bundle["summary"]["draft"]["language"] == "en"
    )
    assert bundle["source_ref"] == imported["source_ref"] and all(
        span["locator"] for span in bundle["evidence_spans"]
    )
    return reference, bundle, receipt


@pytest.mark.parametrize("mime", ["text/html", "application/pdf", "text/plain"])
def test_different_configured_runs_default_to_one_generation_post_and_public_pin(
    loopback_model_server, monkeypatch, mime
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint, mime) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        # Each finite run has a dedicated work directory, and the same existing AUTO.
        first_path = request_path(
            root, imported, loopback_model_server.endpoint, "generation-a"
        )
        first_process, first = invoke(root, config, first_path, llm, "generation-a")
        assert first_process.returncode == 0 and first["status"] == "completed", first
        original_ref, original_bundle, _ = public_read(root, config, imported, kind)
        old_reservations = tuple(
            asdict(item)
            for item in NarrativeRunStore(root / "AUTO.sqlite").reservations_for_run(
                "generation-a"
            )
        )
        next_path = request_path(
            root, imported, loopback_model_server.endpoint, "generation-b"
        )
        next_process, second = invoke(root, config, next_path, llm, "generation-b")
        assert next_process.returncode == 0 and second["status"] == "completed", second
        assert len(loopback_model_server.requests) == 1, (
            "default cross-run generation repeated POST"
        )
        current_ref, current_bundle, _ = public_read(root, config, imported, kind)
        assert current_ref == original_ref and current_bundle == original_bundle
        assert second["budget"] == {
            "tokens": 0,
            "estimated_micro_usd": 0,
            "unknown_reservations": 0,
            "unsettled_reservations": 0,
        }
        assert not NarrativeRunStore(root / "AUTO.sqlite").reservations_for_run(
            "generation-b"
        )
        assert (
            tuple(
                asdict(item)
                for item in NarrativeRunStore(
                    root / "AUTO.sqlite"
                ).reservations_for_run("generation-a")
            )
            == old_reservations
        )
        assert (
            len(loopback_model_server.requests) == 1
            and not loopback_model_server.errors
        )


def invoke(root, config, request, llm, run_id, *, database=None, launcher=None):
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parents[2]
    process = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            str(launcher or repo / "scripts/narrative_batch_configured.py"),
            "--llm-config",
            str(llm),
            "--allow-local-model-http",
            "--project-root",
            str(root),
            "--catalog-config",
            str(config),
            "--automation-db",
            str(database or root / "AUTO.sqlite"),
            "--work-dir",
            str(root / ("work-" + run_id)),
            "--request",
            str(request),
        ],
        cwd=root,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(repo / "src"), str(repo / "scripts")]),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHON_DOTENV_DISABLED": "1",
        },
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert official.batch_fixtures.KEY not in process.stdout + process.stderr
    assert process.stdout.strip(), process.stderr
    return process, json.loads(process.stdout)


def exact_ref(imported, pin):
    return {
        "schema_version": "narrative-ref/1",
        "artifact_version_id": pin["artifact_version_id"],
        "artifact_sha256": pin["content_sha256"],
        "byte_size": pin["byte_size"],
        "source_ref": imported["source_ref"],
    }


def record_proof(name, server, result, read_receipt=None, *, extra=None):
    import os

    output = os.environ.get("NARRATIVE_REUSE_PROOF_FILE")
    if output:
        path = Path(output)
        values = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        values[name] = {
            "local_post_count": len(server.requests),
            "supplier_requests": 0,
            "batch_result": result,
            "read_receipt": read_receipt,
            "extra": extra,
        }
        path.write_text(
            json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def test_zero_new_quota_and_different_database_reuse_keep_origin_accounting(
    loopback_model_server, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        first = request_path(root, imported, loopback_model_server.endpoint, "quota-a")
        process, original = invoke(root, config, first, llm, "quota-a")
        assert process.returncode == 0, original
        origin = NarrativeRunStore(root / "AUTO.sqlite")
        reservations = origin.reservations_for_run("quota-a")
        gate = (
            __import__("company_wiki.automation.store", fromlist=["AutomationStore"])
            .AutomationStore(root / "AUTO.sqlite")
            .read_runtime_gate()
        )
        (root / "companies").rename(root / "relocated-companies")
        config_wire = json.loads(config.read_text(encoding="utf-8"))
        config_wire["roots"][0]["path"] = "relocated-companies"
        config.write_text(json.dumps(config_wire), encoding="utf-8")
        second = request_path(
            root,
            imported,
            loopback_model_server.endpoint,
            "quota-b",
            max_tokens=1,
            max_cost_usd="0",
            max_persistent_bytes=1024 * 1024,
            max_final_bytes=1,
            max_scratch_bytes=1,
        )
        launcher = root / "reuse-readonly-catalog.py"
        launcher.write_text(
            "from company_wiki.source_catalog.store import CatalogStore\nfrom narrative_batch_configured import main\ndef forbidden(*args, **kwargs):\n    raise AssertionError('reuse opened source catalog writer')\nif __name__ == '__main__':\n    CatalogStore.__init__ = forbidden\n    raise SystemExit(main())\n",
            encoding="utf-8",
        )
        process, reused = invoke(
            root,
            config,
            second,
            llm,
            "quota-b",
            database=root / "other.sqlite",
            launcher=launcher,
        )
        assert process.returncode == 0 and reused["status"] == "completed", reused
        assert (
            reused["documents"][0]["artifact_ref"]
            == original["documents"][0]["artifact_ref"]
        )
        assert (
            reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
        )
        run = NarrativeRunStore(root / "other.sqlite").get_run("quota-b")
        assert (
            run.job_ids == () and json.loads(run.binding_json)["reused_artifact_pins"]
        )
        assert origin.reservations_for_run("quota-a") == reservations
        assert (
            __import__("company_wiki.automation.store", fromlist=["AutomationStore"])
            .AutomationStore(root / "AUTO.sqlite")
            .read_runtime_gate()
            == gate
        )
        reference, _, receipt = public_read(root, config, imported, kind)
        assert reference == exact_ref(imported, reused["documents"][0]["artifact_ref"])
        record_proof("zero-quota-other-db", loopback_model_server, reused, receipt)
        assert len(loopback_model_server.requests) == 1


def test_refresh_success_exact_resume_and_changed_refresh_intent_conflict(
    loopback_model_server, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        path = request_path(root, imported, loopback_model_server.endpoint, "refresh-a")
        process, first = invoke(root, config, path, llm, "refresh-a")
        assert process.returncode == 0
        path = request_path(
            root, imported, loopback_model_server.endpoint, "refresh-b", refresh=True
        )
        process, refreshed = invoke(root, config, path, llm, "refresh-b")
        assert process.returncode == 0 and refreshed["status"] == "completed", refreshed
        assert len(loopback_model_server.requests) == 2
        assert (
            first["documents"][0]["artifact_ref"]["artifact_version_id"]
            != refreshed["documents"][0]["artifact_ref"]["artifact_version_id"]
        )
        process, resume = invoke(root, config, path, llm, "refresh-b")
        assert process.returncode == 0 and resume["documents"] == refreshed["documents"]
        assert (
            resume["budget"] == refreshed["budget"]
            and len(loopback_model_server.requests) == 2
        )
        request_path(root, imported, loopback_model_server.endpoint, "refresh-b")
        process, conflict = invoke(root, config, path, llm, "refresh-b")
        assert (
            process.returncode == 2 and conflict["error"] == "BATCH_REQUEST_CHANGED"
        ), conflict
        assert len(loopback_model_server.requests) == 2
        _, _, receipt = public_read(root, config, imported, kind)
        record_proof("refresh-success", loopback_model_server, refreshed, receipt)


def test_failed_refresh_preserves_visible_pin_and_known_charge_then_allows_new_refresh(
    loopback_model_server, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        path = request_path(root, imported, loopback_model_server.endpoint, "failure-a")
        process, first = invoke(root, config, path, llm, "failure-a")
        assert process.returncode == 0
        original_ref, bundle, _ = public_read(root, config, imported, kind)
        loopback_model_server.response_body = json.dumps(
            {
                "model": "stub-model",
                "choices": [],
                "usage": {"prompt_tokens": 73, "completion_tokens": 19},
            }
        ).encode()
        path = request_path(
            root, imported, loopback_model_server.endpoint, "failure-b", refresh=True
        )
        launcher = root / "hold-known-terminal-pointer.py"
        launcher.write_text(
            "import company_wiki.automation.narrative_batch as batch\nfrom narrative_batch_configured import main\nif __name__ == '__main__':\n    batch._generation_owner_finished = lambda *args: False\n    raise SystemExit(main())\n",
            encoding="utf-8",
        )
        process, failed = invoke(
            root, config, path, llm, "failure-b", launcher=launcher
        )
        assert process.returncode == 2 and failed["status"] == "failed", failed
        assert (
            failed["budget"]["tokens"] == 92
            and failed["budget"]["unknown_reservations"] == 0
        )
        reference, current, receipt = public_read(root, config, imported, kind)
        assert reference == original_ref and current == bundle
        assert len(loopback_model_server.requests) == 2
        assert list((root / "catalog/narrative-generations").glob("*.json"))
        record_proof(
            "refresh-failure-old-readable", loopback_model_server, failed, receipt
        )
        loopback_model_server.response_body = None
        path = request_path(
            root, imported, loopback_model_server.endpoint, "failure-c", refresh=True
        )
        process, completed = invoke(
            root, config, path, llm, "failure-c", database=root / "replacement.sqlite"
        )
        assert process.returncode == 0 and completed["status"] == "completed", completed
        assert len(loopback_model_server.requests) == 3
        retained = NarrativeRunStore(root / "AUTO.sqlite").reservations_for_run(
            "failure-b"
        )
        assert (
            len(retained) == 1
            and retained[0].usage_status == "known"
            and retained[0].charged_tokens == 92
        )


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_matching_damaged_object_refuses_without_new_post(
    loopback_model_server, monkeypatch, damage
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        path = request_path(root, imported, loopback_model_server.endpoint, "damaged-a")
        process, first = invoke(root, config, path, llm, "damaged-a")
        assert process.returncode == 0
        pin = first["documents"][0]["artifact_ref"]
        obj = (
            root
            / "catalog/objects/sha256"
            / pin["content_sha256"][:2]
            / (pin["content_sha256"] + ".json")
        )
        original = obj.read_bytes()
        try:
            if damage == "missing":
                obj.unlink()
            else:
                obj.write_bytes(b"X" + original[1:])
            path = request_path(
                root, imported, loopback_model_server.endpoint, "damaged-b"
            )
            process, failed = invoke(root, config, path, llm, "damaged-b")
            assert process.returncode == 2 and failed["status"] == "failed", failed
            assert (
                len(loopback_model_server.requests) == 1
                and failed["budget"]["tokens"] == 0
            )
        finally:
            obj.write_bytes(original)
        _, _, receipt = public_read(root, config, imported, kind)
        record_proof("object-" + damage, loopback_model_server, failed, receipt)


def test_older_compatible_generation_is_pinned_behind_newer_model_setting(
    loopback_model_server, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        path = request_path(root, imported, loopback_model_server.endpoint, "causal-a")
        process, first = invoke(root, config, path, llm, "causal-a")
        assert process.returncode == 0
        original_llm = llm.read_text(encoding="utf-8")
        llm.write_text(
            original_llm.replace("temperature: 0.7", "temperature: 0.9"),
            encoding="utf-8",
        )
        path = request_path(root, imported, loopback_model_server.endpoint, "causal-b")
        process, changed = invoke(root, config, path, llm, "causal-b")
        assert process.returncode == 0 and len(loopback_model_server.requests) == 2
        assert json.loads(loopback_model_server.requests[1][1])["temperature"] == 0.9
        llm.write_text(original_llm, encoding="utf-8")
        path = request_path(
            root,
            imported,
            loopback_model_server.endpoint,
            "causal-c",
            max_cost_usd="0",
            max_tokens=1,
        )
        process, reused = invoke(root, config, path, llm, "causal-c")
        assert process.returncode == 0 and len(loopback_model_server.requests) == 2, (
            reused
        )
        pin = reused["documents"][0]["artifact_ref"]
        assert (
            pin == first["documents"][0]["artifact_ref"]
            and pin != changed["documents"][0]["artifact_ref"]
        )
        _, _, receipt = public_read(
            root, config, imported, kind, exact=exact_ref(imported, pin)
        )
        record_proof(
            "older-compatible-generation", loopback_model_server, reused, receipt
        )


def test_mixed_batch_creates_jobs_and_charge_for_only_actual_miss(
    loopback_model_server, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        path = request_path(root, imported, loopback_model_server.endpoint, "mixed-a")
        process, first = invoke(root, config, path, llm, "mixed-a")
        assert process.returncode == 0
        other = official._public_official_import(
            root,
            config,
            b"Full Conference Call Transcript\nCEO: We expanded overseas production and launched a new product.\n",
            mime="text/plain",
            kind="investor_call_transcript",
            language="en",
        )
        path = request_path(
            root, [imported, other], loopback_model_server.endpoint, "mixed-b"
        )
        process, second = invoke(root, config, path, llm, "mixed-b")
        assert process.returncode == 0 and second["status"] == "completed", second
        assert (
            len(loopback_model_server.requests) == 2
            and second["budget"]["tokens"] == 92
        )
        runs = NarrativeRunStore(root / "AUTO.sqlite")
        run = runs.get_run("mixed-b")
        assert len(run.job_ids) == 3 and len(runs.reservations_for_run("mixed-b")) == 1
        assert (
            second["documents"][0]["artifact_ref"]
            == first["documents"][0]["artifact_ref"]
        )
        process, resume = invoke(root, config, path, llm, "mixed-b")
        assert process.returncode == 0 and resume["documents"] == second["documents"]
        assert len(loopback_model_server.requests) == 2
        public_read(root, config, other, "investor_call_transcript")
        record_proof("mixed-hit-miss", loopback_model_server, second)


def test_visible_origin_recovery_pointer_does_not_block_explicit_refresh(
    loopback_model_server, monkeypatch
):
    from company_wiki.automation.narrative_batch import (
        _thaw_generations,
        _generation_pointer,
        _write_generation_owner,
    )
    from company_wiki._file_mutex import os_file_mutex

    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        path = request_path(root, imported, loopback_model_server.endpoint, "visible-a")
        process, first = invoke(root, config, path, llm, "visible-a")
        assert process.returncode == 0
        run = NarrativeRunStore(root / "AUTO.sqlite").get_run("visible-a")
        manifest = _thaw_generations(json.loads(run.binding_json))[
            imported["source_ref"]["document_id"]
        ]
        pointer = _generation_pointer(catalog, manifest)
        # Replay the minimal recovery locator after the origin's real visible
        # publication; neither jobs nor receipts are changed or fabricated.
        with os_file_mutex(pointer.with_suffix(".lock")):
            _write_generation_owner(pointer, root / "AUTO.sqlite", "visible-a")
        path = request_path(
            root, imported, loopback_model_server.endpoint, "visible-b", refresh=True
        )
        process, refreshed = invoke(
            root, config, path, llm, "visible-b", database=root / "other.sqlite"
        )
        assert process.returncode == 0 and refreshed["status"] == "completed", refreshed
        assert len(loopback_model_server.requests) == 2 and not pointer.exists()
        _, _, receipt = public_read(root, config, imported, kind)
        record_proof(
            "visible-origin-refresh", loopback_model_server, refreshed, receipt
        )
