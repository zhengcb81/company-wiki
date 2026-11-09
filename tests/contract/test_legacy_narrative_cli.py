"""Keep the deployed RF command working across producer refactors."""

from __future__ import annotations

import builtins
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

from support.narrative_transport_fixture import published_fixture


_SRC = Path(__file__).resolve().parents[2] / "src"
_RF_DEFAULT = "company_wiki.source_catalog.narrative_transport_cli"
_CANONICAL = "company_wiki.automation.narrative_transport_cli"


def _run(module: str, config: Path, operation: str, request: dict, cwd: Path):
    env = dict(os.environ, PYTHONPATH=str(_SRC), PYTHON_DOTENV_DISABLED="1",
               COMPANY_WIKI_NETWORK="blocked")
    return subprocess.run(
        [sys.executable, "-B", "-m", module, "--config", str(config), "--operation", operation],
        cwd=cwd, env=env, input=json.dumps(request).encode("utf-8"),
        capture_output=True, timeout=30, check=False,
    )


def test_legacy_module_has_no_import_time_project_dependencies(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        assert not name.startswith("company_wiki"), name
        return original_import(name, globals, locals, fromlist, level)

    path = _SRC.joinpath(*_RF_DEFAULT.split(".")).with_suffix(".py")
    with monkeypatch.context() as scoped:
        scoped.setattr(builtins, "__import__", guarded_import)
        namespace = runpy.run_path(str(path))
    assert not {name for name in namespace if not name.startswith("_")}


def test_rf_default_narrative_command_preserves_bytes_and_receipts(tmp_path):
    unrelated = tmp_path / "unrelated working directory"
    unrelated.mkdir()
    with published_fixture(tmp_path) as fixture:
        database = fixture.catalog.store.database_path
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        request = {"schema_version": "narrative-reference-request/1",
                   "source_ref": fixture.source_ref.to_dict()}
        old = _run(_RF_DEFAULT, fixture.config_path, "reference", request, unrelated)
        new = _run(_CANONICAL, fixture.config_path, "reference", request, unrelated)
        assert old.returncode == new.returncode == 0, old.stderr
        assert old.stdout == new.stdout
        assert old.stderr == new.stderr
        reference = json.loads(old.stdout)
        assert json.loads(old.stderr)["narrative_ref"] == reference
        assert reference["artifact_sha256"] == hashlib.sha256(fixture.payload).hexdigest()

        request = {"schema_version": "narrative-read-request/1", "narrative_ref": reference,
                   "as_of_date": "2026-09-01", "expected_source": fixture.expected_source}
        old = _run(_RF_DEFAULT, fixture.config_path, "read", request, unrelated)
        new = _run(_CANONICAL, fixture.config_path, "read", request, unrelated)
        assert old.returncode == new.returncode == 0, old.stderr
        assert old.stdout == new.stdout == fixture.payload
        assert len(old.stderr.splitlines()) == len(new.stderr.splitlines()) == 1
        old_receipt, new_receipt = json.loads(old.stderr), json.loads(new.stderr)
        # The producer observes the current time once per successful open.
        for receipt in (old_receipt, new_receipt):
            read_at = datetime.fromisoformat(receipt.pop("read_at").replace("Z", "+00:00"))
            assert read_at.utcoffset() == timedelta(0)
        assert old_receipt == new_receipt
        assert old_receipt["replay_status"] == "verified"
        assert old_receipt["narrative_ref"] == reference
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert not list(unrelated.iterdir())
