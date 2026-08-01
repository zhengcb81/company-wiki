"""Safety contracts for user-selected exact-copy recycling."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def _catalog_module():
    import company_wiki.source_catalog as module

    return module


def _catalog_with_three_copies(tmp_path: Path):
    module = _catalog_module()
    project = tmp_path / "project"
    roots = [tmp_path / "primary", tmp_path / "secondary", tmp_path / "tertiary"]
    paths = []
    content = b"ACME FY2025 audited annual report."
    for index, root in enumerate(roots):
        path = root / f"renamed-copy-{index}.pdf"
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        paths.append(path)
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=tuple(
                module.RootSpec(
                    f"root_{index}",
                    root,
                    "directory",
                    priority=10 + index * 10,
                )
                for index, root in enumerate(roots)
            ),
        )
    )
    catalog.scan()
    return module, catalog, paths


def test_duplicate_inventory_exposes_only_noncanonical_exact_copies(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    service = module.DuplicateCleanupService(catalog, recycler=lambda path: None)

    inventory = service.list_groups(limit=10)

    assert inventory["schema_version"] == "1.0"
    assert inventory["total_groups"] == 1
    assert inventory["total_reclaimable_copies"] == 2
    group = inventory["groups"][0]
    assert group["canonical"]["absolute_path"] == str(paths[0].resolve())
    assert group["canonical"]["eligible_for_recycle"] is False
    assert group["canonical"]["protection_reason"] == "canonical_copy"
    assert [item["absolute_path"] for item in group["duplicates"]] == [
        str(paths[1].resolve()),
        str(paths[2].resolve()),
    ]
    assert all(item["eligible_for_recycle"] for item in group["duplicates"])
    assert "confirmation_token" not in group["duplicates"][0]

    preview = service.preview(group["duplicates"][0]["location_id"])
    assert preview["status"] == "ready"
    assert preview["confirmation_phrase"] == (
        "RECYCLE " + preview["confirmation_token"][-8:].upper()
    )
    with pytest.raises(module.DuplicateCleanupError, match="canonical"):
        service.preview(group["canonical"]["location_id"])


def test_recycle_selected_copy_preserves_other_files_and_tombstones_location(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    recycled: list[Path] = []

    def recycler(path: Path) -> None:
        recycled.append(path)
        path.unlink()

    service = module.DuplicateCleanupService(catalog, recycler=recycler)
    selected = service.list_groups(limit=10)["groups"][0]["duplicates"][0]
    preview = service.preview(selected["location_id"])

    result = service.recycle(
        selected["location_id"],
        confirmation_token=preview["confirmation_token"],
    )

    assert result["status"] == "recycled"
    assert result["recoverable"] is True
    assert recycled == [paths[1].resolve()]
    assert paths[0].is_file()
    assert not paths[1].exists()
    assert paths[2].is_file()
    row = catalog.store.fetchone(
        "SELECT location_status FROM locations WHERE location_id=?",
        (selected["location_id"],),
    )
    assert row is not None and row["location_status"] == "missing"
    remaining = service.list_groups(limit=10)
    assert remaining["total_groups"] == 1
    assert remaining["total_reclaimable_copies"] == 1

    journal_path = catalog.config.catalog_dir / "duplicate_cleanup_events.jsonl"
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert [item["event"] for item in events] == ["requested", "recycled"]
    assert {item["action_id"] for item in events} == {result["action_id"]}
    exported = catalog.export_indexes()
    audit_csv = exported["duplicate_cleanup_events_csv"].read_text(encoding="utf-8-sig")
    assert result["action_id"] in audit_csv
    assert "requested" in audit_csv and "recycled" in audit_csv


def test_recycle_revalidates_hash_boundary_and_failure_before_catalog_mutation(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    recycler_calls: list[Path] = []

    def recycler(path: Path) -> None:
        recycler_calls.append(path)

    service = module.DuplicateCleanupService(catalog, recycler=recycler)
    selected = service.list_groups(limit=10)["groups"][0]["duplicates"][0]
    preview = service.preview(selected["location_id"])
    original_stat = paths[1].stat()
    tampered = bytearray(paths[1].read_bytes())
    tampered[0] ^= 1
    paths[1].write_bytes(tampered)
    os.utime(
        paths[1],
        ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
    )

    with pytest.raises(module.DuplicateCleanupError, match="hash"):
        service.recycle(
            selected["location_id"],
            confirmation_token=preview["confirmation_token"],
        )
    assert recycler_calls == []
    row = catalog.store.fetchone(
        "SELECT location_status FROM locations WHERE location_id=?",
        (selected["location_id"],),
    )
    assert row is not None and row["location_status"] == "active"

    paths[1].write_bytes(paths[0].read_bytes())
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(paths[0].read_bytes())
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE locations SET absolute_path=? WHERE location_id=?",
            (str(outside.resolve()), selected["location_id"]),
        )
    with pytest.raises(module.DuplicateCleanupError, match="configured root"):
        service.preview(selected["location_id"])
    assert outside.is_file()
    assert recycler_calls == []


def test_recycler_failure_keeps_location_active_and_records_failure(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)

    def broken_recycler(path: Path) -> None:
        raise OSError("recycle bin unavailable")

    service = module.DuplicateCleanupService(catalog, recycler=broken_recycler)
    selected = service.list_groups(limit=10)["groups"][0]["duplicates"][0]
    preview = service.preview(selected["location_id"])

    with pytest.raises(module.DuplicateCleanupError, match="recycle bin unavailable"):
        service.recycle(
            selected["location_id"],
            confirmation_token=preview["confirmation_token"],
        )

    assert paths[1].is_file()
    row = catalog.store.fetchone(
        "SELECT location_status FROM locations WHERE location_id=?",
        (selected["location_id"],),
    )
    assert row is not None and row["location_status"] == "active"
    journal_path = catalog.config.catalog_dir / "duplicate_cleanup_events.jsonl"
    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    assert [item["event"] for item in events] == ["requested", "failed"]


def test_stale_confirmation_and_missing_canonical_fail_before_recycler(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    recycler_calls: list[Path] = []
    service = module.DuplicateCleanupService(
        catalog,
        recycler=lambda path: recycler_calls.append(path),
    )
    selected = service.list_groups(limit=10)["groups"][0]["duplicates"][0]
    preview = service.preview(selected["location_id"])
    current = paths[1].stat()
    os.utime(
        paths[1],
        ns=(current.st_atime_ns, current.st_mtime_ns + 1_000_000_000),
    )

    with pytest.raises(module.DuplicateCleanupError, match="stale"):
        service.recycle(
            selected["location_id"],
            confirmation_token=preview["confirmation_token"],
        )
    assert recycler_calls == []

    paths[0].unlink()
    with pytest.raises(module.DuplicateCleanupError, match="no longer exists"):
        service.preview(selected["location_id"])
    assert paths[1].is_file()
    assert paths[2].is_file()
    assert recycler_calls == []


def test_duplicate_cli_lists_previews_and_recycles_only_by_location_id(
    tmp_path, monkeypatch, capsys
):
    import company_wiki.source_catalog.cli as cli
    import company_wiki.source_catalog.duplicate_cleanup as cleanup

    _module, catalog, paths = _catalog_with_three_copies(tmp_path)
    config_path = catalog.config.project_root / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    root_lines = []
    for root in catalog.config.roots:
        root_lines.extend(
            [
                f"  - root_id: {root.root_id}",
                "    kind: directory",
                f"    path: '{root.path.as_posix()}'",
                f"    priority: {root.priority}",
            ]
        )
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '${PROJECT_ROOT}/.source_catalog'",
                "roots:",
                *root_lines,
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert cli.main(["--config", str(config_path), "duplicates", "--limit", "5"]) == 0
    inventory = json.loads(capsys.readouterr().out)
    selected = inventory["groups"][0]["duplicates"][0]

    assert (
        cli.main(
            [
                "--config",
                str(config_path),
                "duplicate-preview",
                "--location-id",
                selected["location_id"],
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(cleanup, "recycle_to_windows_bin", lambda path: path.unlink())

    assert (
        cli.main(
            [
                "--config",
                str(config_path),
                "duplicate-recycle",
                "--location-id",
                selected["location_id"],
                "--confirmation-token",
                preview["confirmation_token"],
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "recycled"
    assert paths[0].is_file()
    assert not paths[1].exists()
    assert paths[2].is_file()


def test_control_center_exposes_browse_preview_and_single_copy_recycle_flow():
    project_root = Path(__file__).resolve().parents[2]
    script = (project_root / "scripts" / "source_catalog_control.ps1").read_text(
        encoding="utf-8"
    )

    assert "Show-DuplicateCenter" in script
    assert "duplicates" in script
    assert "duplicate-preview" in script
    assert "duplicate-recycle" in script
    assert "confirmation_phrase" in script
    assert "'--location-id'" in script
    assert "'--path'" not in script
    assert "Remove-Item" not in script
    assert "DELETE FROM" not in script
