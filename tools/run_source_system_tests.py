"""ROOT-owned offline public source-system integration; no per-commit multi-repo gate.

Each checkout is selected explicitly. Provider HTTP is replaced by test fixtures.
All lake state and subprocess caches live in one removed TemporaryDirectory.
The report records participating code versions and the actual cleanup result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from company_wiki._bounded_process import TransportError, run_bounded  # noqa: E402

CURRENT_TESTS = (
    "integration/revenue_forecast/test_p5_source_default_cli_e2e.py",
    "integration/revenue_forecast/test_source_ref_v2_three_repo_e2e.py",
    "integration/revenue_forecast/test_consumer_ci_migration.py",
    "integration/revenue_forecast/test_registered_source_boundary.py",
    "integration/revenue_forecast/test_m3_acquisition_usage_e2e.py",
    "integration/filing_fetch/test_source_ref_v2_cli.py",
    "integration/filing_fetch/test_real_source_query.py",
    "integration/filing_fetch/test_real_et_preflight.py",
    "integration/filing_fetch/test_runtime_config_loader.py",
    "integration/filing_fetch/test_transcript_original_roundtrip.py",
    "integration/test_transcript_budget_chain.py",
    "integration/test_public_protocol_compatibility.py",
    "integration/test_replaceable_readers.py",
)


def code_version(root: Path) -> dict:
    """Bind tracked source state without recording configs, keys or run artifacts."""
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args],
            capture_output=True, check=True, timeout=15)
        return result.stdout
    paths = ("src", "scripts", "stockwiki", "skills", "tests", "tools", "integration", "references",
        ".github", ".ruff.toml", "mypy.ini", "pytest.ini", "pyproject.toml", "setup.cfg",
        "SKILL.md", "CHANGELOG.md")
    new_paths = git("ls-files", "--others", "--exclude-standard", "-z", "--", *paths).decode("utf-8").split("\0")
    new = {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in new_paths if path and (root / path).is_file()}
    return {
        "head": git("rev-parse", "HEAD").decode().strip(),
        "tracked_diff_sha256": hashlib.sha256(git("diff", "--binary", "HEAD", "--", *paths)).hexdigest(),
        "new_files": new,
    }


def environment(roots: dict[str, Path], scratch: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
        if not (key.upper().endswith(("API_KEY", "API_KEY_FILE")) or key.startswith("GIT_"))}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHON_DOTENV_DISABLED="1",
        COMPANY_WIKI_NETWORK="blocked", COMPANY_WIKI_REAL_LLM="0",
        CWP_V2_CODE_ROOT=str(roots["company-wiki"]), RF_CODE_ROOT=str(roots["revenue-forecast"]),
        FF_V2_CODE_ROOT=str(roots["filing-fetch"]), ET_CODE_ROOT=str(roots["earnings-transcripts"]),
        FILING_FETCH_V2_WIKI_SRC=str(roots["company-wiki"] / "src"),
        PYTHONPATH=str(roots["company-wiki"] / "src"),
        TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch),
        HTTP_PROXY="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9", NO_PROXY="127.0.0.1,localhost")
    if "StockWiki" in roots:
        env["STOCKWIKI_CODE_ROOT"] = str(roots["StockWiki"])
    else:
        env.pop("STOCKWIKI_CODE_ROOT", None)
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-root", type=Path, required=True)
    parser.add_argument("--ff-root", type=Path, required=True)
    parser.add_argument("--et-root", type=Path, required=True)
    parser.add_argument("--stockwiki-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=240)
    parser.add_argument("--tests", nargs="+", help="Targeted follow-up; default is the current public chain")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args(argv)
    roots = {"company-wiki": ROOT, "revenue-forecast": args.rf_root.resolve(strict=True),
        "filing-fetch": args.ff_root.resolve(strict=True), "earnings-transcripts": args.et_root.resolve(strict=True)}
    if args.stockwiki_root is not None:
        roots["StockWiki"] = args.stockwiki_root.resolve(strict=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    tests = list(args.tests or CURRENT_TESTS)
    record = {"schema_version": "source-system-check/1", "started_at": datetime.now(timezone.utc).isoformat(),
        "versions": {name: code_version(root) for name, root in roots.items()},
        "tests": tests, "consumers": ["rf", *(["stock"] if "StockWiki" in roots else [])],
        "provider_mode": "offline fixtures and loopback only", "collect_only": args.collect_only}
    started = time.monotonic()
    stdout = stderr = b""
    rc = 1
    # Keep Windows basetemp below the existing relocation threshold. Nesting a
    # long TEMP under another fallback would otherwise lengthen source paths.
    with tempfile.TemporaryDirectory(prefix="cw-") as temporary:
        scratch = Path(temporary)
        command = [sys.executable, "-B", "-m", "pytest", *tests,
            "-q", "--tb=short", "-p", "no:cacheprovider", "-o", "addopts=",
            "--basetemp", str(scratch / "pytest"), "--junitxml", str(output / "junit.xml")]
        if args.collect_only:
            command.append("--collect-only")
        try:
            result = run_bounded(command, cwd=str(ROOT), env=environment(roots, scratch),
                timeout_seconds=args.timeout_seconds, stdout_cap_bytes=None,
                stderr_cap_bytes=1024 * 1024, stderr_log_tail=True)
            stdout, stderr = result["stdout"], result["stderr"]
            rc = int(result["returncode"])
        except TransportError as exc:
            stdout, stderr = getattr(exc, "stdout", b""), getattr(exc, "stderr", b"")
            rc = int(getattr(exc, "returncode", 1) or 1)
            record["failure"] = {"kind": type(exc).__name__, "message": str(exc)}
    record.update(returncode=rc, seconds=round(time.monotonic()-started, 3),
        scratch_restored=not Path(temporary).exists())
    (output / "pytest.log").write_bytes(stdout + b"\n" + stderr)
    (output / "report.json").write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(stdout.decode("utf-8", errors="replace"))
    if stderr:
        print(stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    print(json.dumps({"returncode": rc, "scratch_restored": record["scratch_restored"],
        "seconds": record["seconds"]}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
