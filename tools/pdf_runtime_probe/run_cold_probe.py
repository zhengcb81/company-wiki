"""Single-attempt bounded no-document cold observation (W21 revision).

Launches the probe child with the production launch owner's flags and
sanitized environment against the already-deployed isolated interpreter.
Receipts land in the card-owned plan receipts directory; the ROOT c3-20261028
receipts and its single-cold-attempt marker stay untouched. One attempt per
revision: a rerun requires a new revision after diagnosing a failure, never a
raised limit.
"""
from __future__ import annotations

from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
import json
import shutil
import sys
import tempfile
import time

WORKTREE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE / "src"))

from company_wiki._bounded_process import TransportError, run_bounded  # noqa: E402
from company_wiki.source_catalog.narrative_pdf_enhancement import (  # noqa: E402
    CHILD_LAUNCH_FLAGS, child_environment)

REVISION = "rev1"
PROFILE_RELATIVE = "ROOT/.planning/c3-20261028/pdf-sdk-isolated/runtime-isolated.json"
CPU_THREADS = 4
DOCUMENT_TIMEOUT_SECONDS = 120


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path,
        default=Path.home() / "Projects" / "company-wiki" / ".planning" / "c3-20261028"
                / "pdf-sdk-isolated" / "runtime-isolated.json")
    parser.add_argument("--deadline", type=float, default=30)
    parser.add_argument("--receipts-dir", type=Path,
        default=WORKTREE / "docs" / "plans" / "w21-pdf-runtime-2026-10-29" / "receipts")
    arguments = parser.parse_args()

    profile_path = arguments.profile
    profile = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    for key in ("python", "artifacts", "max_memory_bytes", "environment_sha256", "docling_version"):
        if key not in profile:
            raise SystemExit(f"profile is missing {key!r}")
    receipts = arguments.receipts_dir
    receipts.mkdir(parents=True, exist_ok=True)
    probe = Path(__file__).with_name("cold_runtime_probe.py")
    controller = Path(__file__)
    receipt_path = receipts / f"cold-{REVISION}.json"
    marker_path = receipts / f"cold-{REVISION}.marker.json"
    if receipt_path.exists() or marker_path.exists():
        raise SystemExit(f"revision {REVISION} already attempted; a rerun needs a diagnosed new revision")

    fingerprint = {"revision": REVISION, "attempts": 1, "deadline_seconds": arguments.deadline,
        "profile_relative": PROFILE_RELATIVE,
        "profile_sha256": sha256(profile_path.read_bytes()).hexdigest(),
        "probe_sha256": sha256(probe.read_bytes()).hexdigest(),
        "controller_sha256": sha256(controller.read_bytes()).hexdigest()}
    marker_path.write_text(json.dumps(fingerprint, indent=2), encoding="utf-8")

    scratch = Path(tempfile.mkdtemp(prefix="cw-w21-cold-"))
    environment = child_environment(cpu_threads=CPU_THREADS)
    environment.update(TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch),
        HF_HOME=str(scratch / "hf"), XDG_CACHE_HOME=str(scratch / "cache"))
    command = [profile["python"], *CHILD_LAUNCH_FLAGS, str(probe)]
    request = {"artifacts": profile["artifacts"], "max_memory_bytes": profile["max_memory_bytes"],
               "temp": str(scratch), "document_timeout": DOCUMENT_TIMEOUT_SECONDS, "cpu_threads": CPU_THREADS}
    started = time.monotonic()
    receipt = {**fingerprint, "pdf_bytes": 0, "sdk_model_copies": 0, "cpu_threads": CPU_THREADS,
        "memory_bytes": profile["max_memory_bytes"],
        "environment_sha256": profile["environment_sha256"],
        "docling_version": profile["docling_version"],
        "launch_flags": list(CHILD_LAUNCH_FLAGS), "audit_scope": "python_audit_events_only",
        "status": None, "returncode": None, "seconds": None, "events": [],
        "stdout_sha256": None, "stderr_sha256": None, "done_no_document": False,
        "guard_rejections": None, "scratch_restored_absent": False}
    stdout = stderr = b""
    try:
        response = run_bounded(command, input_bytes=json.dumps(request).encode(), env=environment,
            timeout_seconds=arguments.deadline, stdout_cap_bytes=2 * 1024 * 1024, stderr_cap_bytes=65536)
        stdout, stderr = response["stdout"], response["stderr"]
        receipt.update(status="completed", returncode=0)
    except TransportError as failure:
        stdout, stderr = getattr(failure, "stdout", b""), getattr(failure, "stderr", b"")
        receipt.update(status=type(failure).__name__, returncode=getattr(failure, "returncode", None))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        receipt["scratch_restored_absent"] = not scratch.exists()
        receipt["seconds"] = round(time.monotonic() - started, 6)
    (receipts / f"cold-{REVISION}.stdout.jsonl").write_bytes(stdout)
    (receipts / f"cold-{REVISION}.stderr.log").write_bytes(stderr)
    events = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    receipt.update(events=events,
        stdout_sha256=sha256(stdout).hexdigest(), stderr_sha256=sha256(stderr).hexdigest(),
        done_no_document=any(row.get("stage") == "DONE" and row.get("active") == "DONE_NO_DOCUMENT"
                             for row in events),
        guard_rejections=sum(row.get("stage") == "GUARD_REJECTED" for row in events))
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
