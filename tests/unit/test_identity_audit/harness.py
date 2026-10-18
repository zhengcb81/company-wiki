"""Import guard and process helpers for the P3 identity-audit lane.

The lane's production modules live in ``tools/identity_audit``.  Before they
exist every test that needs them routes through :func:`require`, so the RED
evidence shows an explicit ``AssertionError`` naming the missing module rather
than a bare ``ImportError``.

Lane write set: ``tools/identity_audit/``, ``tests/unit/test_identity_audit/``
and this card's plan directory.  No other card and no other test module is
imported here.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src"
LANE_DIR = Path(__file__).resolve().parent

for _path in (str(REPO_ROOT), str(SRC_DIR), str(LANE_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

EXPORT_V2_MODULE = "company_wiki.source_catalog.source_export_v2_cli"
SOURCE_REF_SCHEMA_VERSION = "2.0"


def require(module_name: str) -> Any:
    """Import a lane module, failing the calling test with a named assertion."""
    try:
        return importlib.import_module(module_name)
    except Exception as exc:  # RED phase: the module does not exist yet.
        raise AssertionError(
            f"{module_name} is not implemented yet ({type(exc).__name__}: {exc})"
        ) from exc


def audit_core() -> Any:
    return require("tools.identity_audit.core")


def audit_cli() -> Any:
    return require("tools.identity_audit.cli")


def audit_receipt() -> Any:
    return require("tools.identity_audit.receipt")


def audit_export() -> Any:
    return require("tools.identity_audit.export")


def audit_package() -> Any:
    return require("tools.identity_audit")


def _child_env() -> dict[str, str]:
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH", "")
    parts = [str(SRC_DIR)] + [item for item in existing.split(os.pathsep) if item]
    environment["PYTHONPATH"] = os.pathsep.join(parts)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment.pop("PYTHONDOTENV", None)
    return environment


def run_module(
    module: str,
    args: Iterable[str],
    *,
    stdin_path: Path,
    out_dir: Path,
    stdout_name: str = "child.out",
    stderr_name: str = "child.err",
) -> tuple[int, bytes, bytes]:
    """Run a frozen CLI in this interpreter with file redirection.

    Output is redirected to files rather than pipes: this environment refuses
    piped stdio capture for child processes, and a real file keeps the child's
    exact bytes for the field-by-field comparison.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = out_dir / stdout_name
    stderr_path = out_dir / stderr_name
    command = [sys.executable, "-B", "-m", module, *args]
    with stdin_path.open("rb") as stdin_stream, stdout_path.open(
        "wb"
    ) as stdout_stream, stderr_path.open("wb") as stderr_stream:
        completed = subprocess.run(
            command,
            stdin=stdin_stream,
            stdout=stdout_stream,
            stderr=stderr_stream,
            cwd=str(REPO_ROOT),
            env=_child_env(),
            check=False,
        )
    return (
        int(completed.returncode),
        stdout_path.read_bytes(),
        stderr_path.read_bytes(),
    )


def run_export_v2(config_path: Path, request_path: Path, out_dir: Path) -> dict[str, Any]:
    code, stdout, stderr = run_module(
        EXPORT_V2_MODULE,
        ["--config", str(config_path)],
        stdin_path=request_path,
        out_dir=out_dir,
    )
    assert code == 0, f"export v2 exited {code}: {stderr[:400]!r}"
    return json.loads(stdout.decode("utf-8"))


def write_json(path: Path, payload: Any) -> Path:
    """Write a request/receipt JSON file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def sole_source(receipt: dict[str, Any]) -> dict[str, Any]:
    sources = receipt["sources"]
    assert isinstance(sources, list) and len(sources) == 1, (
        f"expected exactly one audited source, got {len(sources)}"
    )
    return sources[0]


def checks_of(receipt: dict[str, Any]) -> dict[str, Any]:
    return sole_source(receipt)["checks"]


__all__ = [
    "EXPORT_V2_MODULE",
    "LANE_DIR",
    "REPO_ROOT",
    "SOURCE_REF_SCHEMA_VERSION",
    "SRC_DIR",
    "audit_cli",
    "audit_core",
    "audit_export",
    "audit_package",
    "audit_receipt",
    "checks_of",
    "require",
    "run_export_v2",
    "run_module",
    "sole_source",
    "write_json",
]
