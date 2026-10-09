"""Run W03 checks with a fresh owned TEMP and preserve compact receipts."""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent


def run(name, arguments):
    parent = Path(tempfile.gettempdir()).resolve()
    owned = Path(tempfile.mkdtemp(prefix="w03f-", dir=parent)).resolve()
    protected = [
        ROOT / "config/source_catalog.yaml",
        ROOT / "config/source_acquisition.yaml",
    ]

    def snapshots():
        return {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            if p.exists()
            else None
            for p in protected
        }

    before = snapshots()
    command = (
        arguments[1:]
        if arguments and arguments[0] == "--exec"
        else [sys.executable, "-X", "utf8", "-B", *arguments]
    )
    environment = dict(
        os.environ,
        TEMP=str(owned),
        TMP=str(owned),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHON_DOTENV_DISABLED="1",
        RUFF_NO_CACHE="true",
        CWPA_W03_PROOF_FILE=str(PACKAGE / "flow-proof.json"),
    )
    started = time.monotonic()
    receipt = {
        "name": name,
        "command": command,
        "cwd": str(ROOT),
        "temp_root": str(owned),
        "temp_initial": "absent; created exclusively",
        "supplier_requests": 0,
        "protected_before": before,
    }
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
        receipt.update(
            exit_code=process.returncode,
            elapsed_seconds=round(time.monotonic() - started, 3),
        )
        (PACKAGE / (name + ".txt")).write_bytes(process.stdout)
        print(process.stdout.decode("utf-8", errors="replace"))
    except subprocess.TimeoutExpired as exc:
        receipt.update(
            exit_code="timeout", elapsed_seconds=round(time.monotonic() - started, 3)
        )
        (PACKAGE / (name + ".txt")).write_bytes(
            (exc.stdout or b"") + b"\nOWNER RUNNER TIMEOUT\n"
        )
        raise
    finally:
        receipt["protected_after"] = snapshots()
        assert receipt["protected_after"] == before, (
            "protected production configuration changed"
        )
        assert (
            owned.parent == parent
            and owned.name.startswith("w03f-")
            and not owned.is_symlink()
        )
        assert not any(p.is_symlink() for p in owned.rglob("*")), (
            "refuse symlink cleanup"
        )
        shutil.rmtree(owned)
        receipt["temp_final"] = "absent" if not owned.exists() else "cleanup_failed"
        (PACKAGE / (name + ".json")).write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1], sys.argv[2:]))
