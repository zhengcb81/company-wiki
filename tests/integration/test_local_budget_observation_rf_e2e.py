"""Real CWP -> installed FF -> installed RF local-budget failure, no provider."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
CWP = Path(os.environ.get("CWP_LOCAL_OBSERVATION_ROOT", str(ROOT)))
FF = Path(os.environ.get("FF_LOCAL_OBSERVATION_ROOT", str(ROOT.parent / "filing-fetch")))
RF = Path(os.environ.get("RF_LOCAL_OBSERVATION_ROOT", str(ROOT.parent / "revenue-forecast")))

SETUP = r'''
import json,sys
from pathlib import Path
from helpers.source_fact_fixture import lake,close
from contract.test_local_discovery_limits import groups
root=Path(sys.argv[1]);root.mkdir()
cat=lake(root,portfolio=True)
groups(cat,257)
for path in cat.config.roots[1].path.rglob('old.htm'): path.unlink()
close(cat)
(root/'config').mkdir()
(root/'config/source_catalog.yaml').write_text(
 'schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/catalog"\nroots:\n'
 '  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n'
 '  - root_id: provider\n    kind: dayu_portfolio\n    path: "${PROJECT_ROOT}/portfolio"\n'
 '    read_only: true\n    reusable_for_filing: true\n',encoding='utf-8')
(root/'connection.json').write_text(json.dumps({'schema_version':'1.0','company_wiki_root':str(root)}),encoding='utf-8')
'''


def test_actual_local_discovery_bound_reaches_rf_with_owner_measurements(tmp_path):
    if not (FF / "scripts/fetch_filing.py").is_file() or not (RF / "scripts/source_preparation.py").is_file():
        if "FF_LOCAL_OBSERVATION_ROOT" in os.environ or "RF_LOCAL_OBSERVATION_ROOT" in os.environ:
            pytest.fail("explicit FF/RF runtime root is missing")
        pytest.skip("cross-repository integration requires FF and RF checkouts or explicit runtime roots")
    assert (CWP / "tests/helpers/source_fact_fixture.py").is_file()
    wiki = tmp_path / "lake"
    guard = tmp_path / "offline"
    guard.mkdir()
    marker = tmp_path / "network-attempts.txt"
    (guard / "sitecustomize.py").write_text(
        "import socket\nfrom pathlib import Path\n"
        "def deny(*args,**kwargs):\n"
        f" Path({str(marker)!r}).write_text('unexpected network')\n"
        " raise AssertionError('offline integration attempted network')\n"
        "socket.create_connection=deny\nsocket.socket.connect=deny\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(guard), str(CWP / "src"), str(CWP / "tests"))),
        PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    prepared = subprocess.run([sys.executable, "-B", "-c", SETUP, str(wiki)],
        capture_output=True, timeout=30, env=env, cwd=tmp_path)
    assert prepared.returncode == 0, prepared.stderr.decode(errors="replace")
    request = {"schema_version": "2.0", "company_query": "ACME", "market": "US",
        "document_kind": "annual_report", "fiscal_year": 2026, "fiscal_period": "FY",
        "form_type": "10-K", "as_of_date": "2026-10-22", "filing_intent": "reuse_only"}
    command = [sys.executable, "-B", str(RF / "scripts/source_preparation.py"), "--result-envelope",
        "--company-wiki-catalog-config", str(wiki / "config/source_catalog.yaml"),
        "--company-wiki-config", str(wiki / "connection.json"), "--filing-fetch-root", str(FF),
        "--timeout-seconds", "30"]
    result = subprocess.run(command, input=json.dumps(request).encode(), capture_output=True,
        timeout=45, env=env, cwd=tmp_path)
    (tmp_path / "rf-error.json").write_bytes(result.stderr)
    assert result.returncode != 0 and not result.stdout, (result.returncode, result.stdout, result.stderr)
    error = json.loads(result.stderr)
    cause = error["upstream_cause"]
    assert cause["operation"] == "local_prepare" and cause["code"] == "local_source_group_limit", error
    assert cause["provider_started"] is False
    complete = error["filing_fetch_result"]
    observation = complete["local_preparation_observation"]
    assert observation["reason"] == cause["code"] and observation["local_io_usage"] is None
    rows = [row for row in observation["operations"] if row.get("operation") == "local_read_budget"]
    assert len(rows) == 1, observation
    owner = rows[0]
    assert owner["triggered_bound"] == "max_discovery_groups"
    assert owner["consumed"]["discovery_groups"] == owner["limits"]["max_discovery_groups"] + 1
    assert owner["consumed"]["observed_charge_bytes"] >= owner["consumed"]["charged_read_bytes"]
    assert owner["usage_scope"] == "local_original_verification"
    assert complete["downloads"] == 0 and not marker.exists()
    assert str(wiki) not in json.dumps(error)
