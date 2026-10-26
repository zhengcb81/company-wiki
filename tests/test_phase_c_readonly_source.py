"""Phase C mounts actual registered roots; no raw copy or production DB writes."""

import hashlib
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from integration import test_narrative_generation_reuse as reuse  # noqa: E402
from company_wiki.source_catalog.source_location import resolve_source_location  # noqa: E402
from company_wiki.source_catalog.source_reader import SourceVersionReader  # noqa: E402
from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.service import SourceCatalog  # noqa: E402


def _fingerprint(path):
    stat = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), stat.st_size, stat.st_mtime_ns


def _fixture_source(catalog, imported):
    ref = imported["source_ref"]
    locations = catalog.reader.exact_source_locations(
        ref["document_id"], ref["source_id"]
    )
    row = locations[0]
    spec = next(r for r in catalog.config.roots if r.root_id == row["root_id"])
    original = resolve_source_location(spec, row["relative_path"])
    from company_wiki.source_catalog.source_reader import SourceRef

    manifest = SourceVersionReader(catalog).describe_version(SourceRef(**ref))
    descriptor = {**manifest, "entity": "Acme"}
    return original, descriptor


def test_exact_source_content_read_is_separate_from_historical_filing_qualification(tmp_path):
    from company_wiki.source_catalog.source_reader import SourceRef
    from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source, ReadonlySourceGap

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (root, catalog, config, _, imported, _kind):
        original, descriptor = _fixture_source(catalog, imported)
        protected = {p: _fingerprint(p) for p in [original, config, catalog.config.database_path]}
        descriptor["published_date"] = None
        facts = {"content_sha256": imported["source_ref"]["content_sha256"],
                 "facts": {"published_date": None},
                 "evidence": {"published_date": {"value": None, "locator": "fixture/source-date-unproved"}}}
        common = dict(source_config=config, original=original,
                      expected_sha256=imported["source_ref"]["content_sha256"],
                      descriptor=descriptor, as_of_date="2026-10-17", source_facts=facts)
        content = tmp_path / "content"
        result = prepare_registered_source(owned_root=content, expected_ref=SourceRef(**imported["source_ref"]), **common)
        assert result["source_ref"] == imported["source_ref"]
        assert result["manifest"]["published_date"] is None
        assert result["selection"] == {"mode": "exact_source_version", "filing_identity_period_asof_qualification": "NOT_EVALUATED"}
        assert result["raw_copies"] == 0
        # Same bytes/date cannot silently qualify for an historical filing query.
        with pytest.raises(ReadonlySourceGap, match="registered_source_not_found"):
            prepare_registered_source(owned_root=tmp_path / "filing", **common)
        assert all(_fingerprint(p) == fp for p, fp in protected.items())


def test_explicit_version_read_cannot_substitute_another_document(tmp_path):
    from dataclasses import replace
    from company_wiki.source_catalog.source_reader import SourceRef
    from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source, ReadonlySourceGap

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (_root, catalog, config, _, imported, _kind):
        original, descriptor = _fixture_source(catalog, imported)
        wrong = replace(SourceRef(**imported["source_ref"]), document_id="urn:company-wiki:document:sha256:" + "b" * 64)
        with pytest.raises(ReadonlySourceGap):
            prepare_registered_source(source_config=config, owned_root=tmp_path / "owned",
                                      original=original, expected_sha256=imported["source_ref"]["content_sha256"],
                                      descriptor=descriptor, as_of_date="2026-10-17", expected_ref=wrong)


def test_registered_source_mounts_same_bytes_and_only_explicit_group(
    tmp_path, monkeypatch
):
    from tools.document_understanding_benchmark.phase_c_readonly_source import (
        prepare_registered_source,
    )

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (
        root,
        catalog,
        config,
        _,
        imported,
        _kind,
    ):
        original, descriptor = _fixture_source(catalog, imported)
        sibling = original.parent / "unrelated.txt"
        sibling.write_text("do not register this unrelated original", encoding="utf-8")
        protected = {
            p: _fingerprint(p) for p in [original, config, catalog.config.database_path]
        }
        root_files = {
            str(p.relative_to(root)): _fingerprint(p)
            for p in root.rglob("*")
            if p.is_file()
        }
        owned = tmp_path / "owned"
        owned.mkdir()
        with monkeypatch.context() as guard:

            def forbidden_copy(*_args, **_kwargs):
                raise AssertionError("registered mode cannot copy raw originals")

            guard.setattr("shutil.copyfile", forbidden_copy)
            guard.setattr("shutil.copy2", forbidden_copy)
            result = prepare_registered_source(
                source_config=config,
                owned_root=owned,
                original=original,
                expected_sha256=imported["source_ref"]["content_sha256"],
                descriptor=descriptor,
                as_of_date="2026-10-17",
            )
        assert result["source_ref"] == imported["source_ref"]
        assert result["raw_copies"] == 0
        assert result["manifest"]["security_id"] == "ACME"
        assert result["verified_sha256"] == imported["source_ref"]["content_sha256"]
        mounted = load_catalog_config(
            Path(result["catalog_config"]), project_root=owned
        )
        assert mounted.catalog_dir == owned / "catalog"
        assert mounted.roots == load_catalog_config(config, project_root=root).roots
        temp_catalog = SourceCatalog(mounted)
        try:
            assert temp_catalog.reader.status()["documents"] == 1
        finally:
            temp_catalog.close()
        assert not (owned / "companies").exists()
        assert all(_fingerprint(p) == fp for p, fp in protected.items())
        assert {
            str(p.relative_to(root)): _fingerprint(p)
            for p in root.rglob("*")
            if p.is_file()
        } == root_files


def test_missing_metadata_is_gap_without_copy_or_fabrication(tmp_path):
    from tools.document_understanding_benchmark.phase_c_readonly_source import (
        prepare_registered_source,
        ReadonlySourceGap,
    )

    source = tmp_path / "source"
    raw = source / "companies" / "Acme" / "update.txt"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"Company business update, no verified period or issuer metadata.")
    config = source / "config" / "source_catalog.yaml"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "catalog_dir": str(source / "production-db"),
                "roots": [
                    {
                        "root_id": "raw",
                        "path": str(source / "companies"),
                        "kind": "company_raw",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    owned = tmp_path / "owned"
    owned.mkdir()
    before = _fingerprint(raw)
    with pytest.raises(ReadonlySourceGap) as exc:
        prepare_registered_source(
            source_config=config,
            owned_root=owned,
            original=raw,
            expected_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
            descriptor={
                "entity": "Acme",
                "document_kind": "investor_relations",
                "market": "US",
                "security_id": "ACME",
                "fiscal_year": 2026,
            },
            as_of_date="2026-10-17",
        )
    assert exc.value.reason == "registered_source_not_found"
    assert not (source / "production-db").exists()
    assert _fingerprint(raw) == before
    assert not (owned / "companies").exists()


def test_sha_mismatch_and_outside_configured_root_are_not_imported(tmp_path):
    from tools.document_understanding_benchmark.phase_c_readonly_source import (
        prepare_registered_source,
        ReadonlySourceGap,
    )

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (
        root,
        catalog,
        config,
        _,
        imported,
        _,
    ):
        original, descriptor = _fixture_source(catalog, imported)
        owned = tmp_path / "owned"
        owned.mkdir()
        with pytest.raises(ReadonlySourceGap, match="registered_source_sha_mismatch"):
            prepare_registered_source(
                source_config=config,
                owned_root=owned,
                original=original,
                expected_sha256="0" * 64,
                descriptor=descriptor,
                as_of_date="2026-10-17",
            )
        outside = tmp_path / "outside.txt"
        outside.write_bytes(original.read_bytes())
        with pytest.raises(
            ReadonlySourceGap, match="registered_source_outside_configured_roots"
        ):
            prepare_registered_source(
                source_config=config,
                owned_root=owned,
                original=outside,
                expected_sha256=imported["source_ref"]["content_sha256"],
                descriptor=descriptor,
                as_of_date="2026-10-17",
            )


def test_selector_versions_default_pair_and_single_09_are_explicit():
    from tools.document_understanding_benchmark.phase_c_runner import selector_versions

    assert selector_versions(None) == ("0.9.0", "0.8.0")
    assert selector_versions("0.9.0") == ("0.9.0",)
    assert selector_versions("0.9.0,0.8.0") == ("0.9.0", "0.8.0")
    for bad in ("", "0.9", "0.9.0,0.9.0", "0.8.0,0.9.0", "1.0.0"):
        with pytest.raises(ValueError):
            selector_versions(bad)


def test_readonly_runner_gap_is_not_run_and_never_calls_model(tmp_path, monkeypatch):
    from tools.document_understanding_benchmark import phase_c_runner as runner

    source = tmp_path / "source"
    raw = source / "companies" / "Acme" / "update.txt"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"Business material without public issuer or period metadata.")
    config = source / "config/source_catalog.yaml"
    config.parent.mkdir()
    config.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "catalog_dir": str(source / "production-db"),
                "roots": [
                    {
                        "root_id": "raw",
                        "path": str(source / "companies"),
                        "kind": "company_raw",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    gold = tmp_path / "gold.json"
    gold.write_text('{"facts": []}', encoding="utf-8")
    sample = {
        "sample_id": "cn-h1",
        "original": str(raw),
        "fingerprint": runner.fingerprint(raw),
        "gold": str(gold),
        "mime_type": "text/plain",
        "source_metadata_observation": {
            "title": "Acme business update",
            "document_kind": "investor_relations",
            "market": "US",
            "security_id": "ACME",
            "fiscal_year": 2026,
        },
    }
    meta = runner.loopback_preparation()
    provider = meta["providers"][0]
    output = tmp_path / "receipts"
    output.mkdir()
    calls = []

    def forbidden_cli(*args, **kwargs):
        calls.append(args)
        raise AssertionError("no public import or model command after metadata gap")

    monkeypatch.setattr(runner, "_cli", forbidden_cli)
    before = {p: runner.fingerprint(p) for p in (raw, config, gold)}
    actual = runner.run_pair(
        sample,
        provider,
        meta,
        mode="live",
        output=output,
        source_mode="registered_readonly",
        source_catalog_config=config,
        selected_versions="0.9.0",
    )
    assert actual["status"] == "NOT_RUN", actual
    assert actual["source_gap"]["reason"] == "registered_source_not_found"
    assert actual["model_post_attempts"] == 0 and calls == []
    assert actual["temporary_lake_removed"] and actual["protected_unchanged"]
    assert actual["comparison_scope"] == "single_selector_no_paired_improvement_claim"
    assert all(runner.fingerprint(p) == fp for p, fp in before.items())
    assert not (source / "production-db").exists()


def test_mother_total_keeps_baseline_unknown_and_deduplicates_native_attempts(tmp_path):
    from tools.document_understanding_benchmark.phase_c_runner import mother_totals

    meta = tmp_path / "metadata.json"
    ledger = tmp_path / "usage.jsonl"
    meta.write_text(
        json.dumps(
            {
                "mother_budget": {
                    "prior_charged_tokens": 413778,
                    "prior_charged_micro_usd": 334463,
                    "retained_fx_hold_micro_usd": 2764,
                    "old_unknown_hold_count_already_in_baseline": 7,
                    "token_limit": 2000000,
                    "micro_usd_limit": 20000000,
                }
            }
        ),
        encoding="utf-8",
    )
    row = {
        "kind": "native_model_charge",
        "mode": "live",
        "database": "old-temp/AUTO.sqlite",
        "attempt_id": "one",
        "usage_status": "unknown",
        "charged_tokens": 200000,
        "charged_micro_usd": 1000000,
    }
    settled = {
        **row,
        "usage_status": "known",
        "charged_tokens": 18103,
        "charged_micro_usd": 3345,
    }
    ledger.write_text(
        json.dumps(row) + "\n" + json.dumps(settled) + "\n", encoding="utf-8"
    )
    actual = mother_totals(meta, ledger)
    assert actual["charged_tokens"] == 431881
    assert actual["charged_micro_usd"] == 340572
    assert actual["prior_unknown7_retained"] == 7
    assert actual["new_unknown_count"] == 0


def test_single_selector_keeps_real_loopback_resume_and_cache_proofs(tmp_path):
    from tools.document_understanding_benchmark import phase_c_runner as runner

    metadata = runner.loopback_preparation()
    provider = metadata["providers"][0]
    output = tmp_path / "one-selector"
    output.mkdir()
    with runner.Loopback() as server:
        result = runner.run_pair(
            {"sample_id": "loopback-fixture"},
            provider,
            metadata,
            mode="loopback",
            output=output,
            fixture_endpoint=server.endpoint,
            reading_model_projection="reading-model-input/4",
            selected_versions="0.9.0",
        )
        assert result["status"] == "PASS", result
        assert len(server.requests) == result["model_post_attempts"] == 1
    assert len(result["states"]) == 1
    state = result["states"][0]
    assert state["version"] == "0.9.0"
    assert state["same_run_zero_POST"] and state["cross_run_zero_POST"]
    assert state["current_exact_ref_single_selector"]["status"] == "PASS"
    assert "historical_exact_ref_after_legacy_LATEST" not in state
    assert result["comparison_scope"] == "single_selector_no_paired_improvement_claim"
    assert (
        result["temporary_lake_removed"]
        and result["sentinel_unchanged"]
        and result["protected_unchanged"]
    )


def test_registered_runner_passes_real_ref_to_valid_batch_without_starting_model(
    tmp_path, monkeypatch
):
    from tools.document_understanding_benchmark import phase_c_runner as runner

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (
        root,
        catalog,
        config,
        _,
        imported,
        _,
    ):
        original, descriptor = _fixture_source(catalog, imported)
        gold = tmp_path / "gold.json"
        gold.write_text('{"facts": []}', encoding="utf-8")
        sample = {
            "sample_id": "registered-synthetic",
            "original": str(original),
            "fingerprint": runner.fingerprint(original),
            "gold": str(gold),
            "mime_type": "text/html",
            "source_metadata_observation": descriptor,
        }
        meta = runner.loopback_preparation()
        provider = meta["providers"][0]
        # This live-shaped request is never sent. Use a valid HTTPS fixture
        # endpoint so the production request validator reaches the held CLI.
        provider["options"]["endpoint"] = (
            "https://model.fixture.invalid/chat/completions"
        )
        calls = []

        def stop_before_model(owned, output, label, command, env, *args, **kwargs):
            calls.append(command)
            assert "phase_c_launcher.py" in command[4]
            request = json.loads(
                Path(command[command.index("--request") + 1]).read_text(
                    encoding="utf-8"
                )
            )
            assert request["sources"] == [imported["source_ref"]]
            assert request["selector_version"] == "0.9.0"
            assert request["reading_model_projection"] == "reading-model-input/4"
            assert (
                request["model"]["max_output_tokens"]
                == provider["options"]["max_output_tokens"]
            )
            mounted = load_catalog_config(
                Path(command[command.index("--catalog-config") + 1]), project_root=owned
            )
            assert mounted.roots == load_catalog_config(config, project_root=root).roots
            assert not (owned / "companies").exists()
            raise RuntimeError("ROOT_OFFLINE_MODEL_NOT_STARTED")

        monkeypatch.setattr(runner, "_cli", stop_before_model)
        output = tmp_path / "registered-receipt"
        output.mkdir()
        before = {
            p: runner.fingerprint(p)
            for p in (original, config, catalog.config.database_path)
        }
        actual = runner.run_pair(
            sample,
            provider,
            meta,
            mode="live",
            output=output,
            source_mode="registered_readonly",
            source_catalog_config=config,
            selected_versions="0.9.0",
            reading_model_projection="reading-model-input/4",
        )
        if len(calls) != 1 or "ROOT_OFFLINE_MODEL_NOT_STARTED" not in actual.get(
            "error", ""
        ):
            pytest.fail(json.dumps(actual, ensure_ascii=False, indent=2))
        assert (
            actual["status"] == "FAIL"
        )  # no fabricated complete summary when model intentionally stopped
        assert actual["source_registration"]["raw_copies"] == 0
        assert actual["source_ref"] == imported["source_ref"]
        assert actual["model_post_attempts"] == 0
        assert actual["protected_unchanged"] and actual["temporary_lake_removed"]
        assert all(runner.fingerprint(p) == fp for p, fp in before.items())


def test_invalid_registered_configuration_fails_before_allocating_temp(
    tmp_path, monkeypatch
):
    from tools.document_understanding_benchmark import phase_c_runner as runner

    allocated = []

    def forbidden_temp(*args, **kwargs):
        allocated.append(True)
        raise AssertionError("invalid config must fail before owned IO")

    monkeypatch.setattr(runner.tempfile, "mkdtemp", forbidden_temp)
    with pytest.raises(FileNotFoundError):
        runner.run_pair(
            {},
            {},
            {},
            mode="live",
            output=tmp_path,
            source_mode="registered_readonly",
            source_catalog_config=tmp_path / "missing.yaml",
        )
    assert allocated == []


@pytest.mark.parametrize(
    "declared,expected_family",
    [("en-US", "en"), ("en", "en"), (None, "en"), ("zh-CN", "zh")],
)
def test_registered_source_defers_language_and_display_facts_to_source_owner(
    tmp_path, declared, expected_family
):
    from types import SimpleNamespace
    from company_wiki.automation.narrative_batch import _current_sources
    from company_wiki.automation.narrative_batch_request import NarrativeBatchItem
    from tools.document_understanding_benchmark.phase_c_readonly_source import (
        prepare_registered_source,
    )

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (
        _root,
        catalog,
        config,
        _,
        imported,
        _kind,
    ):
        original, descriptor = _fixture_source(catalog, imported)
        # This owned synthetic sidecar models existing acquisition observations.
        # New official imports deliberately accept worker families only; existing
        # catalogs may contain locale tags or unknown language (the real CN/US cases).
        sidecar = original.with_name(original.name + ".source.json")
        acquisition = json.loads(sidecar.read_text(encoding="utf-8"))
        acquisition["language"] = declared
        acquisition["candidate"]["language"] = declared
        acquisition["request"]["language"] = declared
        sidecar.write_text(json.dumps(acquisition), encoding="utf-8")
        descriptor.update(
            language=expected_family,
            source_url="https://descriptor.example/different",
            published_date="2026-08-25",
        )
        before = {
            p: _fingerprint(p)
            for p in (original, sidecar, config, catalog.config.database_path)
        }
        result = prepare_registered_source(
            source_config=config,
            owned_root=tmp_path / "owned",
            original=original,
            expected_sha256=imported["source_ref"]["content_sha256"],
            descriptor=descriptor,
            as_of_date="2026-10-17",
        )
        assert result["manifest"]["language"] == declared
        assert result["manifest"]["published_date"] == "2026-08-26"
        assert result["descriptor_diagnostics"]["published_date"] == {
            "expected": "2026-08-25",
            "observed": "2026-08-26",
        }
        assert result["manifest"]["source_url"] != descriptor["source_url"]
        owned = SourceCatalog(load_catalog_config(Path(result["catalog_config"])))
        try:
            item = NarrativeBatchItem.from_dict(
                {"kind": "raw", "source_ref": result["source_ref"]}
            )
            payloads, _ = _current_sources(
                SimpleNamespace(work_items=[item]), SourceVersionReader(owned)
            )
            assert (
                payloads[0].to_dict()["source_metadata"]["language"] == expected_family
            )
        finally:
            owned.close()
        assert all(_fingerprint(p) == fingerprint for p, fingerprint in before.items())
        assert result["raw_copies"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"entity": "Different issuer"},
        {"market": "HK"},
        {"security_id": "OTHER"},
        {"fiscal_year": 2027},
        {"fiscal_period": "Q4"},
        {"document_kind": "annual_report"},
        {"_as_of_date": "2026-08-25"},
    ],
)
def test_registered_source_identity_and_period_still_belong_to_query(tmp_path, change):
    from tools.document_understanding_benchmark.phase_c_readonly_source import (
        prepare_registered_source,
        ReadonlySourceGap,
    )

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (
        _root,
        catalog,
        config,
        _,
        imported,
        _kind,
    ):
        original, descriptor = _fixture_source(catalog, imported)
        descriptor.update(
            {key: value for key, value in change.items() if not key.startswith("_")}
        )
        with pytest.raises(ReadonlySourceGap, match="registered_source_not_found"):
            prepare_registered_source(
                source_config=config,
                owned_root=tmp_path / "owned",
                original=original,
                expected_sha256=imported["source_ref"]["content_sha256"],
                descriptor=descriptor,
                as_of_date=change.get("_as_of_date", "2026-10-17"),
            )


def test_registered_source_facts_use_existing_public_owner_without_copy(tmp_path):
    from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source

    raw = tmp_path / "source/companies/WRONG_FOLDER/update.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text("Acme business update. Published 2026-09-30. New factory opened.", encoding="utf-8")
    config = tmp_path / "source/config.json"
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": str(tmp_path / "production-db"),
        "roots": [{"root_id": "raw", "path": str(tmp_path / "source/companies"), "kind": "company_raw"}]}), encoding="utf-8")
    sha = hashlib.sha256(raw.read_bytes()).hexdigest()
    facts = {"entity": "Acme", "market": "CN", "security_id": "300775",
        "document_kind": "investor_relations", "published_date": "2026-09-30", "fiscal_year": 2026}
    proof = {"content_sha256": sha, "facts": facts, "evidence": {
        key: {"value": value, "locator": "test:original-header", "content_sha256": sha}
        for key, value in facts.items()}}
    before = {p: _fingerprint(p) for p in (raw, config)}
    mounted = prepare_registered_source(source_config=config, owned_root=tmp_path / "owned",
        original=raw, expected_sha256=sha, descriptor=facts, as_of_date="2026-10-17", source_facts=proof)
    assert mounted["source_fact_registration"]["status"] == "recorded"
    assert mounted["manifest"]["display_name"] == "Acme"
    assert mounted["manifest"]["published_date"] == "2026-09-30"
    assert mounted["raw_copies"] == 0
    assert all(_fingerprint(p) == v for p, v in before.items())
    assert not (tmp_path / "production-db").exists()


def test_registered_source_fact_proof_is_bound_to_original_sha(tmp_path):
    from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source, ReadonlySourceGap

    with reuse.setup_source("http://127.0.0.1:1/chat/completions") as (root, catalog, config, _, imported, _):
        original, descriptor = _fixture_source(catalog, imported)
        before = _fingerprint(original)
        with pytest.raises(ReadonlySourceGap, match="registered_source_fact_sha_mismatch"):
            prepare_registered_source(source_config=config, owned_root=tmp_path / "owned",
                original=original, expected_sha256=imported["source_ref"]["content_sha256"],
                descriptor=descriptor, as_of_date="2026-10-17",
                source_facts={"content_sha256": "0" * 64, "facts": {"entity": "Acme"}, "evidence": {}})
        assert _fingerprint(original) == before
