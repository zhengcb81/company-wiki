"""Local task files and inventory consume explicit resources, not display caps."""
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest
import yaml

from company_wiki.automation import narrative_batch_cli
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.source_catalog import cli, local_prepare_cli
from company_wiki.source_catalog.local_inventory import (
    LocalPrepareLimits, LocalReadBudget, observe_document,
    read_registered_sidecar, verify_registered_original,
)
from company_wiki.source_catalog.source_reader import SourceReadError
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.store import retire_document, restore_document
from unit.test_narrative_batch import _request
from unit import test_source_facts as source_fact_fixtures
from unit.test_source_facts import _apply, _evidence, _assertions

lake = source_fact_fixtures.lake


def _config(tmp_path, catalog):
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump({"schema_version": "1.0", "catalog_dir": str(catalog.config.catalog_dir),
        "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": str(tmp_path / "companies")}]}), encoding="utf-8")
    return path


def test_batch_cli_and_api_accept_same_complete_local_request(tmp_path, monkeypatch):
    wire = _request().to_dict()
    request = NarrativeBatchRequest.from_dict(wire)
    path = tmp_path / "request.json"
    path.write_bytes(json.dumps(wire).encode() + b" " * (270 * 1024))
    calls = []
    monkeypatch.setattr(narrative_batch_cli, "run_batch", lambda actual, **kwargs: calls.append(actual) or {"status": "completed"})
    assert narrative_batch_cli.main(["--project-root", str(tmp_path), "--catalog-config", str(tmp_path / "unused.yaml"),
        "--automation-db", str(tmp_path / "unused.db"), "--work-dir", str(tmp_path / "unused"), "--request", str(path)]) == 0
    assert calls == [request]


def test_source_fact_cli_and_api_accept_same_complete_evidence(lake, tmp_path):
    catalog, reader, ref, original = lake
    before = original.read_bytes()
    facts = {"security_id": "002643"}
    evidence = _evidence(facts)
    evidence["security_id"]["detail"] = "合成来源注记。" * 20000
    first = _apply(lake, facts, evidence)
    assertions = _assertions(catalog)
    path = tmp_path / "request.json"
    path.write_text(json.dumps({"source_ref": asdict(ref), "facts": facts, "evidence": evidence}, ensure_ascii=False), encoding="utf-8")
    assert path.stat().st_size > 128 * 1024
    assert cli.main(["--config", str(_config(tmp_path, catalog)), "source-facts", "--request", str(path)]) == 0
    assert _assertions(catalog) == assertions and first["status"] == "recorded"
    assert reader.open_version(ref).data == before == original.read_bytes()


def test_local_prepare_cli_uses_same_schema_and_declared_limits(tmp_path, monkeypatch):
    value = {"schema_version": "local-source-prepare-request/1", "source_request": {"entity": "Synthetic",
             "market": "US", "document_kind": "annual_report", "fiscal_year": 2025,
             "as_of_date": "2026-03-31"},
             "limits": {"max_candidates": 3, "max_bytes": 40000, "timeout_seconds": 2}}
    SourceRequest(**value["source_request"])
    path = tmp_path / "request.json"
    path.write_bytes(json.dumps(value).encode() + b" " * 140000)
    config = tmp_path / "catalog.yaml"
    config.write_text(yaml.safe_dump({"schema_version": "1.0", "catalog_dir": str(tmp_path / "catalog"),
        "roots": [{"root_id": "synthetic", "kind": "company_raw", "path": str(tmp_path)}]}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(local_prepare_cli, "SourceCatalog", lambda *_: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(local_prepare_cli, "prepare_local_source", lambda *args, **kwargs: calls.append(kwargs["limits"]) or {"status": "not_found"})
    assert local_prepare_cli.main(["--config", str(config), "--request", str(path)]) == 0
    assert calls == [LocalPrepareLimits(**value["limits"])]


def test_explicit_local_resource_ceiling_is_not_reclamped_to_hidden_defaults():
    limits = LocalPrepareLimits(max_candidates=512, max_bytes=2**30 + 1, timeout_seconds=601,
                               max_discovery_groups=4097, max_discovery_entries=65537)
    budget = LocalReadBudget(limits)
    assert budget.max_candidates == 512 and budget.max_bytes == 2**30 + 1
    assert budget.max_discovery_entries == 65537
    assert LocalPrepareLimits().max_candidates == 16  # defaults do not silently grow


@pytest.mark.parametrize("value", [True, 0, -1, float("inf"), float("nan")])
def test_actual_local_deadline_still_requires_positive_finite_seconds(value):
    with pytest.raises(ValueError, match="invalid local deadline"):
        LocalPrepareLimits(timeout_seconds=value)


def test_active_verified_original_is_not_blocked_by_retirement_history_count(lake):
    catalog, reader, ref, original = lake
    for _ in range(65):
        retire_document(catalog.store, document_id=ref.document_id, reason="synthetic lifecycle", created_by="test")
        restore_document(catalog.store, document_id=ref.document_id, reason="same verified source", created_by="test")
    budget = LocalReadBudget(LocalPrepareLimits())
    observed = observe_document(catalog, ref.document_id, budget=budget)
    assert len(observed["retire_audit"]) == 65
    assert observed["version"]["source_status"] == "active"
    assert budget.discovery_entries >= 65 and budget.bytes_read == 0
    assert reader.open_version(ref).data == original.read_bytes()


def test_many_registered_locations_follow_sufficient_and_insufficient_actual_budgets(lake):
    catalog, _, ref, original = lake
    paths = set()
    for index in range(257):
        path = original.parent / f"copy-{index:04}.pdf"
        path.write_bytes(original.read_bytes())
        paths.add(path.relative_to(catalog.config.roots[0].path).as_posix())
    catalog.register_sources(root_id="company_raw", relative_paths=paths)
    budget = LocalReadBudget(LocalPrepareLimits(max_candidates=512))
    observed = observe_document(catalog, ref.document_id, budget=budget)
    assert len(observed["locations"]) == 258
    checked = verify_registered_original(catalog, ref, budget=budget)
    assert checked.data == original.read_bytes() and len(checked.locations) == 258
    exhausted = LocalReadBudget(LocalPrepareLimits(max_discovery_entries=1))
    with pytest.raises(SourceReadError, match="local_discovery_entry_limit"):
        observe_document(catalog, ref.document_id, budget=exhausted)


def test_registered_inventory_exports_only_location_identity_and_sidecar_observation(lake):
    catalog, _, ref, original = lake
    checked = verify_registered_original(
        catalog, ref, budget=LocalReadBudget(LocalPrepareLimits())
    )
    assert checked.data == original.read_bytes()
    assert checked.locations
    assert all(hasattr(location, "location_id") for location in checked.locations)
    assert all(not hasattr(location, "path") and not hasattr(location, "root")
               for location in checked.locations)

    sidecar = read_registered_sidecar(
        catalog,
        ref,
        checked.locations[0],
        kind="source_sidecar",
        budget=LocalReadBudget(LocalPrepareLimits()),
    )
    assert sidecar is not None
    assert sidecar.original_name == original.name
    assert sidecar.metadata["company_name"] == "Acme"
    assert len(sidecar.content_sha256) == 64


def test_local_budget_preserves_parent_request_account_on_nested_reads():
    budget = LocalReadBudget(LocalPrepareLimits(max_bytes=256))
    assert budget.charge(17) == ""
    budget.begin_request()
    assert budget.bytes_read == 17
    assert budget.max_bytes == 256


def test_registered_sidecar_rejects_location_rebind_after_original_verification(lake):
    catalog, _, ref, original = lake
    second = original.with_name("rebound.pdf")
    second.write_bytes(original.read_bytes())
    second.with_name("meta.json").write_text(
        json.dumps({"provider": "synthetic-rebound"}), encoding="utf-8"
    )
    checked = verify_registered_original(
        catalog, ref, budget=LocalReadBudget(LocalPrepareLimits())
    )
    location = checked.locations[0]
    relative = second.relative_to(catalog.config.roots[0].path).as_posix()
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE locations SET relative_path=? WHERE location_id=?",
            (relative, location.location_id),
        )

    with pytest.raises(SourceReadError, match="location_binding_changed"):
        read_registered_sidecar(
            catalog,
            ref,
            location,
            kind="sec_provider_meta",
            budget=LocalReadBudget(LocalPrepareLimits()),
        )


def test_registered_sidecar_rejects_rebind_during_metadata_read(lake, monkeypatch):
    catalog, _, ref, original = lake
    checked = verify_registered_original(
        catalog, ref, budget=LocalReadBudget(LocalPrepareLimits())
    )
    location = checked.locations[0]
    second = original.with_name("rebound-during-read.pdf")
    second.write_bytes(original.read_bytes())
    budget = LocalReadBudget(LocalPrepareLimits())
    read_metadata = budget.read_metadata_observation

    def read_then_rebind(path, *, root):
        observation = read_metadata(path, root=root)
        relative = second.relative_to(catalog.config.roots[0].path).as_posix()
        with catalog.store.transaction() as connection:
            connection.execute(
                "UPDATE locations SET relative_path=? WHERE location_id=?",
                (relative, location.location_id),
            )
        return observation

    monkeypatch.setattr(budget, "read_metadata_observation", read_then_rebind)
    with pytest.raises(SourceReadError, match="location_binding_changed"):
        read_registered_sidecar(
            catalog,
            ref,
            location,
            kind="source_sidecar",
            budget=budget,
        )

@pytest.mark.parametrize("stop", ["cancelled", "deadline"])
def test_inventory_does_not_reset_cancellation_or_deadline(lake, stop):
    budget = LocalReadBudget(LocalPrepareLimits())
    if stop == "cancelled":
        budget.cancelled = True
    else:
        budget.deadline = 0
    with pytest.raises(SourceReadError, match="cancelled" if stop == "cancelled" else "local_prepare_deadline"):
        observe_document(lake[0], lake[2].document_id, budget=budget)
