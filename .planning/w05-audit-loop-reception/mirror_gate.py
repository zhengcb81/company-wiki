"""Keep ROOT's older integration tree aligned without touching its W04 WIP."""
import hashlib
import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROOT = Path("C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
BASE = Path("docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11")
OUT = PROJECT / BASE / "evidence/root-audit-loop-acceptance"


def main():
    files = ["tools/changed_unit_tests.py", "tests/unit/test_ci_push_selection.py", ".github/workflows/ci.yml"]
    assert not subprocess.check_output(["git", "status", "--porcelain", "--", *files], cwd=ROOT).strip()
    changes = []
    for name in files:
        old_blob = subprocess.check_output(["git", "rev-parse", f"c9dd5124:{name}"], cwd=PROJECT).strip()
        target_blob = subprocess.check_output(["git", "hash-object", name], cwd=ROOT).strip()
        assert old_blob == target_blob, name
        data = (PROJECT / name).read_bytes()
        (ROOT / name).write_bytes(data)
        assert (ROOT / name).read_bytes() == data
        changes.append({"path": str(ROOT / name), "baseline_blob": old_blob.decode(), "new_sha256": hashlib.sha256(data).hexdigest()})
    paths = [tree / "docs/plans" / family / (name + ".md")
             for tree in (PROJECT, ROOT)
             for family in ("cross-market-rf-e2e-2026-10-08", "narrative-evidence-pilot-2026-09-26")
             for name in ("task_plan", "findings", "progress")]
    paths += [PROJECT / BASE / (name + ".md") for name in ("task_plan", "findings", "progress")]
    note = "CWP接收资料commit c9dd5124尚未远端发布时，发现`.planning`与`docs/plans`分类不一致导致资料误触发全量Unit/CI；原失败保留，5RED→58GREEN并正常提交8d281af1，当前正常钩子全范围推送进行中。纯资料以后走已有小smoke/CI路径忽略；运行源码、配置、未知路径仍检查。独立临时根已恢复absent。ROOT旧集成树的3个原干净门禁文件已核baseline blob后定点同步，其他W04 WIP不动。\n\n"
    for path in paths:
        old = path.read_bytes()
        boundary = old.index("以下为历史记录；原字节保留。".encode())
        header, history = old[:boundary], old[boundary:]
        assert note.encode() not in header
        header = header.replace(b"## Next Step\n\n", note.encode() + b"## Next Step\n\n", 1)
        header = header.replace("ROOT继续修W04共用".encode(), "先正常发布本次CWP接收/分类修复，随后ROOT继续修W04共用".encode(), 1)
        path.write_bytes(header + history)
        assert path.read_bytes()[len(header):] == history
    (OUT / "root-gate-mirror.json").write_bytes((json.dumps({"code_files": changes, "pwf_headers": len(paths), "historical_bytes_preserved": True}, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"code_files": 3, "pwf_headers": len(paths)}))


if __name__ == "__main__":
    main()
