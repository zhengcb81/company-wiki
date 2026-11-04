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
from typing import Any
from xml.etree import ElementTree

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
    "integration/filing_fetch/test_dropbox_policy_owner.py",
    "integration/filing_fetch/test_real_et_preflight.py",
    "integration/filing_fetch/test_runtime_config_loader.py",
    "integration/filing_fetch/test_transcript_original_roundtrip.py",
    "integration/test_transcript_budget_chain.py",
    "integration/test_public_protocol_compatibility.py",
    "integration/test_replaceable_readers.py",
)

D4_FINAL_TESTS = (
    "tests/unit/test_document_layer_isolation.py",
    "tests/unit/test_document_model_identity.py",
    "integration/stockwiki/test_d4_company_source_index.py",
    "integration/revenue_forecast/test_d4_rf_consumption.py",
    "integration/revenue_forecast/test_source_ref_v2_three_repo_e2e.py",
    "integration/filing_fetch/test_transcript_original_roundtrip.py",
    "integration/revenue_forecast_audit/test_current_public_bundle_import.py",
)
D4_MIN_CASES_BY_FILE = {
    "tests/unit/test_document_layer_isolation.py": 3,
    "tests/unit/test_document_model_identity.py": 18,
    "integration/stockwiki/test_d4_company_source_index.py": 1,
    "integration/revenue_forecast/test_d4_rf_consumption.py": 1,
    "integration/revenue_forecast/test_source_ref_v2_three_repo_e2e.py": 1,
    "integration/filing_fetch/test_transcript_original_roundtrip.py": 1,
    "integration/revenue_forecast_audit/test_current_public_bundle_import.py": 2,
}
D4_REQUIRED_CASES = (
    "integration.revenue_forecast_audit.test_current_public_bundle_import::test_frozen_public_bundle_v2_contract_reaches_audit_cli",
    "integration.revenue_forecast_audit.test_current_public_bundle_import::test_cwp_projected_public_read_v3_reaches_audit_cli_and_cleans_scratch",
)

CONSUMER_TEST_PREFIXES = {
    "rf": (
        "integration/revenue_forecast/",
        "integration/test_transcript_budget_chain.py",
        "integration/test_public_protocol_compatibility.py",
        "integration/test_replaceable_readers.py",
    ),
    "filing-fetch": ("integration/filing_fetch/", "integration/test_transcript_budget_chain.py"),
    "earnings-transcripts": (
        "integration/filing_fetch/test_transcript_original_roundtrip.py",
        "integration/filing_fetch/test_real_et_preflight.py",
        "integration/test_transcript_budget_chain.py",
    ),
    "stockwiki": ("integration/stockwiki/",),
    "audit": ("integration/revenue_forecast_audit/",),
}
CONSUMER_ROOTS = {
    "rf": "revenue-forecast",
    "filing-fetch": "filing-fetch",
    "earnings-transcripts": "earnings-transcripts",
    "stockwiki": "StockWiki",
    "audit": "revenue-forecast-audit",
}


def select_tests(requested: list[str] | None, *, d4_final: bool) -> list[str]:
    """Do not let a targeted override masquerade as the mandatory D4 suite."""
    if d4_final and requested:
        raise ValueError("--tests cannot replace the mandatory --d4-final suite")
    return list(requested or (D4_FINAL_TESTS if d4_final else CURRENT_TESTS))


def _selected_test_files(tests: list[str]) -> set[str]:
    selected: set[str] = set()
    project_root = ROOT.resolve(strict=True)
    for test in tests:
        raw_path = Path(test.split("::", 1)[0])
        candidate = raw_path if raw_path.is_absolute() else project_root / raw_path
        try:
            selected.add(candidate.resolve(strict=False).relative_to(project_root).as_posix())
        except ValueError:
            continue
    return selected


def consumer_scope(tests: list[str], roots: dict[str, Path]) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Report selected consumers without allowing traversal to match another lane."""
    selected = _selected_test_files(tests)
    consumers: list[str] = []
    coverage: dict[str, list[str]] = {}
    excluded: list[str] = []
    for consumer, patterns in CONSUMER_TEST_PREFIXES.items():
        root_name = CONSUMER_ROOTS[consumer]
        if root_name not in roots:
            excluded.append(f"{consumer}: no explicit {root_name} root; not run and not counted as pass")
            continue
        matched = sorted(
            path for path in selected
            if any(path == pattern or pattern.endswith("/") and path.startswith(pattern) for pattern in patterns)
        )
        if matched:
            consumers.append(consumer)
            coverage[consumer] = matched
        else:
            excluded.append(f"{consumer}: explicit root supplied but no matching test selected; not counted as pass")
    return consumers, coverage, excluded


def executed_consumer_scope(
    selected_coverage: dict[str, list[str]],
    module_counts: dict[str, dict[str, int]],
    roots: dict[str, Path],
    *,
    collect_only: bool,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    consumers: list[str] = []
    coverage: dict[str, list[str]] = {}
    excluded: list[str] = []
    for consumer, root_name in CONSUMER_ROOTS.items():
        if root_name not in roots:
            excluded.append(f"{consumer}: no explicit {root_name} root; not run and not counted as pass")
            continue
        selected_files = selected_coverage.get(consumer, [])
        if not selected_files:
            excluded.append(f"{consumer}: no matching test selected; not counted as pass")
            continue
        if collect_only:
            excluded.append(f"{consumer}: collection only; no tests executed and not counted as pass")
            continue
        executed_files = []
        unexecuted_files = []
        for file_path in selected_files:
            counts = _counts_for_file(file_path, module_counts)
            if counts["passed"] > 0:
                executed_files.append(file_path)
            else:
                unexecuted_files.append(file_path)
        if executed_files and not unexecuted_files:
            consumers.append(consumer)
            coverage[consumer] = executed_files
        else:
            excluded.append(
                f"{consumer}: selected files without a passing test case: {', '.join(unexecuted_files)}; not counted as pass"
            )
    return consumers, coverage, excluded


def _counts_for_file(file_path: str, module_counts: dict[str, dict[str, int]]) -> dict[str, int]:
    module = ".".join(Path(file_path).with_suffix("").parts)
    counts = [value for name, value in module_counts.items() if name == module or name.startswith(module + ".")]
    return {
        key: sum(item[key] for item in counts)
        for key in ("total", "skipped", "failed", "errors")
    } | {"passed": sum(item["total"] - item["skipped"] - item["failed"] - item["errors"] for item in counts)}


def junit_counts(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"total": 0, "skipped": 0, "failed": 0, "errors": 0, "by_module": {}}
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as exc:
        return {"total": 0, "skipped": 0, "failed": 0, "errors": 1, "by_module": {}, "parse_error": str(exc)}
    cases = root.findall(".//testcase")
    by_module: dict[str, dict[str, int]] = {}
    for case in cases:
        module = case.attrib.get("classname", "")
        counts = by_module.setdefault(module, {"total": 0, "skipped": 0, "failed": 0, "errors": 0})
        counts["total"] += 1
        counts["skipped"] += case.find("skipped") is not None
        counts["failed"] += case.find("failure") is not None
        counts["errors"] += case.find("error") is not None
    return {
        "total": len(cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
        "failed": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "by_module": by_module,
        "nodeids": sorted(
            f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}" for case in cases
        ),
    }


def code_version(root: Path) -> dict:
    """Bind tracked source state without recording configs, keys or run artifacts."""
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args],
            capture_output=True, check=True, timeout=15)
        return result.stdout
    paths = ("src", "scripts", "stockwiki", "skills", "tests", "tools", "integration", "references",
        ".github", ".ruff.toml", "mypy.ini", "pytest.ini", "pyproject.toml", "setup.cfg",
        "SKILL.md", "CHANGELOG.md")
    tracked_root_python = [
        path for path in git("ls-files", "-z", "--", "*.py").decode("utf-8").split("\0")
        if path and "/" not in path
    ]
    paths = (*paths, *tracked_root_python)
    new_paths = git("ls-files", "--others", "--exclude-standard", "-z", "--", *paths).decode("utf-8").split("\0")
    untracked_root_python = [
        path for path in git("ls-files", "--others", "--exclude-standard", "-z", "--", "*.py").decode("utf-8").split("\0")
        if path and "/" not in path
    ]
    new_paths = list(dict.fromkeys([*new_paths, *untracked_root_python]))
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
    if "revenue-forecast-audit" in roots:
        env["AUDIT_CODE_ROOT"] = str(roots["revenue-forecast-audit"])
    else:
        env.pop("AUDIT_CODE_ROOT", None)
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-root", type=Path, required=True)
    parser.add_argument("--ff-root", type=Path, required=True)
    parser.add_argument("--et-root", type=Path, required=True)
    parser.add_argument("--stockwiki-root", type=Path)
    parser.add_argument("--audit-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=240)
    parser.add_argument("--tests", nargs="+", help="Targeted follow-up; default is the current public chain")
    parser.add_argument("--d4-final", action="store_true",
        help="Run the one-time D4 closeout set; requires explicit --stockwiki-root and --audit-root")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        tests = select_tests(args.tests, d4_final=args.d4_final)
    except ValueError as exc:
        parser.error(str(exc))
    if args.d4_final and (args.stockwiki_root is None or args.audit_root is None):
        parser.error("--d4-final requires explicit --stockwiki-root and --audit-root; absent consumers are not counted as passes")
    if args.d4_final and args.collect_only:
        parser.error("--collect-only cannot be used for the mandatory --d4-final acceptance run")
    roots = {"company-wiki": ROOT, "revenue-forecast": args.rf_root.resolve(strict=True),
        "filing-fetch": args.ff_root.resolve(strict=True), "earnings-transcripts": args.et_root.resolve(strict=True)}
    if args.stockwiki_root is not None:
        roots["StockWiki"] = args.stockwiki_root.resolve(strict=True)
    if args.audit_root is not None:
        roots["revenue-forecast-audit"] = args.audit_root.resolve(strict=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    consumers, consumer_test_coverage, excluded_consumers = consumer_scope(tests, roots)
    initial_versions = {name: code_version(root) for name, root in roots.items()}
    record = {"schema_version": "source-system-check/1", "started_at": datetime.now(timezone.utc).isoformat(),
        "versions": initial_versions,
        "tests": tests, "selected_consumers": consumers,
        "selected_consumer_test_files": consumer_test_coverage,
        "consumers": [], "consumer_test_coverage": {}, "excluded_consumers": [],
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
    test_counts = junit_counts(output / "junit.xml")
    executed_consumers, executed_coverage, executed_excluded = executed_consumer_scope(
        consumer_test_coverage, test_counts["by_module"], roots, collect_only=args.collect_only
    )
    record.update(consumers=executed_consumers, consumer_test_coverage=executed_coverage,
        excluded_consumers=executed_excluded)
    d4_consumers = {"rf", "filing-fetch", "earnings-transcripts", "stockwiki", "audit"}
    d4_file_counts = {
        file_path: _counts_for_file(file_path, test_counts["by_module"])
        for file_path in D4_FINAL_TESTS
    } if args.d4_final else {}
    undercovered_d4_files = [
        file_path for file_path, minimum in D4_MIN_CASES_BY_FILE.items()
        if d4_file_counts[file_path]["passed"] < minimum
    ] if args.d4_final else []
    missing_d4_cases = sorted(set(D4_REQUIRED_CASES) - set(test_counts.get("nodeids", []))) if args.d4_final else []
    if args.d4_final and (
        test_counts["total"] == 0
        or test_counts["skipped"] > 0
        or not d4_consumers.issubset(executed_consumers)
        or undercovered_d4_files
        or missing_d4_cases
    ):
        rc = 1
        record["failure"] = {
            "kind": "IncompleteD4Suite",
            "message": "mandatory D4 acceptance requires every required file and case to pass with zero skips",
            "undercovered_files": undercovered_d4_files,
            "missing_cases": missing_d4_cases,
        }
    final_versions = {name: code_version(root) for name, root in roots.items()}
    stable_during_run = initial_versions == final_versions
    record.update(returncode=rc if stable_during_run else 1,
        seconds=round(time.monotonic()-started, 3), scratch_restored=not Path(temporary).exists(),
        test_counts=test_counts,
        d4_file_counts=d4_file_counts,
        versions_after=final_versions, source_stable_during_run=stable_during_run)
    if not stable_during_run:
        record["failure"] = {"kind": "SourceChangedDuringRun", "message": "one or more code snapshots changed while the suite was running"}
    (output / "pytest.log").write_bytes(stdout + b"\n" + stderr)
    (output / "report.json").write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(stdout.decode("utf-8", errors="replace"))
    if stderr:
        print(stderr.decode("utf-8", errors="replace"), file=sys.stderr)
    print(json.dumps({"returncode": rc, "scratch_restored": record["scratch_restored"],
        "seconds": record["seconds"]}))
    return int(record["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
