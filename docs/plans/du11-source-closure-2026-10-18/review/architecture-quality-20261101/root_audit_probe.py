"""Bounded audit evidence, not a production gate or repository test suite.

Reads current source files, uses temporary synthetic source for two checker
counterexamples, and invokes legacy CLI --help only. No catalog/model/network.
"""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main() -> None:
    root = Path(__file__).resolve().parents[5]
    package = root / "src/company_wiki"
    files = list(package.rglob("*.py"))
    sizes = []
    errors = []
    groups: dict[str, dict[str, int]] = {}
    for file in files:
        text = file.read_text(encoding="utf-8-sig")
        rel = file.relative_to(package)
        group = rel.parts[0] if len(rel.parts) > 1 else "package_root"
        stats = groups.setdefault(group, {"files": 0, "lines": 0})
        stats["files"] += 1
        stats["lines"] += len(text.splitlines())
        try:
            ast.parse(text)
        except SyntaxError as exc:
            errors.append({"path": file.relative_to(root).as_posix(), "line": exc.lineno})
        sizes.append({"path": file.relative_to(root).as_posix(), "lines": len(text.splitlines())})
    gate_path = package / "source_catalog/architecture_gate.py"
    spec = importlib.util.spec_from_file_location("audit_architecture_checker", gate_path)
    assert spec is not None and spec.loader is not None
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    cases = {
        "uncovered_research_module_not_in_denylist": ("adapter.py", "from company_wiki import legacy_research_ingest\n"),
        "named_prohibited_qualified_import_false_negative": ("adapter.py", "from scripts.auto_synthesis import run_synthesis\n"),
        "initializer_false_negative": ("__init__.py", "import auto_synthesis\n"),
        "comment_false_positive": ("adapter.py", "# never import auto_synthesis here\n"),
    }
    observations = {}
    with tempfile.TemporaryDirectory(prefix="cwp-audit-checker-") as name:
        scratch = Path(name)
        for label, (filename, content) in cases.items():
            candidate = scratch / filename
            candidate.write_text(content, encoding="utf-8")
            ok, violations = gate.source_catalog_does_not_import_prohibited_modules(scratch)
            observations[label] = {"ok": ok, "violations": violations}
            candidate.unlink()
        candidate = scratch / "summarizer.py"
        candidate.write_text("def summarize():\n    return '投资建议：买入'\n", encoding="utf-8")
        ok, violations = gate.llm_summarizer_rejects_investment_content(scratch)
        observations["unused_content_checker_unconditional_success"] = {"ok": ok, "violations": violations}
    cli = {}
    writer_pattern = re.compile(r"\.write_text\s*\(|\.unlink\s*\(|os\.replace\s*\(")
    for name in ("copy_docs.py", "clean_watermarks.py"):
        file = root / "scripts" / name
        text = file.read_text(encoding="utf-8-sig")
        completed = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(file), "--help"],
            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=15,
            check=False,
        )
        cli[name] = {
            "returncode": completed.returncode,
            "help_visible": completed.stdout.startswith("usage:"),
            "explicit_retirement_guard_present": "enforce_direct_cli" in text,
            "existing_writer_inventory_regex_detects": bool(writer_pattern.search(text)),
            "executed_scope": "argparse help only; no copy or cleanup executed",
        }
    result = {
        "scope": "CWP current src AST inventory; synthetic checkers; two legacy --help probes",
        "not_proven": ["runtime throughput", "actual production stale cache", "all dynamic import edges", "whole sibling repository quality"],
        "inventory": {"files": len(files), "groups": groups, "syntax_errors": errors,
                      "largest_files": sorted(sizes, key=lambda x: x["lines"], reverse=True)[:12]},
        "checker_counterexamples": observations,
        "legacy_cli_help": cli,
        "cleanup": {"synthetic_temp_tree_removed": not scratch.exists(), "production_writes": 0,
                    "models": 0, "downloads": 0, "originals_changed": 0},
    }
    # Extract just these functions. Never import/construct a CatalogStore.
    scanner = ast.parse((package / "source_catalog/scanner.py").read_text(encoding="utf-8-sig"))
    selected = [node for node in scanner.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in {"CutoverGateError", "gate_production_dry_shadow", "scan_catalog"}]
    subset = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                             *selected], type_ignores=[])
    ast.fix_missing_locations(subset)
    namespace = {"_scan_catalog_impl": lambda *args, **kwargs: {"preview_reached": True}}
    exec(compile(subset, "scanner_audit_subset", "exec"), namespace)
    previews = {}
    for rounds in (None, 1, 2):
        try:
            previews[str(rounds)] = namespace["scan_catalog"](
                object(), None, dry_run=True, v2_scan_shadow=True, zero_diff_rounds=rounds)
        except namespace["CutoverGateError"] as exc:
            previews[str(rounds)] = {"blocked": True, "reason": str(exc)}
    result["legacy_explicit_v2_preview"] = previews
    output = Path(__file__).with_name("root_evidence.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(files), "syntax_errors": len(errors), "counterexamples": observations,
                      "legacy_cli_help": cli, "cleanup": result["cleanup"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
