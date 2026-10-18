"""Manual acceptance demo for the P3 identity audit (card section 5.1).

Builds a synthetic sidecar catalog under %TEMP%, snapshots every file
(sha256 + size + mtime_ns), runs ``python -m tools.identity_audit`` with
``--out --pretty``, snapshots again and proves nothing changed except the
documented ``--out`` receipt.  No production config, catalog or original is
opened.  Run: ``python demo-cli-run.py`` from this directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = CARD_DIR.parents[3]
sys.path.insert(0, str(REPO_ROOT / "tests" / "unit" / "test_identity_audit"))
sys.path.insert(0, str(REPO_ROOT / "tests" / "unit" / "test_identity_audit" / "fixtures"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from fixtures.sidecar_catalog import build_fixture, request_payload  # noqa: E402


def snapshot(root: Path) -> dict[str, tuple[str, int, int]]:
    state: dict[str, tuple[str, int, int]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        state[
            str(path.relative_to(root)).replace("\\", "/")
        ] = (
            hashlib.sha256(data).hexdigest(),
            len(data),
            path.stat().st_mtime_ns,
        )
    return state


def main() -> int:
    demo_root = Path(tempfile.mkdtemp(prefix="p3-identity-audit-demo-"))
    fixture = build_fixture(demo_root, capture=True)
    try:
        request_path = demo_root / "request.json"
        request_path.write_text(
            json.dumps(
                request_payload(
                    refs=[fixture.ref_payload()],
                    expect={"market": "CN", "security_id": "688012", "fiscal_year": 2026},
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        out_path = CARD_DIR / "receipt.json"
        if out_path.exists():
            out_path.unlink()

        before = snapshot(demo_root)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(REPO_ROOT / "src")
        environment["PYTHONIOENCODING"] = "utf-8"
        stdout_path = demo_root / "cli-stdout.txt"
        stderr_path = demo_root / "cli-stderr.txt"
        with stdout_path.open("wb") as stdout_stream, stderr_path.open("wb") as stderr_stream:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "tools.identity_audit",
                    "--config",
                    str(fixture.config_path),
                    "--request",
                    str(request_path),
                    "--out",
                    str(out_path),
                    "--pretty",
                ],
                stdout=stdout_stream,
                stderr=stderr_stream,
                cwd=str(REPO_ROOT),
                env=environment,
                check=False,
            )
        after = snapshot(demo_root)
        changed = {
            key
            for key in set(before) | set(after)
            if before.get(key) != after.get(key)
            and not key.startswith("cli-")  # this demo's own redirection files
        }
        assert changed == set(), f"synthetic tree changed: {sorted(changed)}"

        line = stdout_path.read_bytes().decode("utf-8")
        receipt = json.loads(line)
        assert line.endswith("\n") and line.count("\n") == 1
        assert receipt["schema_version"] == "identity-audit-receipt/1"
        pretty = json.loads(out_path.read_text(encoding="utf-8"))
        assert pretty == receipt, "--out copy must be content-equivalent"
        counts = receipt["counts"]
        print(f"exit={completed.returncode} status={receipt['status']}")
        print(
            "counts="
            + json.dumps(
                {key: counts[key] for key in sorted(counts)},
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        print(f"inputs={sorted(receipt['inputs'])}")
        print(f"out={out_path}")
        return 0
    finally:
        fixture.catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
