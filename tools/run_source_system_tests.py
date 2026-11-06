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
D5_FF_ROUTE_TESTS = (
    "integration/filing_fetch/test_source_ref_v2_cli.py",
)
D5_FF_ROUTE_REQUIRED_CASES = (
    "test_schema_2_0_defaults_to_v2_and_never_uses_legacy_handle_validation",
    "test_schema_1_1_keeps_legacy_path_handle_in_its_explicit_route",
)
D5_FINAL_TEST_FILES = {
    "cwp_contract": "tests/contract/test_processed_document_cli.py",
    "stockwiki_e2e": "tests/e2e/test_cwp_processed_document.py",
    "real_sample_e2e": "integration/stockwiki/test_d5_real_sample_e2e.py",
    "ff_route": D5_FF_ROUTE_TESTS[0],
}
D5_FINAL_REQUIRED_CASES = (
    "test_processed_document_port_serves_three_stockwiki_entries",
    "test_real_sample_uses_processed_port_and_preserves_original",
    *D5_FF_ROUTE_REQUIRED_CASES,
)
D5_STOCKWIKI_TRANSPORT_CONFIG = "config/cwp_source_index.transport.json"

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


def select_tests(
    requested: list[str] | None,
    *,
    d4_final: bool = False,
    d5_ff_route: bool = False,
    d5_final: bool = False,
    d5_cwp_root: Path | None = None,
    stockwiki_root: Path | None = None,
) -> list[str]:
    """Keep named ROOT acceptance suites mandatory and independently selectable."""
    selected_modes = sum((d4_final, d5_ff_route, d5_final))
    if selected_modes > 1:
        raise ValueError("--d4-final, --d5-ff-route, and --d5-final cannot combine")
    if d5_final:
        if d5_cwp_root is None or stockwiki_root is None:
            raise ValueError("--d5-final requires explicit D5 CWP and StockWiki roots")
        cwp_root = Path(d5_cwp_root).resolve()
        sw_root = Path(stockwiki_root).resolve()
        mandatory_suite = [
            str(cwp_root / D5_FINAL_TEST_FILES["cwp_contract"]),
            str(sw_root / D5_FINAL_TEST_FILES["stockwiki_e2e"]),
            D5_FINAL_TEST_FILES["real_sample_e2e"],
            D5_FINAL_TEST_FILES["ff_route"],
        ]
    else:
        mandatory_suite = D4_FINAL_TESTS if d4_final else D5_FF_ROUTE_TESTS if d5_ff_route else None
    if mandatory_suite is not None and requested:
        raise ValueError("--tests cannot replace the mandatory ROOT acceptance suite")
    return list(requested or mandatory_suite or CURRENT_TESTS)


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
    if not counts and Path(file_path).is_absolute():
        # Pytest's classname for an absolute test file outside ROOT varies with
        # its chosen common root.  The D5 candidate files have unique basenames,
        # so a module-suffix match accounts for them without path heuristics.
        suffix = Path(file_path).stem
        counts = [
            value for name, value in module_counts.items()
            if name == suffix or name.endswith("." + suffix)
        ]
    return {
        key: sum(item[key] for item in counts)
        for key in ("total", "skipped", "failed", "errors")
    } | {"passed": sum(item["total"] - item["skipped"] - item["failed"] - item["errors"] for item in counts)}


def _counts_for_case_names(case_names: tuple[str, ...], test_counts: dict[str, Any]) -> dict[str, int]:
    selected = [
        node_id for node_id in test_counts.get("nodeids", [])
        if any(node_id.endswith("::" + case_name) for case_name in case_names)
    ]
    total = len(selected)
    failed_or_skipped = bool(
        test_counts.get("failed") or test_counts.get("errors") or test_counts.get("skipped")
    )
    return {
        "total": total,
        "skipped": 0,
        "failed": int(failed_or_skipped),
        "errors": 0,
        "passed": total if total and not failed_or_skipped else 0,
    }


def _attribute_d5_consumers(
    executed_consumers: list[str],
    executed_coverage: dict[str, list[str]],
    executed_excluded: list[str],
    file_counts: dict[str, dict[str, int]],
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Attribute the two D5 downstream domains from their required E2E cases."""
    consumers = list(executed_consumers)
    coverage = dict(executed_coverage)
    excluded = list(executed_excluded)
    expected = {
        "real_sample_e2e": ("stockwiki", D5_FINAL_TEST_FILES["real_sample_e2e"]),
        "ff_route": ("filing-fetch", D5_FINAL_TEST_FILES["ff_route"]),
    }
    for file_label, (consumer, file_path) in expected.items():
        if file_counts.get(file_label, {}).get("passed", 0) <= 0:
            continue
        if consumer not in consumers:
            consumers.append(consumer)
        coverage[consumer] = [file_path]
        excluded = [item for item in excluded if not item.startswith(consumer + ":")]
    return consumers, coverage, excluded


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


def code_version(root: Path, *, extra_paths: tuple[str, ...] = ()) -> dict:
    """Bind selected source paths, with optional explicit nonsecret contract config."""
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args],
            capture_output=True, check=True, timeout=15)
        return result.stdout
    paths = ("src", "scripts", "stockwiki", "skills", "tests", "tools", "integration", "references",
        ".github", ".ruff.toml", "mypy.ini", "pytest.ini", "pyproject.toml", "setup.cfg",
        "SKILL.md", "CHANGELOG.md", *extra_paths)
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


def git_worktree_status(root: Path) -> list[str]:
    """Return all visible tracked/untracked worktree changes without touching Git state."""
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True, check=True, timeout=30,
    )
    return [line for line in result.stdout.decode("utf-8", "replace").splitlines() if line]


def git_file_blob_at_commit(root: Path, commit: str, path: str) -> str:
    """Return a committed file's object ID, independent of checkout line endings."""
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", f"{commit}:{path}"],
        capture_output=True, check=True, timeout=30,
    ).stdout.decode("ascii").strip()


def git_working_file_blob(root: Path, path: str) -> str:
    """Hash working bytes through Git's clean filters without writing an object."""
    return subprocess.run(
        ["git", "-C", str(root), "hash-object", f"--path={path}", "--stdin"],
        input=(root / path).read_bytes(), capture_output=True, check=True, timeout=30,
    ).stdout.decode("ascii").strip()


def environment(
    roots: dict[str, Path],
    scratch: Path,
    *,
    d5_cwp_root: Path | None = None,
    d5_real_sample: Path | None = None,
) -> dict[str, str]:
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
    if d5_cwp_root is not None:
        if "StockWiki" not in roots:
            raise ValueError("D5 final acceptance requires an explicit StockWiki root")
        d5_src = d5_cwp_root / "src"
        env.update(
            STOCKWIKI_CWP_PROJECT=str(d5_cwp_root),
            STOCKWIKI_CWP_PYTHON=sys.executable,
            D5_REAL_PDF_SAMPLE=str(d5_real_sample) if d5_real_sample else "",
            CWP_V2_CODE_ROOT=str(d5_cwp_root),
            FILING_FETCH_V2_WIKI_SRC=str(d5_src),
            PYTHONPATH=os.pathsep.join(
                [str(d5_src), str(roots["StockWiki"]), str(ROOT / "src")]
            ),
        )
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
    parser.add_argument("--d5-ff-route", action="store_true",
        help="Run the focused mandatory D5 FF V2/V1 boundary suite")
    parser.add_argument("--d5-final", action="store_true",
        help="Run the mandatory D5 CWP + StockWiki + FF composition and real-sample suite")
    parser.add_argument("--d5-cwp-root", type=Path,
        help="Explicit D5 producer worktree; required by --d5-final")
    parser.add_argument("--d5-real-sample", type=Path,
        help="Existing read-only PDF used by the D5 real-source composition test")
    parser.add_argument("--d5-cwp-head", help="Expected CWP producer HEAD for D5 final acceptance")
    parser.add_argument("--d5-stockwiki-head", help="Expected StockWiki consumer HEAD for D5 final acceptance")
    parser.add_argument("--collect-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        tests = select_tests(
            args.tests, d4_final=args.d4_final, d5_ff_route=args.d5_ff_route,
            d5_final=args.d5_final, d5_cwp_root=args.d5_cwp_root,
            stockwiki_root=args.stockwiki_root,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.d4_final and (args.stockwiki_root is None or args.audit_root is None):
        parser.error("--d4-final requires explicit --stockwiki-root and --audit-root; absent consumers are not counted as passes")
    if args.d4_final and args.collect_only:
        parser.error("--collect-only cannot be used for the mandatory --d4-final acceptance run")
    if args.d5_ff_route and args.collect_only:
        parser.error("--collect-only cannot be used for the mandatory --d5-ff-route acceptance run")
    if args.d5_final and args.collect_only:
        parser.error("--collect-only cannot be used for the mandatory --d5-final acceptance run")
    d5_cwp_root = None
    d5_real_sample = None
    if args.d5_final:
        if args.stockwiki_root is None or args.d5_cwp_root is None or args.d5_real_sample is None:
            parser.error("--d5-final requires --d5-cwp-root, --stockwiki-root, and --d5-real-sample")
        if not args.d5_cwp_head or not args.d5_stockwiki_head:
            parser.error("--d5-final requires expected --d5-cwp-head and --d5-stockwiki-head from the reviewed handoff")
        try:
            d5_cwp_root = args.d5_cwp_root.resolve(strict=True)
            d5_real_sample = args.d5_real_sample.resolve(strict=True)
            stockwiki_root = args.stockwiki_root.resolve(strict=True)
        except OSError as exc:
            parser.error(f"D5 input path is unavailable: {exc}")
        if d5_cwp_root == ROOT.resolve() or stockwiki_root == ROOT.resolve():
            parser.error("--d5-final requires candidate worktrees separate from the ROOT checkout")
        if not d5_real_sample.is_file() or d5_real_sample.suffix.lower() != ".pdf":
            parser.error("--d5-real-sample must name an existing PDF file")
        try:
            sample_bytes = d5_real_sample.read_bytes()
        except OSError as exc:
            parser.error(f"D5 real sample cannot be read: {exc}")
        if not sample_bytes.startswith(b"%PDF-"):
            parser.error("--d5-real-sample does not have a PDF signature")
        sample_mtime_ns_before = d5_real_sample.stat().st_mtime_ns
        transport_path = stockwiki_root / D5_STOCKWIKI_TRANSPORT_CONFIG
        try:
            transport_payload = json.loads(transport_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            parser.error(f"StockWiki D5 production transport config is unreadable: {exc}")
        if not isinstance(transport_payload, dict) or not isinstance(
            transport_payload.get("processed_command"), list
        ):
            parser.error("StockWiki D5 production transport config has no processed_command")
        transport_config_sha_before = hashlib.sha256(transport_path.read_bytes()).hexdigest()
        try:
            cwp_head = subprocess.run(
                ["git", "-C", str(d5_cwp_root), "rev-parse", "HEAD"],
                check=True, capture_output=True, timeout=15,
            ).stdout.decode().strip()
            stockwiki_head = subprocess.run(
                ["git", "-C", str(stockwiki_root), "rev-parse", "HEAD"],
                check=True, capture_output=True, timeout=15,
            ).stdout.decode().strip()
        except (OSError, subprocess.SubprocessError) as exc:
            parser.error(f"D5 candidate Git version is unavailable: {exc}")
        if cwp_head != args.d5_cwp_head or stockwiki_head != args.d5_stockwiki_head:
            parser.error(
                "D5 candidate HEAD differs from the independently reviewed handoff: "
                f"CWP={cwp_head}, StockWiki={stockwiki_head}"
            )
        try:
            cwp_dirty = git_worktree_status(d5_cwp_root)
            stockwiki_dirty = git_worktree_status(stockwiki_root)
            committed_transport_blob = git_file_blob_at_commit(
                stockwiki_root, args.d5_stockwiki_head, D5_STOCKWIKI_TRANSPORT_CONFIG,
            )
            working_transport_blob = git_working_file_blob(
                stockwiki_root, D5_STOCKWIKI_TRANSPORT_CONFIG,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            parser.error(f"D5 candidate worktree state is unavailable: {exc}")
        if cwp_dirty or stockwiki_dirty:
            parser.error(
                "D5 candidates must match their reviewed commits before acceptance; "
                f"CWP dirty paths={len(cwp_dirty)}, StockWiki dirty paths={len(stockwiki_dirty)}"
            )
        if committed_transport_blob != working_transport_blob:
            parser.error("StockWiki transport config differs from the reviewed commit blob")
    roots = {"company-wiki": ROOT, "revenue-forecast": args.rf_root.resolve(strict=True),
        "filing-fetch": args.ff_root.resolve(strict=True), "earnings-transcripts": args.et_root.resolve(strict=True)}
    if args.stockwiki_root is not None:
        roots["StockWiki"] = args.stockwiki_root.resolve(strict=True)
    if args.audit_root is not None:
        roots["revenue-forecast-audit"] = args.audit_root.resolve(strict=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    consumers, consumer_test_coverage, excluded_consumers = consumer_scope(tests, roots)
    version_roots = dict(roots)
    if d5_cwp_root is not None:
        version_roots["company-wiki-d5-candidate"] = d5_cwp_root
    initial_versions = {
        name: code_version(
            root,
            extra_paths=(D5_STOCKWIKI_TRANSPORT_CONFIG,)
            if args.d5_final and name == "StockWiki" else (),
        )
        for name, root in version_roots.items()
    }
    record = {"schema_version": "source-system-check/1", "started_at": datetime.now(timezone.utc).isoformat(),
        "versions": initial_versions,
        "tests": tests, "selected_consumers": consumers,
        "selected_consumer_test_files": consumer_test_coverage,
        "consumers": [], "consumer_test_coverage": {}, "excluded_consumers": [],
        "provider_mode": "offline fixtures and loopback only", "collect_only": args.collect_only}
    if args.d5_final:
        record["d5_final"] = {
            "reviewed_heads": {
                "company-wiki-d5-candidate": args.d5_cwp_head,
                "StockWiki": args.d5_stockwiki_head,
            },
            "real_sample": {
                "name": d5_real_sample.name,
                "byte_size": len(sample_bytes),
                "mtime_ns_before": sample_mtime_ns_before,
                "sha256_before": hashlib.sha256(sample_bytes).hexdigest(),
            },
            "stockwiki_transport_config": {
                "path": D5_STOCKWIKI_TRANSPORT_CONFIG,
                "sha256_before": transport_config_sha_before,
                "git_blob_matches_reviewed_commit": True,
                "reviewed_git_blob": committed_transport_blob,
                "working_git_blob": working_transport_blob,
            },
            "candidate_worktrees_clean_before": True,
        }
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
            result = run_bounded(command, cwd=str(ROOT), env=environment(
                roots, scratch, d5_cwp_root=d5_cwp_root, d5_real_sample=d5_real_sample,
            ),
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
    d5_ff_file_counts = {
        file_path: _counts_for_file(file_path, test_counts["by_module"])
        for file_path in D5_FF_ROUTE_TESTS
    } if args.d5_ff_route else {}
    d5_ff_required_cases = [
        case for case in D5_FF_ROUTE_REQUIRED_CASES
        if any(node_id.endswith("::" + case) for node_id in test_counts.get("nodeids", []))
    ] if args.d5_ff_route else []
    if args.d5_ff_route and (
        test_counts["total"] == 0
        or test_counts["skipped"] > 0
        or "filing-fetch" not in executed_consumers
        or any(counts["passed"] == 0 for counts in d5_ff_file_counts.values())
        or len(d5_ff_required_cases) != len(D5_FF_ROUTE_REQUIRED_CASES)
    ):
        rc = 1
        record["failure"] = {
            "kind": "IncompleteD5FFRouteSuite",
            "message": "mandatory D5 FF route acceptance requires the V2 pathless and V1 compatibility cases to pass with zero skips",
            "missing_cases": sorted(set(D5_FF_ROUTE_REQUIRED_CASES) - set(d5_ff_required_cases)),
        }
    d5_final_file_counts = {}
    if args.d5_final:
        d5_final_file_counts = {
            "cwp_contract": _counts_for_file(
                str(d5_cwp_root / D5_FINAL_TEST_FILES["cwp_contract"]),
                test_counts["by_module"],
            ),
            "stockwiki_e2e": _counts_for_case_names(
                ("test_processed_document_port_serves_three_stockwiki_entries",), test_counts,
            ),
            "real_sample_e2e": _counts_for_case_names(
                ("test_real_sample_uses_processed_port_and_preserves_original",), test_counts,
            ),
            "ff_route": _counts_for_case_names(D5_FF_ROUTE_REQUIRED_CASES, test_counts),
        }
    d5_missing_cases = sorted(
        case for case in D5_FINAL_REQUIRED_CASES
        if not any(node_id.endswith("::" + case) for node_id in test_counts.get("nodeids", []))
    ) if args.d5_final else []
    d5_undercovered_files = [
        label for label, counts in d5_final_file_counts.items() if counts["passed"] == 0
    ] if args.d5_final else []
    if args.d5_final:
        # Pytest emits empty JUnit classnames for absolute files outside ROOT.
        # Attribute the mandatory D5 cases by their unique test names instead
        # of incorrectly reporting executed consumers as missing.
        executed_consumers, executed_coverage, executed_excluded = _attribute_d5_consumers(
            executed_consumers, executed_coverage, executed_excluded, d5_final_file_counts,
        )
        try:
            sample_after = d5_real_sample.read_bytes()
            sample_after_stat = d5_real_sample.stat()
            sample_sha_after = hashlib.sha256(sample_after).hexdigest()
            sample_stable = (
                sample_sha_after == record["d5_final"]["real_sample"]["sha256_before"]
                and len(sample_after) == record["d5_final"]["real_sample"]["byte_size"]
                and sample_after_stat.st_mtime_ns
                == record["d5_final"]["real_sample"]["mtime_ns_before"]
            )
        except OSError as exc:
            sample_sha_after = None
            sample_stable = False
            record["d5_final"]["real_sample"]["observation_error"] = type(exc).__name__
        record["d5_final"]["real_sample"].update(
            sha256_after=sample_sha_after,
            source_stable=sample_stable,
        )
        try:
            transport_config_sha_after = hashlib.sha256(
                (roots["StockWiki"] / D5_STOCKWIKI_TRANSPORT_CONFIG).read_bytes()
            ).hexdigest()
        except OSError as exc:
            transport_config_sha_after = None
            record["d5_final"]["stockwiki_transport_config"]["observation_error"] = type(exc).__name__
        record["d5_final"]["stockwiki_transport_config"].update(
            sha256_after=transport_config_sha_after,
            stable=transport_config_sha_after == transport_config_sha_before,
        )
        try:
            cwp_dirty_after = git_worktree_status(d5_cwp_root)
            stockwiki_dirty_after = git_worktree_status(roots["StockWiki"])
            worktrees_clean_after = not cwp_dirty_after and not stockwiki_dirty_after
        except (OSError, subprocess.SubprocessError):
            worktrees_clean_after = False
        record["d5_final"]["candidate_worktrees_clean_after"] = worktrees_clean_after
    if args.d5_final and (
        test_counts["total"] == 0 or test_counts["skipped"] > 0
        or test_counts["failed"] > 0 or test_counts["errors"] > 0
        or d5_undercovered_files or d5_missing_cases
        or "stockwiki" not in executed_consumers
        or "filing-fetch" not in executed_consumers
        or not record["d5_final"]["real_sample"]["source_stable"]
        or not record["d5_final"]["stockwiki_transport_config"]["stable"]
        or not record["d5_final"]["candidate_worktrees_clean_after"]
    ):
        rc = 1
        record["failure"] = {
            "kind": "IncompleteD5FinalSuite",
            "message": "D5 final acceptance requires CWP contract, all three StockWiki entries, FF V2/V1 routes, real-sample replay, and zero skips",
            "undercovered_files": d5_undercovered_files,
            "missing_cases": d5_missing_cases,
            "real_sample_stable": record["d5_final"]["real_sample"]["source_stable"],
            "stockwiki_transport_config_stable": record["d5_final"]["stockwiki_transport_config"]["stable"],
            "candidate_worktrees_clean_after": record["d5_final"]["candidate_worktrees_clean_after"],
        }
    record.update(
        consumers=executed_consumers,
        consumer_test_coverage=executed_coverage,
        excluded_consumers=executed_excluded,
    )
    final_versions = {
        name: code_version(
            root,
            extra_paths=(D5_STOCKWIKI_TRANSPORT_CONFIG,)
            if args.d5_final and name == "StockWiki" else (),
        )
        for name, root in version_roots.items()
    }
    stable_during_run = initial_versions == final_versions
    record.update(returncode=rc if stable_during_run else 1,
        seconds=round(time.monotonic()-started, 3), scratch_restored=not Path(temporary).exists(),
        test_counts=test_counts,
        d4_file_counts=d4_file_counts,
        d5_ff_file_counts=d5_ff_file_counts,
        d5_ff_required_cases=d5_ff_required_cases,
        d5_final_file_counts=d5_final_file_counts,
        d5_final_required_cases=[case for case in D5_FINAL_REQUIRED_CASES if case not in d5_missing_cases]
        if args.d5_final else [],
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
