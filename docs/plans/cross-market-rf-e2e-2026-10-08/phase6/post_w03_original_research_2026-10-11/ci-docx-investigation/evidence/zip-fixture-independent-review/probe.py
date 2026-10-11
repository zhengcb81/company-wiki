"""Bounded independent ZIP fixture review. No network, providers, or product writes."""
from __future__ import annotations
import ast
from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import types
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(r"C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
CI = ROOT / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/post_w03_original_research_2026-10-11/ci-docx-investigation"
OUT = CI / "evidence/zip-fixture-independent-review"
SOURCE = "ee293769037d0a9a205d75d15d64f0600929eaad"
TEST = "tests/unit/test_docx_heading_normalization.py"
OLD_SHA = "d428ad041147fb650671ee805c38a03539b4f28529a5516bce325cc3a8541761"
OLD_FP = "a6580fca5dcd6c063e2447bf5cf489aaabd8f61c52856646db744cb68d0031e4"
LINUX_SHA = "1af5cb9e60f9b799b6057fe992b20a4009c338b38c5eb28e01307902024fa0d9"
LINUX_FP = "63c83b5638f54e4454dd66e69fbd51b89cd5b69f8f2f9a1146298e87c64e7c97"
sys.path.insert(0, str(ROOT / "src"))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])

def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value

def complete_record(document):
    return {
        "source_sha256": document.source_sha256,
        "parser_version": document.parser_version,
        "metadata": plain(document.metadata),
        "errors": list(document.structure.errors),
        "units": [{
            "unit_id": unit.unit_id, "source_id": unit.source_id,
            "parser_name": unit.parser_name, "parser_version": unit.parser_version,
            "coordinates": asdict(unit.coordinates), "raw_text": unit.raw_text,
            "unit_kind": unit.unit_kind, "source_role": unit.source_role,
            "language": unit.language, "quality_flags": list(unit.quality_flags),
            "metadata": plain(unit.metadata),
        } for unit in document.units],
    }

def record_fp(record):
    return sha(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())

current_bytes = (ROOT / TEST).read_bytes()
current_source = current_bytes.decode("utf-8")
baseline_bytes = git("show", SOURCE + ":" + TEST)
baseline_source = baseline_bytes.decode("utf-8")
assert git("rev-parse", "HEAD").decode().strip() == SOURCE
source_tree = ast.parse(baseline_source)
current_tree = ast.parse(current_source)
old_named = {node.name: node for node in source_tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
new_named = {node.name: node for node in current_tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
preserved = []
for name, old_node in old_named.items():
    if name == "package":
        continue
    assert ast.dump(old_node, include_attributes=False) == ast.dump(new_named[name], include_attributes=False), name
    preserved.append(name)
assert set(new_named) - set(old_named) == {"test_legacy_fixture_bytes_are_independent_of_zip_host_default"}
old_non_functions = [node for node in source_tree.body if not isinstance(node, (ast.FunctionDef, ast.ClassDef))]
new_non_functions = [node for node in current_tree.body if not isinstance(node, (ast.FunctionDef, ast.ClassDef))
    and not (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "LEGACY_SOURCE_SHA256" for target in node.targets))]
assert ast.dump(ast.Module(body=old_non_functions, type_ignores=[]), include_attributes=False) == ast.dump(ast.Module(body=new_non_functions, type_ignores=[]), include_attributes=False)
changed_under_guard = git("diff", "--name-only", "--", "src", "config.yaml", "config/source_catalog.yaml", "tests").decode().splitlines()
assert changed_under_guard == [TEST], changed_under_guard

import pytest
from company_wiki import document_normalization as dn
from company_wiki.document_normalization.units import verify_unit_identity

baseline = types.ModuleType("independent_baseline")
current = types.ModuleType("independent_current")
exec(compile(baseline_source, TEST + "@baseline", "exec"), baseline.__dict__)
exec(compile(current_source, TEST + "@fixed", "exec"), current.__dict__)
sealed_path = CI / "evidence/docx-heading-implementation/legacy-original.docx"
sealed = sealed_path.read_bytes()
assert sha(sealed) == OLD_SHA
original_info = zipfile.ZipInfo
cases = []
payloads = {}
for label, module in (("baseline", baseline), ("fixed", current)):
    for host_system in (0, 3):
        class SimulatedHostZipInfo(original_info):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.create_system = host_system
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(zipfile, "ZipInfo", SimulatedHostZipInfo)
            data = module.legacy_original()
            document = module.normalize(data, parser_version="1.0.0")
            record = complete_record(document)
            fingerprint = record_fp(record)
            digest = sha(data)
            expected_sha = LINUX_SHA if label == "baseline" and host_system == 3 else OLD_SHA
            expected_fp = LINUX_FP if label == "baseline" and host_system == 3 else OLD_FP
            assert digest == expected_sha and fingerprint == expected_fp
            assert len(document.units) == 6
            locators = [unit.metadata["source_locator"] for unit in document.units]
            assert locators == [
                "cwp-docx-body/1|p=0", "cwp-docx-body/1|p=1", "cwp-docx-body/1|p=2",
                "cwp-docx-body/1|p=3", "cwp-docx-body/1|p=4", "cwp-docx-body/1|t=0|r=0|c=0|p=0",
            ]
            assert dn.replay_units(data, source_sha256=digest, units=document.units,
                limits=dn.NormalizationLimits()) == tuple(unit.raw_text for unit in document.units)
            for unit in document.units:
                verify_unit_identity(unit, format_name="docx")
            assert set(document.units[1].metadata) == {"normalization_schema", "format", "source_sha256", "source_locator", "transform"}
            with zipfile.ZipFile(BytesIO(data)) as archive:
                creator_systems = sorted({info.create_system for info in archive.infolist()})
                entry_payload_sha = {name: sha(archive.read(name)) for name in archive.namelist()}
            sealed_equal = data == sealed
            if label == "fixed":
                assert sealed_equal and creator_systems == [0]
            cases.append({
                "label": label, "simulated_host_default": host_system,
                "source_sha256": digest, "complete_record_fingerprint": fingerprint,
                "bytes": len(data), "unit_count": len(document.units),
                "creator_systems": creator_systems, "equal_to_sealed_original": sealed_equal,
                "locator_identity_metadata_replay": "PASS",
                "entry_payload_sha256": entry_payload_sha,
            })
            payloads[(label, host_system)] = data

assert len({json.dumps(case["entry_payload_sha256"], sort_keys=True) for case in cases}) == 1
delta = [offset for offset, (left, right) in enumerate(zip(payloads[("baseline", 0)], payloads[("baseline", 3)])) if left != right]
assert len(delta) == len(cases[0]["entry_payload_sha256"]) == 5
assert payloads[("fixed", 0)] == payloads[("fixed", 3)] == sealed

publication = CI / "evidence/source-publication"
red = json.loads((publication / "zip-host-tdd-red.json").read_text(encoding="utf-8"))
green = json.loads((publication / "zip-host-tdd-green.json").read_text(encoding="utf-8"))
assert sha((publication / "zip-host-tdd-red.log").read_bytes()) == red["log_sha256"]
assert sha((publication / "zip-host-tdd-green.log").read_bytes()) == green["log_sha256"]
assert red["exit_code"] == 1 and green["exit_code"] == 0
red_log = (publication / "zip-host-tdd-red.log").read_text(encoding="utf-8")
green_log = (publication / "zip-host-tdd-green.log").read_text(encoding="utf-8")
assert "1 failed, 1 passed in 0.82s" in red_log and "39 passed, 1 warning in 0.74s" in green_log
protected = {name: sha((ROOT / name).read_bytes()) for name in green["protected_after"]}
assert protected == green["protected_before"] == green["protected_after"]
check = json.loads((publication / "exact-ci-check-failure.json").read_text(encoding="utf-8"))
assert check["head_sha"] == SOURCE and check["conclusion"] == "failure"
ci_log = (publication / "exact-ci-failed-job.log").read_text(encoding="utf-8")
assert "platform linux -- Python 3.12.15" in ci_log and "2 failed, 3057 passed, 6 skipped" in ci_log
assert LINUX_FP in ci_log and OLD_FP in ci_log
assert "test_explicit_legacy_is_exact_field_metadata_identity_and_replay_freeze" in ci_log
assert "test_default_and_saved_old_pins_have_separate_generation_and_replay_identity" in ci_log
reproduction = json.loads((publication / "zip-host-reproduction.json").read_text(encoding="utf-8"))
assert {(item["host_create_system"], item["original_sha256"], item["record_fingerprint"]) for item in reproduction["records"]} == {(0, OLD_SHA, OLD_FP), (3, LINUX_SHA, LINUX_FP)}

host_tests = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "pytest",
    TEST + "::test_legacy_fixture_bytes_are_independent_of_zip_host_default",
    "-q", "--tb=short", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True)
host_log = host_tests.stdout + host_tests.stderr
(OUT / "two-host-tests.log").write_bytes(host_log)
assert host_tests.returncode == 0 and b"2 passed" in host_log
assert protected == {name: sha((ROOT / name).read_bytes()) for name in protected}
assert current_bytes == (ROOT / TEST).read_bytes()

evidence_paths = [
    "ZIP_FIXTURE_CONTINUATION.md",
    "evidence/source-publication/exact-ci-check-failure.json",
    "evidence/source-publication/exact-ci-failed-job.log",
    "evidence/source-publication/zip-host-reproduction.json",
    "evidence/source-publication/zip-host-tdd-red.json",
    "evidence/source-publication/zip-host-tdd-red.log",
    "evidence/source-publication/zip-host-tdd-green.json",
    "evidence/source-publication/zip-host-tdd-green.log",
    "evidence/docx-heading-implementation/legacy-original.docx",
]
report = {
    "review_type": "bounded_independent_zip_fixture_review",
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "source_commit": SOURCE,
    "original_ci": {"run_id": 38105648234, "job_id": 114370500236, "platform": "linux", "result": "2 failed, 3057 passed, 6 skipped"},
    "decision": "ACCEPT_FIXTURE_ONLY_FIX",
    "material_findings": [],
    "rationale": "Only the test ZIP creator metadata is frozen. Original complete-record, metadata, identity, locator, replay and version assertions are AST-identical to the exact source commit. Both simulated host defaults produce sealed historical bytes and the original full legacy fingerprint.",
    "actual_independent_probe_cases": len(cases),
    "actual_new_host_pytest_cases": 2,
    "independent_cases": cases,
    "baseline_host_byte_delta": {"count": len(delta), "offsets": delta, "all_uncompressed_xml_payloads_equal": True},
    "original_assertion_functions_preserved": preserved,
    "original_non_function_statements_preserved_except_added_sha_constant": True,
    "guarded_git_diff": changed_under_guard,
    "test_file_sha256": sha(current_bytes),
    "probe_sha256": sha(Path(__file__).read_bytes()),
    "protected_product_and_config_sha256": protected,
    "protected_before_equals_after": True,
    "red_and_green_log_hashes_verified": True,
    "new_host_pytest_exit_code": host_tests.returncode,
    "new_host_pytest_log_sha256": sha(host_log),
    "evidence_sha256": {name: sha((CI / name).read_bytes()) for name in evidence_paths},
    "remote_ci_claim": "NOT_SIGNED: new exact Linux CI has not been observed by this review; local simulated ZIP hosts cannot substitute for that final evidence.",
    "boundaries": {"company_review_material_read": False, "external_network_calls": 0, "provider_calls": 0, "model_calls": 0, "source_or_config_writes": 0, "large_suites_rerun": False},
    "stop": "STOP",
}
(OUT / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
markdown = f"""# ZIP fixture 独立定点验收

接受此 fixture-only 修复。精确 source 为 `{SOURCE}`；未发现材料问题。

原 CI38105648234 的 Linux Python 3.12.15 日志只有两个旧完整 record 指纹断言失败，实际值 `{LINUX_FP}`。独立反例以同一 XML、顺序与时间戳重建 baseline：宿主 0 得到旧源 SHA `{OLD_SHA}` 和旧指纹 `{OLD_FP}`；宿主 3 精确得到远端失败指纹。两者只有 5 个 ZIP creator-system 字节不同，各 XML payload SHA 均相同。

独立运行 4 个 probe case（baseline 0/3、fixed 0/3），另仅运行新增参数化 host 测试 2 项，全部符合预期。修复后两个模拟宿主输出字节彼此相等且逐字节等于封存 `evidence/docx-heading-implementation/legacy-original.docx`，仍为 2729 B、6 units，旧 SHA 和完整指纹保持。定位、单位 identity、metadata 集合与 replay 均通过。

与精确 source commit 的 AST 比较证明：原有所有函数（除 package 封套生成）及原有非函数语句未改，包括 complete-record serializer、旧 fingerprint、metadata、locator、replay、source mutation 拒绝与 parser/version 断言。新增原 SHA 常量与两宿主反例增强守卫；保护范围内 Git 唯一测试差异是 `{TEST}`。7 个产品源及 2 份配置的 SHA 与保存 GREEN 前后完全一致。

已核验原 RED/GREEN 日志 SHA：RED 1 fail/1 pass，GREEN 39 pass/0.74s；本次未重跑 39/3196/public E2E，未访问网络、公司审查材料或付费供应商。

**新精确 Linux CI 尚未由本审查观察，不能代签。** 本结论接受该 fixture-only 实施及局部证据，不宣称新远端 CI 已通过。

完整证据 SHA、4 probe case 与本次两宿主测试日志 SHA 见 review.json。

STOP
"""
(OUT / "review.md").write_text(markdown, encoding="utf-8")
print(json.dumps({"decision": report["decision"], "probe_cases": len(cases), "host_tests": 2,
    "review_json_sha256": sha((OUT / "review.json").read_bytes()),
    "review_md_sha256": sha((OUT / "review.md").read_bytes()), "stop": "STOP"}, ensure_ascii=False))
