"""Read-policy pin contracts that are deliberately separate from RootPolicy 2.x."""

from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import re
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import (  # noqa: E402
    CatalogConfig,
    RootSpec,
    RouteSpec,
)
from company_wiki.source_catalog.policy_2x import export_policy_2x  # noqa: E402
from company_wiki.source_catalog.runtime_policy import build_snapshot  # noqa: E402
from company_wiki.source_catalog.source_read_policy import (  # noqa: E402
    source_read_policy_sha256,
)


def _config(tmp_path: Path) -> CatalogConfig:
    root = RootSpec(
        "lake", tmp_path / "lake", "directory", priority=10,
        adapter_id="sidecar_filing_v1", read_only=True,
        reusable_for_filing=True,
    )
    return CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(root,), reusable_root_kinds=("directory",),
    )


@pytest.mark.parametrize(
    "change",
    (
        {"max_file_size": 42},
        {"allowed_statuses": ("quarantined",)},
        {"priority": 5},
    ),
)
def test_read_policy_pin_covers_effective_admission_dimensions(tmp_path, change):
    config = _config(tmp_path)
    first = source_read_policy_sha256(config, None)
    changed = replace(config, roots=(replace(config.roots[0], **change),))
    second = source_read_policy_sha256(changed, None)
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert second != first
    if set(change) <= {"max_file_size", "allowed_statuses"}:
        assert export_policy_2x(config)[0] == export_policy_2x(changed)[0]


def test_read_policy_pin_covers_runtime_activation_snapshot(tmp_path):
    config = _config(tmp_path)
    policy_hash = export_policy_2x(config)[0]
    snapshot = build_snapshot({
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": False,
        },
        "current_epoch": "epoch-a",
        "active_cohorts": ["cohort-a"],
        "policy_hash": policy_hash,
        "updated_at": "2026-09-27T00:00:00Z",
    })
    assert source_read_policy_sha256(config, None) != source_read_policy_sha256(
        config, snapshot
    )
    changed = build_snapshot({
        key: value for key, value in snapshot.items()
        if key != "snapshot_sha256"
    } | {"current_epoch": "epoch-b"})
    assert source_read_policy_sha256(config, snapshot) != source_read_policy_sha256(
        config, changed
    )


def _runtime_snapshot(
    config: CatalogConfig,
    *,
    updated_at: str = "2026-09-27T00:00:00Z",
    current_epoch: str = "epoch-a",
    active_cohorts: tuple[str, ...] = ("cohort-a",),
    flag_changes: dict[str, bool] | None = None,
) -> dict:
    from company_wiki.source_catalog.runtime_policy import build_snapshot

    flags = {
        "v2_scan_shadow": False,
        "v2_persist_assertions": False,
        "v2_resolve_shadow": False,
        "v2_resolve_active": False,
        "v2_bundle_active": False,
        "legacy_bridge_enabled": False,
    }
    flags.update(flag_changes or {})
    return build_snapshot({
        "schema_version": "1.0",
        "flags": flags,
        "current_epoch": current_epoch,
        "active_cohorts": list(active_cohorts),
        "policy_hash": export_policy_2x(config)[0],
        "updated_at": updated_at,
    })


def test_read_policy_pin_ignores_timestamp_and_unrelated_runtime_flags(tmp_path):
    config = _config(tmp_path)
    baseline = _runtime_snapshot(config)
    changed = _runtime_snapshot(
        config,
        updated_at="2026-09-28T00:00:00Z",
        flag_changes={"v2_scan_shadow": True},
    )

    assert baseline["snapshot_sha256"] != changed["snapshot_sha256"]
    assert source_read_policy_sha256(config, baseline) == source_read_policy_sha256(
        config, changed
    )


@pytest.mark.parametrize(
    "changes",
    (
        {"current_epoch": "epoch-b", "flag_changes": {
            "v2_scan_shadow": True, "v2_persist_assertions": True,
            "v2_resolve_shadow": True, "v2_resolve_active": True,
        }},
        {"active_cohorts": ("cohort-b",), "flag_changes": {
            "v2_scan_shadow": True, "v2_persist_assertions": True,
            "v2_resolve_shadow": True, "v2_resolve_active": True,
        }},
        {"flag_changes": {
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
        }},
        {"flag_changes": {"legacy_bridge_enabled": True}},
    ),
)
def test_read_policy_pin_changes_with_effective_reader_visibility(tmp_path, changes):
    config = _config(tmp_path)
    baseline = _runtime_snapshot(config)
    changed = _runtime_snapshot(config, **changes)

    assert source_read_policy_sha256(config, baseline) != source_read_policy_sha256(
        config, changed
    )


def _indexed_reader(tmp_path, request):
    from company_wiki.source_catalog import SourceCatalog, SourceVersionReader

    config = _config(tmp_path)
    raw = config.roots[0].path / "2025.txt"
    raw.parent.mkdir()
    body = b"Revenue increased through expansion of our product portfolio."
    raw.write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()
    raw.with_name(raw.name + ".source.json").write_text(json.dumps({
        "schema_version": "1.0", "canonical_entity_id": "ent-acme",
        "display_name": "Acme", "market": "US", "security_id": "ACME",
        "document_kind": "annual_report", "source_title": "Acme annual report",
        "fiscal_year": 2025, "period_end": "2025-12-31", "filing_date": "2026-02-20",
        "form_type": "10-K", "provider": "sec", "provider_document_id": "doc-1",
        "content_sha256": digest, "language": "en",
    }), encoding="utf-8")
    catalog = SourceCatalog(config)
    request.addfinalizer(catalog.close)
    catalog.scan()
    row = catalog.reader.fetchone(
        "SELECT d.document_id, d.primary_source_id AS source_id "
        "FROM documents d JOIN sources s ON s.source_id=d.primary_source_id "
        "WHERE s.content_sha256=?", (digest,),
    )
    assert row is not None
    reader = SourceVersionReader(catalog)
    ref = reader.query_ref(row["document_id"], row["source_id"], digest)
    return catalog, reader, ref, raw, body


def _steady_runtime(config):
    return build_snapshot({
        "schema_version": "2.0", "mode": "steady",
        "policy_hash": export_policy_2x(config)[0],
        "updated_at": "2026-10-07T00:00:00Z",
    })


def _batch_request(ref):
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest

    return NarrativeBatchRequest.from_dict({
        "schema_version": "narrative-batch-request/1", "run_id": "pin-resume",
        "sources": [asdict(ref)], "profile": "P1", "max_seconds": 30,
        "max_tokens": 1000, "max_cost_usd": "0.01",
        "model": {"model_id": "test-model", "endpoint": "https://example.invalid/v1",
                  "api_key_env": "TEST_PIN_UNUSED_KEY"},
        "pricing": {"version": "test", "input_micro_usd_per_million_tokens": 1,
                    "output_micro_usd_per_million_tokens": 1},
    })


@pytest.mark.parametrize("change", (
    {"privacy_class": "diagnostic-label"}, {"cohort": "diagnostic-label"},
    {"canonical_write_target": "diagnostic-label"},
    {"adapter_id": "company_raw_v1"}, {"encoding": "gb18030"}, {"read_only": False},
    {"routes": (RouteSpec(include=("reports/**",), exclude=("secret/**",)),)},
))
def test_steady_nonread_config_change_preserves_actual_open_and_batch_identity(tmp_path, request, change):
    from company_wiki.automation.narrative_batch import build_batch_events

    catalog, reader, ref, _, body = _indexed_reader(tmp_path, request)
    policy_path = catalog.config.catalog_dir / "runtime_policy.json"
    policy_path.write_text(json.dumps(_steady_runtime(catalog.config)), encoding="utf-8")
    pin = reader.read_policy_sha256()
    batch = _batch_request(ref)
    first = build_batch_events(batch, reader, now="2026-10-07T00:00:00Z")
    catalog.config = replace(catalog.config, roots=(replace(
        catalog.config.roots[0], **change,
    ),))
    assert reader.open_version(ref, expected_read_policy_sha256=pin).data == body
    second = build_batch_events(batch, reader, now="2026-10-07T00:00:00Z")
    assert second.input_hash == first.input_hash
    assert second.events == first.events


@pytest.mark.parametrize("change", (
    {"max_file_size": 1}, {"allowed_statuses": ("quarantined",)},
    {"allowed_document_kinds": ("quarterly_report",)},
))
def test_changed_actual_admission_refuses_existing_pin_and_unpinned_open(tmp_path, request, change):
    from company_wiki.source_catalog import SourceReadError

    catalog, reader, ref, _, _ = _indexed_reader(tmp_path, request)
    pin = reader.read_policy_sha256()
    catalog.config = replace(catalog.config, roots=(replace(catalog.config.roots[0], **change),))
    with pytest.raises(SourceReadError, match="root_admission_denied"):
        reader.open_version(ref, expected_read_policy_sha256=pin)
    with pytest.raises(SourceReadError, match="root_admission_denied"):
        reader.open_version(ref)


def test_effective_pin_upgrade_reports_current_rules_without_denying_old_lineage(tmp_path, request):

    catalog, reader, ref, _, body = _indexed_reader(tmp_path, request)

    def plain(value):
        if isinstance(value, Path):
            return str(value.resolve(strict=False))
        if isinstance(value, dict):
            return {key: plain(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [plain(item) for item in value]
        return value

    old_payload = {"schema_version": "1.0", "catalog_config": plain(asdict(catalog.config)),
                   "runtime_read_activation": None}
    old_pin = hashlib.sha256(json.dumps(
        old_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    opened = reader.open_version(ref, expected_read_policy_sha256=old_pin)
    assert opened.data == body and opened.source_read_policy_sha256 != old_pin
    new_pin = reader.read_policy_sha256()
    assert new_pin != old_pin
    assert reader.open_version(ref, expected_read_policy_sha256=new_pin).data == body


def test_labels_do_not_disable_actual_byte_verification(tmp_path, request):
    from company_wiki.source_catalog import SourceReadError

    catalog, reader, ref, raw, body = _indexed_reader(tmp_path, request)
    pin = reader.read_policy_sha256()
    catalog.config = replace(catalog.config, roots=(replace(
        catalog.config.roots[0], privacy_class="private_user",
    ),))
    raw.write_bytes(b"x" * len(body))
    with pytest.raises(SourceReadError, match="content_sha256_mismatch"):
        reader.open_version(ref)
    assert reader.read_policy_sha256() == pin


def test_steady_effective_rules_still_refuse_changed_root_with_old_pin(tmp_path, request):
    from company_wiki.source_catalog import SourceReadError

    catalog, reader, ref, _, _ = _indexed_reader(tmp_path, request)
    (catalog.config.catalog_dir / "runtime_policy.json").write_text(
        json.dumps(_steady_runtime(catalog.config)), encoding="utf-8",
    )
    pin = reader.read_policy_sha256()
    catalog.config = replace(catalog.config, roots=(replace(
        catalog.config.roots[0], path=tmp_path / "unregistered-lake",
    ),))
    with pytest.raises(SourceReadError, match="no_verified_location"):
        reader.open_version(ref, expected_read_policy_sha256=pin)
    with pytest.raises(SourceReadError, match="no_verified_location"):
        reader.open_version(ref)


def test_bad_automatic_runtime_snapshot_is_ignored_by_current_reads(tmp_path, request):

    catalog, reader, ref, _, body = _indexed_reader(tmp_path, request)
    snapshot = _steady_runtime(catalog.config)
    snapshot["policy_hash"] = "a" * 64  # do not rebuild snapshot hash
    (catalog.config.catalog_dir / "runtime_policy.json").write_text(
        json.dumps(snapshot), encoding="utf-8",
    )
    assert reader.read_policy_sha256()
    assert reader.open_version(ref).data == body


def test_legacy_automatic_runtime_does_not_bind_current_personal_reads(tmp_path, request):

    catalog, reader, ref, _, body = _indexed_reader(tmp_path, request)
    (catalog.config.catalog_dir / "runtime_policy.json").write_text(
        json.dumps(_runtime_snapshot(catalog.config)), encoding="utf-8",
    )
    reader.read_policy_sha256()
    catalog.config = replace(catalog.config, roots=(replace(
        catalog.config.roots[0], cohort="changed-old-cohort",
    ),))
    assert reader.read_policy_sha256()
    assert reader.open_version(ref).data == body
