"""Safety contracts for duplicate maintenance after the G3-CWP-MAINT retirement.

The read surface (``list_groups``) stays: canonical/exact-copy inventory with
``eligible_for_recycle`` uniformly false, inventory-only reporting and no
confirmation tokens.  The write surface (preview / recycle / recycle-bin /
journal record) fails closed with the unified retirement signal before any
hash, root, token or journal check — and the CLI branches fail closed the
same way.  The stale ``scripts/source_catalog_control.ps1`` entry assertion
was removed with the retired flow (the script no longer exists; it is not
rebuilt).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from company_wiki.source_catalog.maintenance_retirement import (
    RetiredMaintenanceError,
)


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
    assert inventory["inventory_only"] is True
    assert inventory["original_delete_count"] == 0
    assert inventory["reclaimable_is_upper_bound"] is True
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
    assert all(item["eligible_for_recycle"] is False for item in group["duplicates"])
    assert all(item["protection_reason"] for item in group["duplicates"])
    assert "confirmation_token" not in group["duplicates"][0]


def test_duplicate_preview_and_recycle_retire_and_preserve_everything(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    recycler_calls: list[Path] = []
    service = module.DuplicateCleanupService(
        catalog,
        recycler=lambda path: recycler_calls.append(path),
    )
    selected = service.list_groups(limit=10)["groups"][0]["duplicates"][0]
    tree_before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.preview(selected["location_id"])
    assert exc.value.operation == "duplicate-preview"
    assert isinstance(exc.value, module.DuplicateCleanupError)

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.recycle(
            selected["location_id"],
            confirmation_token="stale-token",
        )
    assert exc.value.operation == "duplicate-recycle"
    assert isinstance(exc.value, module.DuplicateCleanupError)

    assert recycler_calls == []
    assert all(path.is_file() for path in paths)
    row = catalog.store.fetchone(
        "SELECT location_status FROM locations WHERE location_id=?",
        (selected["location_id"],),
    )
    assert row is not None and row["location_status"] == "active"
    journal_path = catalog.config.catalog_dir / "duplicate_cleanup_events.jsonl"
    assert not journal_path.exists()
    assert service.journal.read_all() == ()
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")) == (
        tree_before
    )


def test_retirement_skips_hash_root_and_token_validation_entirely(tmp_path):
    """Tampered bytes, a moved path and a stale token used to raise specific
    DuplicateCleanupErrors; the retired entries never reach those checks."""
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    recycler_calls: list[Path] = []
    service = module.DuplicateCleanupService(
        catalog,
        recycler=lambda path: recycler_calls.append(path),
    )
    selected = service.list_groups(limit=10)["groups"][0]["duplicates"][0]

    original_stat = paths[1].stat()
    tampered = bytearray(paths[1].read_bytes())
    tampered[0] ^= 1
    paths[1].write_bytes(tampered)
    os.utime(
        paths[1],
        ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
    )
    with pytest.raises(RetiredMaintenanceError) as exc:
        service.recycle(
            selected["location_id"],
            confirmation_token="whatever",
        )
    assert exc.value.operation == "duplicate-recycle"

    paths[1].write_bytes(paths[0].read_bytes())
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(paths[0].read_bytes())
    with catalog.store.transaction() as connection:
        connection.execute(
            "UPDATE locations SET absolute_path=? WHERE location_id=?",
            (str(outside.resolve()), selected["location_id"]),
        )
    with pytest.raises(RetiredMaintenanceError) as exc:
        service.preview(selected["location_id"])
    assert exc.value.operation == "duplicate-preview"

    paths[0].unlink()
    with pytest.raises(RetiredMaintenanceError) as exc:
        service.preview(selected["location_id"])
    assert exc.value.operation == "duplicate-preview"

    assert outside.is_file()
    assert paths[1].is_file()
    assert paths[2].is_file()
    assert recycler_calls == []


def test_recycle_bin_helper_and_journal_record_retire(tmp_path):
    module, catalog, paths = _catalog_with_three_copies(tmp_path)
    target = paths[1]
    before = target.read_bytes()

    with pytest.raises(RetiredMaintenanceError) as exc:
        module.recycle_to_windows_bin(target)
    assert exc.value.operation == "duplicate-recycle-bin"
    assert target.read_bytes() == before

    with pytest.raises(RetiredMaintenanceError) as exc:
        module.DuplicateCleanupJournal(catalog.config.catalog_dir).record(
            action_id="action-1",
            event="requested",
            location_id="loc-1",
            absolute_path=str(target),
            canonical_location_id="loc-0",
            canonical_path=str(paths[0]),
            source_id="src-1",
            content_sha256="a" * 64,
        )
    assert exc.value.operation == "duplicate-journal-record"
    assert not (catalog.config.catalog_dir / "duplicate_cleanup_events.jsonl").exists()
    assert all(path.is_file() for path in paths)


def test_duplicate_cli_lists_inventory_but_write_entries_retire(tmp_path, capsys):
    import company_wiki.source_catalog.cli as cli

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

    # read-only inventory branch still works
    assert cli.main(["--config", str(config_path), "duplicates", "--limit", "5"]) == 0
    inventory = json.loads(capsys.readouterr().out)
    assert inventory["inventory_only"] is True
    selected = inventory["groups"][0]["duplicates"][0]

    # write branches fail closed as retired, before any state change
    exit_code = cli.main(
        [
            "--config",
            str(config_path),
            "duplicate-preview",
            "--location-id",
            selected["location_id"],
        ]
    )
    error = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert error["status"] == "failed"
    assert "retired" in error["error"]
    assert "duplicate-preview" in error["error"]

    exit_code = cli.main(
        [
            "--config",
            str(config_path),
            "duplicate-recycle",
            "--location-id",
            selected["location_id"],
            "--confirmation-token",
            "any-token",
        ]
    )
    error = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert "retired" in error["error"]
    assert "duplicate-recycle" in error["error"]

    assert all(path.is_file() for path in paths)
    row = catalog.store.fetchone(
        "SELECT location_status FROM locations WHERE location_id=?",
        (selected["location_id"],),
    )
    assert row is not None and row["location_status"] == "active"
    assert not (catalog.config.catalog_dir / "duplicate_cleanup_events.jsonl").exists()
