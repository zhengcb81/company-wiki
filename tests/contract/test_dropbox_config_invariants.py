"""WU-2A.1: Dropbox config-only invariants (CONFIG-DBX-01/02).

Lock the two production config entries so a future drift is caught in CI:

- CONFIG-DBX-01: production YAML loads; ``dropbox_stock`` kind/path/priority
  unchanged; ``directory`` is listed in ``reusable_root_kinds``.
- CONFIG-DBX-02: kind=directory roots are EXACTLY the allowlisted pair
  ``{dropbox_stock, future_lake}``. dropbox_stock alone since WU-2A.1;
  ``future_lake`` was added deliberately by ZR-409 (commit eb3aa79 — fourth
  root by CONFIG ONLY, kind ``directory`` + sidecar adapter, pinned by
  tests/contract/test_zr409_fourth_root_real_journeys.py), so the invariant
  now locks the pair.  Any OTHER directory root must fail: the kind-level
  grant in ``reusable_root_kinds`` would otherwise auto-whitelist the new
  root, which is exactly the drift this gate exists to catch.

CONFIG-DBX-03/04 (filing-fetch side) live in the filing-fetch repo.
"""

from __future__ import annotations

from pathlib import Path


WIKI_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = WIKI_ROOT / "config" / "source_catalog.yaml"

# The only directory-kind roots the production grant may whitelist.
_ALLOWED_DIRECTORY_ROOTS = frozenset({"dropbox_stock", "future_lake"})


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


def test_config_dbx_02_directory_kinds_are_exactly_allowlisted() -> None:
    data = _load_config()
    directory_roots = {
        str(r.get("root_id")) for r in data["roots"] if r.get("kind") == "directory"
    }
    assert directory_roots == _ALLOWED_DIRECTORY_ROOTS, (
        "kind=directory roots must be exactly the allowlisted set "
        f"{sorted(_ALLOWED_DIRECTORY_ROOTS)}, got {sorted(directory_roots)}"
    )


def test_config_dbx_02_fixture_third_directory_root_is_caught() -> None:
    """A THIRD directory root — outside the allowlisted pair — in a fixture
    config must be caught by the same invariant: proves the gate detects a
    future drift (an unapproved root would otherwise be auto-whitelisted by
    the kind-level grant)."""
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
    assert "other_dir" in directory_roots, "fixture must introduce a 3rd directory root"
    assert len(directory_roots) == len(_ALLOWED_DIRECTORY_ROOTS) + 1
