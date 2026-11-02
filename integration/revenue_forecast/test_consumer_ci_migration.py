"""System suite retains the former real-chain deployment assertion."""
import importlib.util
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parent
def test_default_cli_fixture_requires_siblings_without_opt_in(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("p5_roots_test", ROOT / "test_p5_source_default_cli_e2e.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delenv("FF_V2_CODE_ROOT", raising=False)
    monkeypatch.delenv("CWP_V2_CODE_ROOT", raising=False)
    rf = tmp_path / "revenue-forecast"
    rf.mkdir()
    monkeypatch.setattr(module, "ROOT", rf)
    for name in ("filing-fetch", "company-wiki"):
        (tmp_path / name).mkdir()
    assert module._env_roots() == (tmp_path / "filing-fetch", tmp_path / "company-wiki")
    (tmp_path / "company-wiki").rmdir()
    with pytest.raises(FileNotFoundError):
        module._env_roots()
