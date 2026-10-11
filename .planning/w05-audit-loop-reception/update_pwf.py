"""Prepend the exact W05 acceptance without rewriting historical plan bytes."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROOT_TREE = Path("C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
AUDIT = Path("C:/Users/郑曾波/Projects/revenue-forecast-audit")
BASE = Path("docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11")
OUT = PROJECT / BASE / "evidence/root-audit-loop-acceptance"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepend(path, content, changes):
    data = path.read_bytes()
    marker = "## W05-AUDIT-LOOP ROOT 已接收（2026-10-11）"
    assert marker.encode() not in data[:500], path
    prefix = (marker + "\n\n" + content + "\n\n以下为历史记录；原字节保留。\n\n").encode()
    path.write_bytes(prefix + data)
    assert path.read_bytes()[len(prefix):] == data
    changes.append({"path": str(path), "previous_sha256": sha(data), "new_sha256": sha(prefix + data), "previous_bytes_preserved": True})


def main():
    acceptance = json.loads((OUT / "acceptance.json").read_bytes())
    installation = json.loads((OUT / "installation.json").read_bytes())
    assert acceptance["status"].startswith("PASS")
    assert all(r["status"] == "MATCH" for r in installation["check"]["installations"])
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=AUDIT).decode().strip()
    assert head == installation["main_head"]
    body = f"""Audit `codex/w05-audit-loop` 的 `7a5d4b8`、`2ed0b5e` 已接收；ROOT封存原FAIL并按共因修复，正常快进 main `{head}`。两套物理技能目录 .claude/.agents 各24文件SHA MATCH，只同步本技能4差异文件/套与manifest，其他文件保留。Audit无remote，未创建远端。

24项原交接验真、19新增RED→GREEN、全220PASS、48步隔离E2E PASS（86.696s）、独立原6纯/2tmp反例复验PASS_WITH_SCOPE；scratch恢复absent，0项目HTTP/LLM/token/费用。实际源码/安装/独审与失败记录见[接收报告](phase6/w05_parallel_common_roots_2026-10-11/evidence/root-audit-loop-acceptance/acceptance.md)。这是循环进度/恢复工具验收，不是三家真实预测质量通过。

W05-CWP-OCR、W05-RF-FLOW继续原owner；W06三卡READY各自排他，不能重派在施工卡。ROOT W04阶段判断/预算召回独审仍FAIL，保留原3P1/2P2及实证，不发布有缺陷selector；G2真实摘要消费、G4原公司独审和G5新公司/池loop未完成。原件、生产配置、活动累计账、其他owner WIP、Dayu/IQS均未改。既有母账413778tokens/334463µUSD+FX2764保持；本轮增量0。

## Next Step

ROOT继续修W04共用阶段/预算召回，原件回放和大节点独审通过后才推进G2→G4→G5。接收已完成的其他施工卡按真实交接逐项并线，不增加小节点签收。"""
    changes = []
    for tree in (PROJECT, ROOT_TREE):
        for family in ("cross-market-rf-e2e-2026-10-08", "narrative-evidence-pilot-2026-09-26"):
            for name in ("task_plan.md", "findings.md", "progress.md"):
                adjusted = body
                if family == "narrative-evidence-pilot-2026-09-26":
                    adjusted = adjusted.replace("(phase6/", "(../cross-market-rf-e2e-2026-10-08/phase6/")
                prepend(tree / "docs/plans" / family / name, adjusted, changes)
    lane_body = body.replace("(phase6/w05_parallel_common_roots_2026-10-11/evidence/", "(evidence/")
    for name in ("task_plan.md", "findings.md", "progress.md"):
        prepend(PROJECT / BASE / name, lane_body, changes)
    selected = PROJECT / ".planning/w05-audit-loop-reception"
    text = (selected / "task_plan.md").read_bytes().decode()
    text = text.replace("- [ ]", "- [x]")
    text = text[:text.index("## Next Step")] + "## Next Step\n\n本次接收/并线/安装完成。正常提交并推送CWP记录；之后回到母PWF的W04责任包。\n"
    (selected / "task_plan.md").write_bytes(text.encode())
    for name in ("findings.md", "progress.md"):
        prepend(selected / name, lane_body, changes)
    (OUT / "pwf-update.json").write_bytes((json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "changes": changes}, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"updated": len(changes), "main_head": head}))


if __name__ == "__main__":
    main()
