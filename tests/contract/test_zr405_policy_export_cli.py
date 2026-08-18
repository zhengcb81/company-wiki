"""ZR-405 acceptance tests: read-only ``policy-export`` CLI endpoint.

The endpoint emits the root policy for consumers (filing-fetch
containment): ``policy_hash`` must equal ``export_policy_2x``'s canonical
hash, consumers can re-compute the hash over the payload bytes
(excluding the ``policy_hash`` envelope key), and roots carry the
contract fields with absolute path_refs (the byte-for-byte hash contract
forbids reshaping; the local wiki->filing channel is trusted).  Read-only:
the command touches no catalog/database.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import cli  # noqa: E402


def _config_path(tmp_path: Path, *, include_dayu: bool = True) -> Path:
    # cli.main derives project_root as config_path.parents[1], so the
    # config must live at <project_root>/config/source_catalog.yaml.
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    roots = [
        {
            "root_id": "company_raw",
            "kind": "company_raw",
            "path": "${PROJECT_ROOT}/companies",
            "priority": 10,
            "adapter_id": "company_raw_v1",
            "read_only": True,
            "reusable_for_filing": True,
        },
        {
            "root_id": "dropbox_stock",
            "kind": "directory",
            "path": "${PROJECT_ROOT}/Dropbox/Stock",
            "priority": 30,
            "adapter_id": "sidecar_filing_v1",
            "read_only": True,
            "reusable_for_filing": True,
        },
    ]
    if include_dayu:
        roots.append(
            {
                "root_id": "dayu_portfolio",
                "kind": "dayu_portfolio",
                "path": "${PROJECT_ROOT}/portfolio",
                "priority": 20,
                "adapter_id": "dayu_filing_v1",
                "read_only": True,
                "reusable_for_filing": True,
            }
        )
    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "reusable_root_kinds": ["company_raw", "dayu_portfolio", "directory"],
        "roots": roots,
    }
    path = config_dir / "source_catalog.yaml"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _run_export(config_path: Path) -> dict:
    import io
    import contextlib

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["--config", str(config_path), "policy-export"])
    assert code == 0, out.getvalue()
    return json.loads(out.getvalue())


def test_zr405_policy_export_hash_matches_export_policy_2x(tmp_path):
    """The endpoint's policy_hash is the SAME canonical hash as
    export_policy_2x(config), and consumers can re-compute it over the
    payload bytes (excluding the policy_hash envelope key) — the byte
    contract holds."""
    import hashlib

    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.policy_2x import export_policy_2x

    config_path = _config_path(tmp_path)
    config = load_catalog_config(config_path, project_root=tmp_path)
    expected_hash, policy = export_policy_2x(config)
    payload = _run_export(config_path)
    assert payload["policy_hash"] == expected_hash
    recomputed = hashlib.sha256(
        json.dumps(
            {k: v for k, v in payload.items() if k != "policy_hash"},
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert recomputed == expected_hash
    assert payload["schema_version"] == policy["schema_version"]


def test_zr405_policy_export_roots_contract_fields(tmp_path):
    """Every root carries the contract fields; reusable flags match the
    config; the endpoint is a pure function of the config (no DB access)."""
    payload = _run_export(_config_path(tmp_path))
    by_id = {entry["root_id"]: entry for entry in payload["roots"]}
    assert set(by_id) == {"company_raw", "dropbox_stock", "dayu_portfolio"}
    assert by_id["dropbox_stock"]["reusable_for_filing"] is True
    assert by_id["dropbox_stock"]["read_only"] is True
    for entry in payload["roots"]:
        for key in (
            "root_id",
            "path_ref",
            "adapter_id",
            "read_only",
            "reusable_for_filing",
            "priority",
        ):
            assert key in entry, entry


def test_zr405_policy_export_paths_are_absolute_and_consistent(tmp_path):
    """path_ref values are the verbatim absolute root paths from the
    export (the byte-for-byte hash contract forbids reshaping them)."""
    payload = _run_export(_config_path(tmp_path))
    for entry in payload["roots"]:
        assert Path(entry["path_ref"]).is_absolute(), entry
        assert str(tmp_path.resolve()) in entry["path_ref"], entry


def test_zr405_policy_export_deterministic(tmp_path):
    """Two runs produce byte-identical output (stable consumer contract)."""
    config_path = _config_path(tmp_path)
    first = _run_export(config_path)
    second = _run_export(config_path)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_zr405_policy_export_read_only(tmp_path):
    """The command creates no catalog database and writes nothing."""
    config_path = _config_path(tmp_path)
    catalog_dir = tmp_path / ".source_catalog"
    _run_export(config_path)
    assert not catalog_dir.exists()
