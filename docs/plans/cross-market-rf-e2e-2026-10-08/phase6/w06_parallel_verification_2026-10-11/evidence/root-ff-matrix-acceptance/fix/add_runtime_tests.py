from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
ROOT.joinpath('tests/test_w06_matrix_runtime.py').write_text('''"""Runtime countermodels. Synthetic fixtures only; no producer or HTTP calls."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "tools/offline_contract_matrix"
sys.path.insert(0, str(HERE))
import run as runner
import cli_main

def test_production_guard_does_not_read_even_synthetic_key(tmp_path):
    roots = [tmp_path / n for n in ("ff", "cwp", "et")]
    for root in roots:
        (root / "config").mkdir(parents=True)
    key = roots[0] / "config/FMP_API_KEY.txt"
    key.write_text("synthetic-not-a-secret", encoding="utf-8")
    with patch.object(runner, "sha256_file", side_effect=AssertionError("byte read forbidden")):
        guard = runner.ProductionGuard(*roots)
        assert guard.unchanged(guard.snapshot())
    assert "sha256" not in guard.before[str(key)]

def test_context_does_not_inherit_host_credentials_or_endpoints(tmp_path):
    ctx = object.__new__(runner.Context)
    ctx.cwp_root = tmp_path / "cwp"
    ctx.et_root = tmp_path / "et"
    ctx.scratch = tmp_path / "scratch"
    ctx.env = SimpleNamespace(proxy_state=tmp_path / "proxy")
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY":"synthetic-marker", "OPENAI_API_KEY":"synthetic-marker", "API_BASE_URL":"https://synthetic.invalid", "FMP_API_KEY_FILE":"synthetic-file"}, clear=True):
        child = ctx.child_env()
    assert not ({"DEEPSEEK_API_KEY", "OPENAI_API_KEY", "API_BASE_URL", "FMP_API_KEY_FILE"} & child.keys())
    assert child["FMP_API_KEY"] == runner.FAKE_FMP_KEY
    assert Path(child["HOME"]).is_relative_to(ctx.scratch)

def _unbound_cli(tmp_path):
    owned = tmp_path / "owned"
    out = tmp_path / "out"
    (owned / "scratch").mkdir(parents=True)
    out.mkdir()
    existing = owned / "scratch/existing.txt"
    existing.write_text("old baseline", encoding="utf-8")
    sentinel = owned / runner.SENTINEL_NAME
    sentinel.write_text("old sentinel", encoding="utf-8")
    report = out / "report.json"
    report.write_text("old report", encoding="utf-8")
    class Context:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
        def child_env(self): return {}
    with patch.object(cli_main, "Context", Context), patch.object(cli_main, "_verify_binding", return_value={"verified":False}), patch.object(cli_main, "seed_all"), patch.object(cli_main, "_case_registry", return_value=[]), patch.object(cli_main, "_dependency", return_value=SimpleNamespace(to_dict=lambda: {})), patch.object(cli_main, "_module_record", return_value={}):
        rc = cli_main.main(["--cwp-project", str(tmp_path / "cwp"), "--et-project", str(tmp_path / "et"), "--owned-root", str(owned), "--out-root", str(out)])
    return rc, existing, sentinel, report

def test_unbound_cli_never_reports_success(tmp_path):
    rc, *_ = _unbound_cli(tmp_path)
    assert rc != 0

def test_cli_preserves_existing_scratch_sentinel_and_report(tmp_path):
    _, existing, sentinel, report = _unbound_cli(tmp_path)
    assert existing.read_text(encoding="utf-8") == "old baseline"
    assert sentinel.read_text(encoding="utf-8") == "old sentinel"
    assert report.read_text(encoding="utf-8") == "old report"
''', encoding='utf-8')
