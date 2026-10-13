"""Prepend a short DU navigation section to the mother PWF.

An earlier session corrupted this file by rewriting its newlines; the file is therefore
read and written as BYTES so the existing content is preserved exactly and only a new
prefix is added.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PWF = ROOT / "docs" / "plans" / "narrative-evidence-pilot-2026-09-26" / "task_plan.md"

PREFIX = """## 文档理解升级并线状态 — 2026-10-13

[文档理解升级（du-input/route/structure/packages）](../document-understanding-2026-10-13/README.md)
三包已实现并合并到 `codex/du-root-integration-20261013`，跨层验收 331 tests 通过（含真实原件节点），
原件 0 复制 0 修改、0 模型调用、0 费用；**尚未接入生产解析链**。母计划的 W04、G2、G4、G5
保持开放，本计划不替代也不签收它们。生产切换与真实模型大节点按母计划 G4/G5 另行执行。
下面内容为原有记录，按原字节保留。

"""


def main() -> int:
    payload = PWF.read_bytes()
    marker = PREFIX.encode("utf-8")
    if marker in payload:
        print("prefix already present; nothing to do")
        return 0
    PWF.write_bytes(marker + payload)
    print(f"prepended {len(marker)} bytes; file is now {PWF.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
