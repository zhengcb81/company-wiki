"""Real consumers calling the installed CWP wheel in an empty working directory."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import sysconfig

import pytest

from contract.test_installed_public_entrypoints import installed as installed_cwp  # noqa: F401 - pytest fixture
from support.narrative_transport_fixture import published_fixture


CONSUMER = """
import asyncio
import hashlib
import importlib.util
import sys
from pathlib import Path

dashboard, wiki, libraries, python, cwd, config, original, entity, expected_sha, output = sys.argv[1:]
# -S prevents this machine's globally installed editable packages from
# registering source checkouts. The test still uses the host's site packages
# for third-party dependencies, without executing their .pth files.
sys.path.insert(0, libraries)
sys.path.insert(0, dashboard)
sys.path.insert(0, wiki)

from fastapi.testclient import TestClient
from backend.dashboard.adapters.factory import build_ports
from backend.dashboard.transport.http import create_app
from stockwiki.dashboard_research_source_client import run_public

assert "company_wiki" not in sys.modules, "a consumer imported provider implementation"
assert importlib.util.find_spec("company_wiki") is None, "provider code on consumer path"
assert not (Path(cwd) / "src").exists()
key = "src_" + hashlib.sha1(str(Path(original).resolve()).encode()).hexdigest()[:16]
result = run_public(
    {"cwp_python": python, "cwp_root": cwd, "cwp_config": config},
    "company_wiki.source_catalog.public_legacy_source_link_cli",
    {"schema_version": "company-wiki-legacy-source-link-request/1", "legacy_source_id": key},
)
assert result.get("state") == "available", result.get("reason_codes")
assert result["current_byte_verification"]["content_sha256"] == expected_sha
ref = result["source_ref"]

ports = build_ports({"cwp_python": python, "cwp_root": cwd, "cwp_config": config}, mode="owner")
company = {"entity_id": entity, "listing_id": None, "analysis_subject_id": None,
           "resolution_status": "resolved", "display_name": "Acme"}

async def browse():
    page = await ports["source"].list_documents(company)
    assert page["snapshot"]["state"] == "available"
    row, = page["items"]
    assert row["source_ref"] == ref
    return row["document_version_id"]

version_id = asyncio.run(browse())
assert version_id == result["document_version_id"]
with TestClient(create_app(ports, Path(output), mode="owner", allow_test_origin=True)) as http:
    target = f"/api/v1/document-versions/{version_id}"
    original = http.get(target + "/original")
    assert original.status_code == 200, original.text[:900]
    assert hashlib.sha256(original.content).hexdigest() == expected_sha
    extraction = http.get(target + "/extraction")
    assert extraction.status_code == 200, extraction.text[:900]
    view = extraction.json()
    assert view["source_ref"] == ref
    assert view["summary"] and view["evidence"], view
    assert all(row["provenance"]["locator"]["value"] for row in view["evidence"])
"""


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.environ.get("MB_DASHBOARD_ROOT") or not os.environ.get("MB_STOCKWIKI_ROOT"),
    reason="run with the explicit Dashboard and StockWiki candidates for ROOT E08",
)
def test_installed_owner_services_stockwiki_and_dashboard(request, tmp_path):
    # Persist one summary via the real local DAG and a deterministic model.
    # The producer then runs from its wheel and the callers from a separate Python.
    entity = "ENT_11111111-2222-4333-8444-555555555555"
    installed = request.getfixturevalue("installed_cwp")
    deployment_roots = [
        Path(os.environ[name]).resolve(strict=True)
        for name in ("MB_DASHBOARD_ROOT", "MB_STOCKWIKI_ROOT")
    ]
    before = tuple(tmp_path.iterdir())
    with published_fixture(tmp_path, kind="pdf", source_spec={
        "sidecar_overrides": {"canonical_entity_id": entity, "fiscal_period": "FY"},
    }) as fixture:
        env = dict(os.environ, PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1")
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "-X", "utf8", "-c", CONSUMER,
             *(str(root) for root in deployment_roots), sysconfig.get_path("purelib"), str(installed["python"]),
             str(installed["cwd"]), str(fixture.config_path), str(fixture.raw_path), entity,
             fixture.source_ref.content_sha256, str(fixture.root / "dashboard")],
            cwd=installed["cwd"], env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=90, check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
    assert tuple(tmp_path.iterdir()) == before
