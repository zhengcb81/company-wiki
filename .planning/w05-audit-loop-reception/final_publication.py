"""Record observed remote publication, then close the owned reception plan."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROOT = Path("C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
BASE = Path("docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11")
OUT = PROJECT / BASE / "evidence/root-audit-loop-acceptance"


def main():
    assert not (OUT / "completion.json").exists()
    result = json.loads((OUT / "publication-B-push.json").read_text(encoding="utf-8-sig"))
    assert result["exit_code"] == 0
    remote = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/master"], cwd=PROJECT).decode().split()[0]
    assert remote == result["commit"] == "8d281af1a2ee4f9adbba4c9bdbb576505c240095"
    log = (OUT / "publication-B-push.log").read_text(encoding="utf-8-sig", errors="replace")
    assert "pre-push gate GREEN" in log and "passed" in log
    summary = [line.strip() for line in log.splitlines() if "passed" in line]
    record = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "COMPLETE",
              "audit_main": "321d4c165575e81add3b4aa1ee9ba0a047ca6082", "audit_remote": None,
              "company_wiki_source_commit": result["commit"], "observed_remote_head": remote,
              "normal_push_unit_summary": summary, "gate_tdd": "5 RED then 58 GREEN",
              "installed_destinations": 2, "package_files_per_destination": 24,
              "project_incremental_fees_usd": 0, "raw_and_production_config_unchanged": True,
              "scope": "W05-AUDIT-LOOP acceptance, root cause repair, main merge, skill installation and observed CWP publication",
              "remaining_mother_pwf": "W04 semantic roots and G2/G4/G5; W05 other owners/W06 remain separate"}
    (OUT / "completion.json").write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode())
    md = f"""# W05-AUDIT-LOOP 接收已完成

交付两笔commit加ROOT共因修复正常合入Audit main **321d4c1**；主线干净，两套技能各24文件MATCH。Audit无remote，未创建远端。

24项交接验真、原201/47步骤保留、19新增RED→GREEN、最终全220PASS与48步骤隔离E2E PASS、独立6纯/2tmp复验PASS。原FAIL和观察脚本错误均保留；原件、生产配置、真实活动与累计账不变，本轮项目费用0。

CWP接收/目录分类修复已正常推远端 **8d281af1**，实读remote同HEAD。正常全范围推送结果：{'；'.join(summary)}。第一次c9dd推送未成功记录保留；已根治`.planning`被误当runtime的目录责任缺口，5RED→58GREEN。后续纯资料不启动全CI，混合runtime/配置/未知路径继续验证。

详见[工程接收](acceptance.md)、[最终独审](independent/final-review.md)、[定点安装](installation.json)、[发布共因](publication-fix.md)及[实际推送](publication-B-push.json)。CI精确commit状态另外只读观察，本文不冒称远端CI成功。

本包完成；母PWF继续W04共用阶段/预算召回后推进G2→G4→G5，不将记录工具通过代替真实公司研究通过。W05其他两线及W06保持原owner。
"""
    (OUT / "completion.md").write_bytes(md.encode())
    paths = [tree / "docs/plans" / family / (name + ".md") for tree in (PROJECT, ROOT)
             for family in ("cross-market-rf-e2e-2026-10-08", "narrative-evidence-pilot-2026-09-26")
             for name in ("task_plan", "findings", "progress")]
    paths += [PROJECT / BASE / (name + ".md") for name in ("task_plan", "findings", "progress")]
    for path in paths:
        before = path.read_bytes()
        boundary = before.index("以下为历史记录；原字节保留。".encode())
        header, history = before[:boundary], before[boundary:]
        header = header.replace("当前正常钩子全范围推送进行中".encode(),
                                f"正常钩子全范围PASS（{'；'.join(summary)}）、远端8d281af1已实读验真".encode(), 1)
        header = header.replace("先正常发布本次CWP接收/分类修复，随后ROOT继续".encode(), "本次CWP接收/分类修复已发布；ROOT继续".encode(), 1)
        path.write_bytes(header + history)
        assert path.read_bytes()[len(header):] == history
    selected = PROJECT / ".planning/w05-audit-loop-reception"
    plan = (selected / "task_plan.md").read_text(encoding="utf-8")
    plan = plan.replace("- [ ] 正常推送CWP", "- [x] 正常推送CWP")
    plan = plan[:plan.index("## Next Step")] + "## Next Step\n\n本包COMPLETE：Audit main321d4c1、两套技能24文件MATCH、CWP源修复8d281af1已正常推送且远端同HEAD。最终发布本收尾记录；之后恢复母PWF的W04责任包，不重跑一次性补丁或重派其他owner。\n"
    (selected / "task_plan.md").write_bytes(plan.encode())
    print(json.dumps(record))


if __name__ == "__main__":
    main()
