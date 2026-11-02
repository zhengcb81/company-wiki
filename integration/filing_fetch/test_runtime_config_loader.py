import importlib.util
import json
from pathlib import Path
import pytest
import fetch_filing
ROOT = Path(__file__).resolve().parent

def _configured_runtime(tmp_path):
    wiki = tmp_path / "configured-wiki"
    (wiki / "config").mkdir(parents=True)
    (wiki / "config/source_catalog.yaml").write_text("schema_version: '1.0'\n", encoding="utf-8")
    project = tmp_path / "filing-project"
    (project / "config").mkdir(parents=True)
    config = project / "config/company_wiki.json"
    config.write_text(json.dumps({"schema_version": "1.0", "company_wiki_root": str(wiki)}),
        encoding="utf-8")
    return project, wiki, config
def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / "test_source_ref_v2_cli.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def test_v2_e2e_uses_public_loader_without_an_opt_in_environment(monkeypatch, tmp_path):
    e2e = _load("ff_v2_public_root", "e2e/test_source_ref_v2_cli.py")
    _project, wiki, _config = _configured_runtime(tmp_path)
    cli = wiki / "src" / "company_wiki" / "source_catalog" / "cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("pass\n", encoding="utf-8")
    monkeypatch.delenv("FILING_FETCH_V2_WIKI_SRC", raising=False)
    loaded = []
    monkeypatch.setattr(fetch_filing, "load_company_wiki_root", lambda: loaded.append(1) or wiki)
    try:
        environment = e2e._environment()
    except pytest.skip.Exception:
        pytest.fail("configured offline v2 E2E was silently skipped")
    assert loaded == [1]
    assert environment["PYTHONPATH"] == str((wiki / "src").resolve())
