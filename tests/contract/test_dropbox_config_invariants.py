"""WU-2A.1: Dropbox config-only invariants (CONFIG-DBX-01/02).

Lock the two production config entries so a future drift is caught in CI:

- CONFIG-DBX-01: production YAML loads; ``dropbox_stock`` kind/path/priority
  unchanged; ``directory`` is listed in ``reusable_root_kinds``.
- CONFIG-DBX-02: every root with ``kind=directory`` has root_id EXACTLY
  ``{dropbox_stock}``; adding ANY second directory root must fail (the
  kind-level grant would otherwise auto-whitelist the new root).

CONFIG-DBX-03/04 (filing-fetch side) live in the filing-fetch repo.
"""

from __future__ import annotations

from pathlib import Path


WIKI_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = WIKI_ROOT / "config" / "source_catalog.yaml"


def _load_config() -> dict:
    import yaml

    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def test_config_dbx_01_dropbox_reusable_and_fields_frozen() -> None:
    data = _load_config()
    kinds = data["reusable_root_kinds"]
    assert isinstance(kinds, list), "reusable_root_kinds must be a list"
    assert "directory" in kinds, "directory must be in reusable_root_kinds (CONFIG-DBX-01)"
    dropbox = next(
        (r for r in data["roots"] if r.get("root_id") == "dropbox_stock"), None
    )
    assert dropbox is not None, "dropbox_stock root missing"
    assert dropbox["kind"] == "directory", "dropbox_stock kind must stay directory"
    assert dropbox["path"] == "${USER_PROFILE}/Dropbox/Stock", (
        "dropbox_stock path must stay ${USER_PROFILE}/Dropbox/Stock"
    )
    assert dropbox["priority"] == 30, "dropbox_stock priority must stay 30"
    # companies/dayu grants unchanged
    for root_id, kind, priority in (
        ("company_raw", "company_raw", 10),
        ("dayu_portfolio", "dayu_portfolio", 20),
    ):
        entry = next((r for r in data["roots"] if r.get("root_id") == root_id), None)
        assert entry is not None, f"{root_id} root missing"
        assert entry["kind"] == kind and entry["priority"] == priority


def test_config_dbx_02_only_dropbox_is_directory_kind() -> None:
    data = _load_config()
    directory_roots = {
        str(r.get("root_id")) for r in data["roots"] if r.get("kind") == "directory"
    }
    assert directory_roots == {"dropbox_stock"}, (
        f"kind=directory roots must be exactly {{dropbox_stock}}, got {directory_roots}"
    )


def test_config_dbx_02_fixture_second_directory_root_fails() -> None:
    """A second directory root in a fixture config must be rejected by the
    same invariant — proves the check can catch a future drift."""
    import yaml

    data = _load_config()
    fixture = dict(data)
    fixture["roots"] = list(data["roots"]) + [
        {
            "root_id": "other_dir",
            "kind": "directory",
            "path": "${USER_PROFILE}/somewhere",
            "priority": 40,
        }
    ]
    raw = yaml.safe_dump(fixture, sort_keys=False)
    directory_roots = {
        str(r.get("root_id"))
        for r in yaml.safe_load(raw)["roots"]
        if r.get("kind") == "directory"
    }
    assert directory_roots != {"dropbox_stock"}, "fixture must introduce a 2nd directory root"
    assert len(directory_roots) == 2
