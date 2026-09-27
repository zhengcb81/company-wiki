"""Registered roots stay usable when a new directory joins the data lake.

The root IDs and physical paths are production configuration, not a Python
allowlist.  This test keeps the historical Dropbox registration visible while
proving that an additional well-formed root passes the same doctor.
"""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


WIKI_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = WIKI_ROOT / "config" / "source_catalog.yaml"
sys.path.insert(0, str(WIKI_ROOT / "scripts"))

from config_doctor import diagnose  # noqa: E402


def _load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _diagnose_fixture(tmp_path: Path, data: dict) -> list[str]:
    master = tmp_path / ".source_catalog" / "security_master"
    master.mkdir(parents=True)
    (master / "us.json").write_text("{}", encoding="utf-8")
    fixture = tmp_path / "source_catalog.yaml"
    fixture.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return diagnose(fixture, project_root=tmp_path)


def test_historical_dropbox_root_is_registered() -> None:
    data = _load_config()
    dropbox = next(
        (r for r in data["roots"] if r.get("root_id") == "dropbox_stock"), None
    )
    assert dropbox is not None, "dropbox_stock root missing"
    assert dropbox["kind"] == "directory", "dropbox_stock kind must stay directory"
    assert isinstance(dropbox["path"], str) and dropbox["path"]


def test_configured_roots_pass_generic_doctor(tmp_path: Path) -> None:
    data = _load_config()
    assert _diagnose_fixture(tmp_path, data) == []


def test_additional_directory_root_passes_doctor(tmp_path: Path) -> None:
    data = _load_config()
    fixture = dict(data)
    fixture["roots"] = list(data["roots"]) + [
        {
            "root_id": "other_dir",
            "kind": "directory",
            "path": "${PROJECT_ROOT}/another_lake",
            "priority": 40,
        }
    ]
    (tmp_path / "another_lake").mkdir()
    assert _diagnose_fixture(tmp_path, fixture) == []
