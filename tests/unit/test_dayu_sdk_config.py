"""Bounded SDK bridge is configured without loading Dayu model configuration."""

from pathlib import Path
import sys

import pytest
import yaml

from company_wiki.source_catalog.acquisition_config import load_acquisition_config, AcquisitionConfigError


def _config(tmp_path: Path):
    adapters = {}
    for market in ("cn", "hk", "us"):
        project = tmp_path / market
        project.mkdir()
        adapters[market] = {
            "name": market, "version": "1.0.0", "project_root": str(project),
            "config_root": None, "command": [sys.executable, "-B", "bridge.py"],
            "interface": "json_command_v1" if market == "cn" else "dayu_sdk_bounded_v1",
            "supports_acquisition_budget": True,
        }
    return {"schema_version": "1.1", "staging_root": str(tmp_path / "stage"),
            "timeout_seconds": 30, "adapters": adapters}


def test_bounded_hk_us_use_json_bridge_and_need_no_llm_config(tmp_path):
    config = _config(tmp_path)
    path = tmp_path / "acquisition.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    registry = load_acquisition_config(path, project_root=tmp_path).build_registry()
    assert registry.hk.supports_acquisition_budget is True
    assert registry.us.supports_acquisition_budget is True
    assert type(registry.hk).__name__ == "JsonCommandAdapter"
    assert type(registry.us).__name__ == "JsonCommandAdapter"


@pytest.mark.parametrize("market", ["hk", "us"])
def test_sdk_config_cannot_claim_an_unbounded_bridge(tmp_path, market):
    config = _config(tmp_path)
    config["adapters"][market]["supports_acquisition_budget"] = False
    path = tmp_path / "acquisition.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(AcquisitionConfigError, match="requires bounded"):
        load_acquisition_config(path, project_root=tmp_path)
