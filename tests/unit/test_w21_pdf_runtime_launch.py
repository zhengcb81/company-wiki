"""The production launch owner isolates the child interpreter search path.

Parent-injected PYTHONPATH/PYTHONHOME/user sites must not reach the real
child: it starts only from the configured interpreter, its own site-packages
and the explicit first-party source tree. The parent environment is observed,
never modified. No SDK launch happens here — a lightweight sentinel child
carries the proof.
"""
import json
import os
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from company_wiki._bounded_process import run_bounded
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog import narrative_pdf_enhancement as owner
from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement
from unit.test_pdf_paragraph_runtime import config, source


def poison_parent_environment(monkeypatch, tmp_path):
    poison = tmp_path / "poison-packages"
    poison.mkdir()
    (poison / "docling.py").write_text("raise AssertionError('injected docling reached the child')\n", encoding="utf-8")
    (poison / "shadow_probe.py").write_text("marker = 'injected-pythonpath'\n", encoding="utf-8")
    user_base = tmp_path / "poison-user"
    site_packages = user_base / "lib" / "site-packages"
    site_packages.mkdir(parents=True)
    (site_packages / "shadow_probe.py").write_text("marker = 'injected-user-site'\n", encoding="utf-8")
    home = tmp_path / "poison-home"
    home.mkdir()
    monkeypatch.setenv("PYTHONPATH", str(poison))
    monkeypatch.setenv("PYTHONHOME", str(home))
    monkeypatch.setenv("PYTHONUSERBASE", str(user_base))
    monkeypatch.setenv("PYTHONSTARTUP", str(tmp_path / "startup.py"))
    return poison


SENTINEL = (
    "import importlib.util, json, os, site, sys\n"
    "info = {'pythonpath_env': os.environ.get('PYTHONPATH'),\n"
    "        'isolated': bool(sys.flags.isolated), 'safe_path': bool(sys.flags.safe_path),\n"
    "        'utf8_mode': bool(sys.flags.utf8_mode), 'user_site': bool(site.ENABLE_USER_SITE),\n"
    "        'poison_path_entries': [p for p in sys.path if 'poison' in p]}\n"
    "spec = importlib.util.find_spec('docling')\n"
    "info['docling_origin'] = None if spec is None or spec.origin is None else spec.origin\n"
    "shadow = importlib.util.find_spec('shadow_probe')\n"
    "info['shadow_origin'] = None if shadow is None or shadow.origin is None else shadow.origin\n"
    "print(json.dumps(info))\n"
)


def test_child_environment_omits_parent_python_search_config(monkeypatch, tmp_path):
    poison_parent_environment(monkeypatch, tmp_path)
    env = owner.child_environment(cpu_threads=4)
    assert not {"PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "PYTHONSTARTUP"} & set(env)
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["HF_HUB_OFFLINE"] == "1" and env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["OMP_NUM_THREADS"] == env["OPENBLAS_NUM_THREADS"] == env["MKL_NUM_THREADS"] == "4"
    assert {"PATH", "SYSTEMROOT"} <= set(env), "OS essentials must survive the allowlist"


def test_real_child_rejects_injected_search_paths_and_keeps_parent_env(monkeypatch, tmp_path):
    poison = poison_parent_environment(monkeypatch, tmp_path)
    before = dict(os.environ)
    script = tmp_path / "search_path_sentinel.py"
    script.write_text(SENTINEL, encoding="utf-8")
    command = owner.child_launch_command(sys.executable, script)
    result = run_bounded(command, input_bytes=b"", env=owner.child_environment(cpu_threads=4),
        timeout_seconds=60, stdout_cap_bytes=65536, stderr_cap_bytes=65536)
    assert dict(os.environ) == before
    info = json.loads(result["stdout"])
    assert info["isolated"] and info["safe_path"] and info["utf8_mode"]
    assert not info["user_site"]
    assert info["pythonpath_env"] is None
    assert info["poison_path_entries"] == []
    assert info["docling_origin"] is None or not Path(info["docling_origin"]).is_relative_to(poison)
    assert info["shadow_origin"] is None, "an injected shadow package reached the child"


def test_enhance_launches_through_isolated_owner_and_keeps_parent_env(monkeypatch, tmp_path):
    poison_parent_environment(monkeypatch, tmp_path)
    data, parsed = source()
    captured = {}

    def runner(command, **kwargs):
        captured.update(command=list(command), kwargs=kwargs)
        raise ValueError("captured launch observation")

    before = dict(os.environ)
    result = ParagraphEnhancement(config(), runner=runner).enhance(
        data, parsed, work_budget=WorkBudget(100000), deadline=None)
    assert dict(os.environ) == before
    assert Path(captured["command"][-1]).name == "_paragraph_worker.py"
    assert captured["command"][1:-1] == list(owner.CHILD_LAUNCH_FLAGS)
    assert captured["command"][0] == config().python
    env = captured["kwargs"]["env"]
    assert "PYTHONPATH" not in env and "PYTHONHOME" not in env and "PYTHONSTARTUP" not in env
    assert env["PYTHONNOUSERSITE"] == "1" and env["HF_HUB_OFFLINE"] == "1"
    assert Path(env["TEMP"]).name.startswith("cw-paragraph-")
    assert env["TEMP"] == env["TMP"] == env["TMPDIR"]
    assert result.layout_diagnostics[-1]["status"] == "native_fallback"
    assert result.layout_diagnostics[-1]["reason"] == "ValueError"


def test_worker_identity_stage_survives_isolated_flags_with_real_interpreter(tmp_path):
    """The real worker module starts under the owner's flags and fails only at
    the configured dependency check, proving first-party imports still bind."""
    request = {"schema_version": "pdf-paragraph-request/1", "pages": [1],
               "source_sha256": sha256(b"").hexdigest(), "pdf_base64": "",
               "runtime_versions": {"python": "0.0.0"},
               "environment_sha256": "0" * 64, "docling_version": "0.0.0",
               "max_memory_bytes": 4 * 1024**3,
               "max_output_bytes": 1, "max_seconds": 1, "cpu_threads": 1, "artifacts": str(tmp_path),
               "model_sha256": "0" * 64, "model_config_sha256": "0" * 64}
    script = owner.child_launch_command(sys.executable, Path(owner.__file__).with_name("_paragraph_worker.py"))
    with pytest.raises(Exception) as failure:
        run_bounded(script, input_bytes=json.dumps(request).encode(),
            env=owner.child_environment(cpu_threads=1), timeout_seconds=60,
            stdout_cap_bytes=65536, stderr_cap_bytes=65536)
    stderr = getattr(failure.value, "stderr", b"") or b""
    assert b"CWP_PARAGRAPH_STAGE=INPUT" in stderr
    assert b"CWP_PARAGRAPH_STAGE=IDENTITY" in stderr
