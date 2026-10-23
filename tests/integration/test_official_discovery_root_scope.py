"""Actual local-pages CLI preserves source coverage and fixture bytes."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def declared(payload):
    return '<script type="application/ld+json">' + json.dumps(payload) + '</script>'


@pytest.mark.parametrize(("payload", "expected"), [
    ({"@type": "DigitalDocument", "contentUrl": "/report.pdf"}, "partial"),
    ({"@type": "Event", "name": "Investor Day"}, "checked_index_only"),
])
def test_public_local_pages_cli_preserves_embedded_coverage_without_writing_inputs(
    tmp_path, payload, expected,
):
    html = tmp_path / "index.html"
    html.write_text(declared(payload), encoding="utf-8")
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"schema_version": "official-discovery-request/1",
        "entity": "Neutral Holding", "start_date": "2026-01-01", "as_of_date": "2026-10-21",
        "pages": [{"input_file": str(html), "url": "https://neutral.example/ir",
                   "mime_type": "text/html", "capture_id": "root-cli-fixture"}]}), encoding="utf-8")
    sentinel = tmp_path / "preexisting-sentinel"
    sentinel.write_bytes(b"preserve fixture bytes")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    repo = Path(__file__).resolve().parents[2]
    run = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m",
        "company_wiki.source_catalog.official_source_cli", "--operation", "discover",
        "--request", str(request)], cwd=tmp_path, env={**os.environ,
        "PYTHONPATH": str(repo / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result["coverage_status"] == expected
    assert result["candidates"] == [] and result["no_documents_claimed"] is False
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
