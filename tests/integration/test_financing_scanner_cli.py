"""Opt-in real financing PDF bytes through the public scanner, in a separate lake."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from integration import test_narrative_batch_cli_e2e as cli


protected_inputs = cli.r6_protected_inputs
REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(("sample_id", "kind"), [
    ("S05", "equity_offering_prospectus"),
    ("S06", "convertible_bond_prospectus"),
])
def test_real_financing_pdf_rescans_keep_raw_and_source_identity(
    tmp_path, protected_inputs, sample_id, kind,
):
    configured_root = os.environ.get("CWP_FINANCING_REAL_ROOT")
    if not configured_root:
        pytest.skip("explicit read-only company raw sample root required")
    samples = json.loads((REPO / "benchmarks/narrative_document_types/samples.json").read_text(encoding="utf-8"))
    sample = next(item for item in samples["samples"] if item["sample_id"] == sample_id)
    source = Path(configured_root).resolve() / sample["relative_path"]
    protected_inputs([source])
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == sample["sha256"]
    target = tmp_path / sample["relative_path"]
    target.parent.mkdir(parents=True)
    target.write_bytes(data)
    config = tmp_path / "config/catalog.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".source_catalog"),
        "roots": [{"root_id": "company_raw", "kind": "company_raw",
                   "path": str(tmp_path / "companies"), "priority": 10}]}), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(REPO / "src"), str(REPO / "scripts"))),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
    argv = [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(config),
            "register", "--root-id", "company_raw", "--relative-path", target.relative_to(tmp_path / "companies").as_posix()]
    database = tmp_path / ".source_catalog/catalog.sqlite3"
    identity = ("urn:company-wiki:document:sha256:" + sample["sha256"],
                "urn:company-wiki:source:sha256:" + sample["sha256"])
    for step in range(3):
        if step == 1:
            with sqlite3.connect(database) as connection:
                connection.execute("UPDATE documents SET document_kind='other',source_type='other' WHERE document_id=?",
                                   (identity[0],))
        result = subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True,
                                text=True, encoding="utf-8", timeout=40)
        assert result.returncode == 0, result.stderr
        with sqlite3.connect(database) as connection:
            row = connection.execute("SELECT document_id,primary_source_id,document_kind,source_type FROM documents").fetchone()
            assert row == (*identity, kind, "prospectus")
            assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM narrative_artifact_versions").fetchone()[0] == 0
        assert target.read_bytes() == data
