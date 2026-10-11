"""Six independent selector micro probes; no pytest or network/provider calls."""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path.cwd().resolve()
OUT = Path(__file__).resolve().parent
FIXTURE_OUT = Path(chr(92) * 2 + "?" + chr(92) + str(OUT)) if os.name == "nt" else OUT
previous = json.loads((OUT / "review.json").read_text(encoding="utf-8"))
previous_probes = {item["name"]: item for item in previous["probes"]}
previous_attempt = {
    "command": ["python", "-X", "utf8", "-B", str(OUT / "probe.py")],
    "exit_code": 1, "passed": 4, "probe_count": 6,
    "review_json_sha256": hashlib.sha256((OUT / "review.json").read_bytes()).hexdigest(),
    "fixture_errors": [item for item in previous["probes"] if item["status"] == "fail"],
    "classification": "Two FileNotFoundError fixture writes caused by Windows path length; no selector assertion failure.",
}
assert OUT.is_relative_to(ROOT / "docs/plans")
BASE = "d3d807691efa68a30ae50fffb9980db4942eccae"
OLD = "ee293769037d0a9a205d75d15d64f0600929eaad"
spec = importlib.util.spec_from_file_location("independent_changed_selector", ROOT / "tools/changed_unit_tests.py")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)
commands = []
probes = []

def git(*args):
    cmd = ["git", *args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)
    commands.append({"argv": cmd, "exit_code": proc.returncode,
                     "stdout": proc.stdout, "stderr": proc.stderr})
    assert proc.returncode == 0, proc.stderr
    return proc.stdout

def put(root, name, body):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return name

def seed(root):
    put(root, "src/parcel/__init__.py", "")
    put(root, "src/parcel/model.py", "value = 2\n".replace("\\n", "\n"))
    put(root, "tests/unit/test_known.py", "from parcel.model import value\n".replace("\\n", "\n"))
    put(root, "tests/unit/test_other.py", "def test_independent(): pass\n".replace("\\n", "\n"))

def run_probe(name, body):
    try:
        result = body()
        probes.append({"name": name, "status": "pass", "result": result})
    except Exception as exc:
        probes.append({"name": name, "status": "fail", "error": type(exc).__name__ + ": " + str(exc)})

source_files = ["tools/changed_unit_tests.py", "tests/unit/test_ci_push_selection.py",
                "tools/pre_push_gate.py", ".githooks/pre-push", ".github/workflows/ci.yml"]
before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files}

def actual_range():
    changes = selector.changed_paths(ROOT, f"refs/heads/master {BASE} refs/heads/master {OLD}\n")
    assert changes is not None
    selected, reason = selector.select_unit_tests(ROOT, changes)
    assert selected == ["tests/unit/test_docx_heading_normalization.py"], (selected, reason)
    assert all(p.startswith("docs/plans/") or p == selected[0] for p in changes)
    raw = git("diff", "--no-renames", "--name-only", OLD, BASE, "--")
    assert changes == set(raw.splitlines())
    return {"old": OLD, "new": BASE, "change_count": len(changes),
            "changes": sorted(changes), "selected": selected, "reason": reason}

def archive_filter():
    with tempfile.TemporaryDirectory(prefix="archive-", dir=FIXTURE_OUT) as tmp:
        root = Path(tmp).resolve()
        assert root.is_relative_to(FIXTURE_OUT)
        seed(root)
        changes = {"docs/plans/a/conftest.py", "docs/plans/a/config/x.yaml",
                   "docs/plans/a/evidence/subprocess_probe.py", "docs/plans/a/requirements-dev.txt"}
        result = selector.select_unit_tests(root, changes)
        assert result == ([], "no behavior changes"), result
        return {"changes": sorted(changes), "selected": result[0], "reason": result[1]}

def conservative_fallbacks():
    with tempfile.TemporaryDirectory(prefix="fallback-", dir=FIXTURE_OUT) as tmp:
        root = Path(tmp).resolve()
        assert root.is_relative_to(FIXTURE_OUT)
        seed(root)
        variants = [None, {"src/parcel/deleted.py"}, {"scripts/deleted_driver.py"},
                    {"src/parcel/schema.json"}, {"config/source_catalog.yaml"},
                    {"tests/fixtures/shared.json"}, {"tests/support/conftest.py"}]
        observed = []
        for changes in variants:
            result = selector.select_unit_tests(root, changes)
            assert result[0] == ["tests/unit"], (changes, result)
            observed.append({"changes": sorted(changes) if changes is not None else None,
                             "selected": result[0], "reason": result[1]})
        assert selector.changed_paths(root, "bad push line") is None
        assert selector.changed_paths(root, f"a {'a' * 40} b {'0' * 40}") is None
        return observed

def runtime_with_archive_keeps_dynamic_consumers():
    with tempfile.TemporaryDirectory(prefix="runtime-", dir=FIXTURE_OUT) as tmp:
        root = Path(tmp).resolve()
        assert root.is_relative_to(FIXTURE_OUT)
        seed(root)
        put(root, "tests/support/launcher.py", "from runpy import run_path as execute\nexecute(script_name)\n")
        put(root, "tests/unit/test_cli_consumer.py", "from support.launcher import launch\n")
        put(root, "tests/unit/test_computed.py", "import importlib as il\nil.import_module(prefix + suffix)\n")
        changes = {"src/parcel/model.py", "docs/plans/evidence/conftest.py"}
        result = selector.select_unit_tests(root, changes)
        expected = ["tests/unit/test_cli_consumer.py", "tests/unit/test_computed.py",
                    "tests/unit/test_known.py"]
        assert result == (expected, "affected unit tests"), result
        return {"changes": sorted(changes), "selected": result[0], "reason": result[1]}

def test_only_helper_chain():
    with tempfile.TemporaryDirectory(prefix="helper-", dir=FIXTURE_OUT) as tmp:
        root = Path(tmp).resolve()
        assert root.is_relative_to(FIXTURE_OUT)
        seed(root)
        put(root, "tests/unit/test_helper.py", "import subprocess as sp\nsp.run(argv)\n")
        put(root, "tests/unit/test_bridge.py", "from .test_helper import value\n")
        put(root, "tests/unit/test_consumer.py", "from unit import test_bridge\n")
        put(root, "tests/unit/test_unrelated_cli.py", "from subprocess import run as launch\nlaunch(argv)\n")
        result = selector.select_unit_tests(root, {"tests/unit/test_helper.py", "docs/plans/x/probe.py"})
        expected = ["tests/unit/test_bridge.py", "tests/unit/test_consumer.py", "tests/unit/test_helper.py"]
        assert result == (expected, "affected unit tests"), result
        return {"selected": result[0], "reason": result[1],
                "kept_relative_helper_chain": True, "unrelated_cli_not_seeded": True}

def changed_runtime_dynamic():
    with tempfile.TemporaryDirectory(prefix="dynamic-", dir=FIXTURE_OUT) as tmp:
        root = Path(tmp).resolve()
        assert root.is_relative_to(FIXTURE_OUT)
        seed(root)
        observations = []
        for body in ["from subprocess import Popen as launch\nlaunch(argv)\n",
                     "from runpy import run_path as execute\nexecute('scripts/parcel.py')\n"]:
            put(root, "src/parcel/model.py", body)
            result = selector.select_unit_tests(root, {"src/parcel/model.py", "docs/plans/x/probe.py"})
            assert result == (["tests/unit"], "dynamic execution changed"), result
            observations.append({"body": body, "selected": result[0], "reason": result[1]})
        return observations

for name, body in [
    ("actual_ee293769_to_d3d80769_only_docx", actual_range),
    ("archive_responsibility_filter_precedes_entrypoint_rules", archive_filter),
    ("unknown_deleted_runtime_config_shared_fixture_full_unit", conservative_fallbacks),
    ("runtime_change_keeps_computed_and_cli_support_consumers", runtime_with_archive_keeps_dynamic_consumers),
    ("test_only_keeps_two_hop_known_helper_without_unrelated_cli", test_only_helper_chain),
    ("changed_aliased_runtime_execution_full_unit", changed_runtime_dynamic),
]:
    if "--retry-fixture-failures" in sys.argv and previous_probes[name]["status"] == "pass":
        probes.append(previous_probes[name])
    else:
        run_probe(name, body)

baseline = git("show", f"{BASE}:tests/unit/test_ci_push_selection.py")
current = (ROOT / "tests/unit/test_ci_push_selection.py").read_text(encoding="utf-8-sig")
def functions(text):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
old_funcs, new_funcs = functions(baseline), functions(current)
preserved = all(new_funcs.get(k) == v for k, v in old_funcs.items())
assert preserved and len(old_funcs) == 20
product_diff = git("diff", BASE, "--", "src", "config")
assert not product_diff
source_diff = git("diff", BASE, "--", "tools/changed_unit_tests.py", "tests/unit/test_ci_push_selection.py")
hook = (ROOT / ".githooks/pre-push").read_text(encoding="utf-8")
ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
gate = (ROOT / "tools/pre_push_gate.py").read_text(encoding="utf-8")
assert "--push-checks" in hook and "--fast-contracts-only" not in hook
assert "python -m pytest tests/unit" in ci and '"docs/plans/**"' in ci
assert "sys.stdin.read()" in gate and "changed_paths(PROJECT_ROOT" in gate

implementation = OUT.parent / "push-scope-implementation"
evidence = {}
for filename in ["red.json", "green.json", "ruff.json", "actual-range-green.json", "old-tests-preserved.json"]:
    path = implementation / filename
    evidence[filename] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "data": json.loads(path.read_text(encoding="utf-8-sig"))}
for filename in ["red.log", "green.log", "ruff.log"]:
    path = implementation / filename
    evidence[filename] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "tail": path.read_text(encoding="utf-8-sig").splitlines()[-12:]}
assert evidence["red.log"]["sha256"] == evidence["red.json"]["data"]["log_sha256"]
assert evidence["green.log"]["sha256"] == evidence["green.json"]["data"]["log_sha256"]
assert evidence["ruff.log"]["sha256"] == evidence["ruff.json"]["data"]["log_sha256"]
after = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files}
assert after == before
failed = [p for p in probes if p["status"] != "pass"]
report = {
    "reviewed_at": datetime.now(timezone.utc).isoformat(),
    "status": "no_material_findings" if not failed else "material_probe_failure",
    "base_head": BASE, "source_sha256": after,
    "scope": "Read-only stopped selector/test diff, existing hook/CI wiring and RED-to-GREEN; six local selector micro probes only.",
    "exclusions": ["No full Unit/48/39 suite rerun", "No public E2E", "No original test/source/config/PWF/company execution package modifications",
                   "No external GET/provider/model calls", "No new-HEAD CI success assertion"],
    "external_gets": 0, "provider_calls": 0, "model_calls": 0, "cost": 0,
    "source_unchanged_before_after": True,
    "old_test_functions": {"count": len(old_funcs), "all_ast_identical": preserved},
    "src_config_diff_against_base_empty": not product_diff,
    "hooks": {"pre_push_uses_push_checks": True, "ci_keeps_full_unit": True,
              "push_uses_stdin_full_range": True, "docs_plans_ignored_for_ci_scheduling": True},
    "existing_evidence_checked": evidence,
    "source_diff": source_diff,
    "probes": probes,
    "commands": commands,
    "earlier_tool_diagnostics": [
        {"tool": "CodeGraph context", "error": "not initialized", "action": "Read located files per review card; no init"},
        {"command": "git diff d3 -- selector/test; git status --short", "sandbox_exit_code": 1,
         "error": "must be run in a work tree", "action": "Read-only require_escalated Git succeeded without config changes"},
        {"command": "clear inherited GIT_*; git diff/status/range", "aggregate_exit_code": 0,
         "per_operation_errors": "diff working tree/status still failed; commit-to-commit range succeeded",
         "action": "No further environment/config investigation; use authorized read-only Git"}
    ],
    "material_findings": failed,
    "prior_probe_attempt": previous_attempt,
    "review_command": ["python", "-X", "utf8", "-B", str(OUT / "probe.py"), "--retry-fixture-failures"],
    "retry_scope": "Only the two fixture write failures rerun; four prior passes reused.",
    "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "limitations": [
        "Selection optimization is not a full CI guarantee.",
        "d3 CI success covers DOCX fix; selector change new exact HEAD CI remains pending.",
        "Test-only optimization retains statically known helper consumers; tests/unit/test_* changed files do not seed all unrelated dynamic consumers.",
        "Independent probes parse synthetic code; they do not execute synthetic runtime bodies."
    ],
    "stop": True
}
json_path = OUT / "review.json"
json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
lines = [
    "# 推送范围集中独立验收",
    "",
    "结论：" + ("无 material finding。六个独立 selector 微型 probe 全部通过。" if not failed else "有未通过 probe，详见 JSON。") + "只读停写源码、既有 hooks/CI 与 RED→GREEN。",
    "",
    "- 实际 ee293769037d0a9a205d75d15d64f0600929eaad → d3d807691efa68a30ae50fffb9980db4942eccae 40 个变更路径只选 tests/unit/test_docx_heading_normalization.py。",
    "- docs/plans 先按归档责任过滤；未知区间、删除/未知 runtime、global config、shared fixture 仍全 Unit；runtime 修改仍保留 computed/CLI support 消费者；变动的动态 runtime 仍 full Unit。",
    "- test-only 修改保留两跳相对 helper 与已知 consumer，未变的无关 CLI 不全 seed。",
    "- 原 20 个测试函数 AST 一致；src/config 对 d3 无 diff；审查前后 selector、tests、gate、hook、workflow 的 SHA 相同。",
    "- 既有 RED 5 failed / 43 passed；GREEN 48 passed / 1.35s；Ruff exit 0。读取并核验 log SHA，未重跑这些 suites。",
    "",
    "源码 SHA-256：",
    "",
]
lines.extend("- " + p + ": " + sha for p, sha in after.items())
lines += ["", "实际命令：python -X utf8 -B <本目录>/probe.py --retry-fixture-failures；最终 exit " + str(1 if failed else 0) + "。六组独立 probe，首轮 4 pass / 2 Windows 长路径 fixture 写入失败 / exit 1；只重验这两组，保留首轮真实错误。Git 子命令及各自 exit 在 review.json，均为 0。"]
lines += ["", "证据范围：本目录 probe.py/review.json/review.md；合成 fixture 仅在本目录临时子目录创建并自动清理。未修改源码、原 tests/config、ROOT PWF 或公司执行包。0 GET / provider / model 调用与费用。"]
lines += ["", "工具诊断：CodeGraph 对隔离 tree 未初始化，按卡读取已定位文件；默认沙箱 Git 的 work-tree 错误保留于 JSON，require_escalated 只读 Git 成功，未变更 Git 配置。"]
lines += ["", "限制：d3 精确 CI success 仅覆盖 DOCX 修复；本 selector 新 HEAD CI 尚待正常 commit/ff/push 后观测。selector 局部验证不能代签 full CI。"]
lines += ["", "STOP：此单一集中节点已完成，不增加审查门。", ""]
(OUT / "review.md").write_text("\n".join(lines), encoding="utf-8")
for p in [json_path, OUT / "review.md"]:
    print(str(p), hashlib.sha256(p.read_bytes()).hexdigest())
print(json.dumps({"probe_count": len(probes), "passed": len(probes) - len(failed), "exit_code": 1 if failed else 0}, ensure_ascii=False))
raise SystemExit(1 if failed else 0)
