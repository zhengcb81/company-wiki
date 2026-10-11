"""Seal this one W05 reception after real unit/E2E/independent evidence."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance"
SOURCE = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/audit-loop-root")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, data):
    assert not path.exists(), str(path)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    args = parser.parse_args()
    review_path = args.review.resolve(strict=True)
    assert review_path.is_relative_to((OUT / "independent").resolve())
    review = read(review_path)
    assert str(review["status"]).startswith("PASS"), review["status"]
    assert review["stop"] is True and all(r["status"] == "PASS" for r in review["tests"])
    assert review["old_fail_preservation"]["all_preserved"]
    assert (review_path.parent / "final-manifest.json").is_file()
    unit_dir = OUT / "20261011T101209544274Z"
    unit = read(unit_dir / "unit-full.json")
    assert unit["exit_code"] == 0 and not unit["timed_out"]
    unit_log = unit_dir / "unit-full.log"
    assert digest(unit_log) == unit["log_sha256"]
    assert "Ran 220 tests" in unit_log.read_text(encoding="utf-8")
    e2e_dir = OUT / "final-e2e-20261011T101539365420Z"
    e2e_root = read(e2e_dir / "root-receipt.json")
    e2e = read(e2e_dir / "receipt.json")
    assert e2e_root["status"] == "PASS" and e2e_root["cleanup"]["restored"]
    assert not (e2e_dir / "scratch").exists()
    assert len(e2e["steps"]) == 48 and e2e["sentinel"]["unchanged"]
    freeze = read(unit_dir / "source-freeze.json")
    current = {name: digest(SOURCE / name) for name in freeze}
    differences = [name for name in freeze if freeze[name] != current[name]]
    assert differences == ["tools/run_pool_progress_e2e.py"], differences
    assert current["tools/run_pool_progress_e2e.py"] == e2e_root["e2e_script_sha"]
    assert current["skills/revenue-forecast-audit/scripts/pool_progress.py"] == e2e_root["producer_sha_before"] == e2e_root["producer_sha_after"]
    for field in ("source_sha256", "producer_sha256", "core_sha256"):
        if field in review:
            if isinstance(review[field], dict):
                assert all(current[name] == value for name, value in review[field].items())
            else:
                assert review[field] == e2e_root["producer_sha_after"]
    repairs = [
        "One reducer boundary binds run/execute attempt and freezes run versions; role retry attempt remains separate.",
        "Missing report/expert/retest references cannot count as completed quality evidence.",
        "Null or nonfinite/negative/bool cost never becomes settled zero; unknown remains reconcile, resend=false.",
        "Open historical major and retest obligations survive three new clean samples; last company can close honestly.",
        "Kernel-held Windows/POSIX mutex cannot be stolen by age; real process death releases it without splitting the lock domain.",
        "init/plan/migrate-preview atomically create new output only; existing state/pool/history is not overwritten.",
    ]
    report = {
        "schema_version": "w05-root-acceptance/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_ROOT_REPAIRED_READY_TO_MERGE_INSTALL",
        "delivery": {"branch": "codex/w05-audit-loop", "commits": ["7a5d4b8733c3442002b7ced95a4a319265ee687a", "2ed0b5e2dcaf3c5b2436e6a61bcf06f8fb03ac3a"], "original_intake_files_verified": 24},
        "integration_branch": "codex/root-w05-audit-loop-20261011",
        "source_sha256": current,
        "repairs": repairs,
        "unit": {"count": 220, "exit_code": 0, "command_seconds": unit["elapsed_seconds"], "log_sha256": unit["log_sha256"]},
        "new_root_behavior_methods": 19,
        "e2e": {"steps": 48, "seconds": e2e["elapsed_seconds"], "restore_initial_absent": True, "receipt_sha256": digest(e2e_dir / "receipt.json")},
        "independent": {"path": review_path.relative_to(OUT).as_posix(), "sha256": digest(review_path), "status": review["status"]},
        "prior_failures_preserved": True,
        "scope": "Synthetic progress/recovery protocol and skill wiring. No real company forecast quality conclusion.",
        "fees": {"http_calls": 0, "llm_calls": 0, "tokens": 0, "usd": 0},
        "shared_or_production_writes": "No raw, production configuration, active campaign, provider ledger or other owner WIP writes.",
        "remaining": ["Normal Audit commit/main fast-forward and targeted two-skill installation", "Company-wiki shared PWF commit/push"],
    }
    write(OUT / "acceptance.json", report)
    md = """# W05-AUDIT-LOOP ROOT 接收

状态：**PASS — 共因修复及集中复验完成，进入正常并线/安装。**

接收 `codex/w05-audit-loop` 的 `7a5d4b8` + `2ed0b5e`；原提交、原交接、原失败收据均保留。交付24项SHA/大小已验。ROOT在独立树修复状态机共因，没有改写交付树。

## 实际验收

- 原201项及原47步E2E通过，但独审原6纯/2tmp反例发现覆盖缺口；原FAIL仍保留。
- ROOT新增19个行为测试方法，先RED后GREEN，包括杀持锁子进程后立即恢复；全220项PASS，命令81.441秒。
- 最终48步隔离E2E PASS，86.696秒；模拟崩溃/丢角色/迟到报告/未知费用/版本改变/复测/停止，哨兵不变，scratch由absent恢复absent。
- 独立agent原范围复验通过；报告定位见 acceptance.json。全部核心、技能文档和19测试SHA仍匹配冻结输入。最终E2E仅补合成专家的真实fixture引用，旧失败不覆盖。

## 共因修复

1. 观察在同一reducer边界绑定run与execution_attempt；角色复审attempt独立，run启动冻结版本，迟到报告不贴新版本。
2. 四报告、专家或复测缺定位不能计clean；记录完整不等于真实研究合格。
3. cost=null持续对账，不把查询过当费用结清；有限非负金额才可结清，未知不盲重发。
4. 三家新clean不能吞历史open major/必须复测；最后一家有明确close动作，池耗尽不冒签。
5. 使用OS内核互斥，活写者不按mtime抢占；进程死自动释放，不删除锁文件造成ABA。
6. init/plan/migrate仅原子创建新输出，拒绝覆盖已有state、pool和历史。

## 范围与后续

已接线SKILL/company-pool-loop和契约，技能结构校验PASS；接下来正常提交、Audit main快进及tools定点同步。工具只给native harness恢复建议，仍由真实独立agent执行与审查。验收0 HTTP/LLM/token/费用，不增加人工许可链、常驻worker或每commit长测试。母PWF的W04语义FAIL与G2/G4/G5真实公司步骤仍未完成，W05另外两条线继续各自所有权。

完整证据在本目录；原件/生产配置/活动账及其他owner WIP未修改。Audit没有remote，不创建公开仓库。
"""
    (OUT / "acceptance.md").write_bytes(md.encode())
    files = {p.relative_to(OUT).as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size}
             for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "acceptance-manifest.json"}
    write(OUT / "acceptance-manifest.json", {"files": files})
    print(json.dumps({"status": report["status"], "files": len(files), "bytes": sum(r["bytes"] for r in files.values())}))


if __name__ == "__main__":
    main()
