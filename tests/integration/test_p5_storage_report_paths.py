"""CLI reports must not overwrite the data they describe."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from support.p5_storage_catalog_fixture import build_catalog
from legacy_storage_retirement import main


@pytest.mark.parametrize("kind", ["raw", "new_final", "database"])
def test_report_path_cannot_overwrite_catalog_data(tmp_path: Path, capsys, kind):
    config, store, _ = build_catalog(tmp_path)
    config_path = tmp_path / "source-catalog.json"
    config_path.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": str(config.catalog_dir),
        "roots": [{"root_id": r.root_id, "path": str(r.path), "kind": r.kind, "priority": r.priority}
                  for r in config.roots],
    }), encoding="utf-8")
    target = config.database_path
    if kind == "raw":
        target = Path(store.fetchone("SELECT absolute_path FROM locations LIMIT 1")["absolute_path"])
    elif kind == "new_final":
        target = next((config.catalog_dir / "objects").rglob("*.json"))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    result = main(["inventory", "--config", str(config_path), "--output", str(target)])
    assert result == 2
    assert json.loads(capsys.readouterr().err)["error_code"] == "report_path_overlaps_data"
    assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
