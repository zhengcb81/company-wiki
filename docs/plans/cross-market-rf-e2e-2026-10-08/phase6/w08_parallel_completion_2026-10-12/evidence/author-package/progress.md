# W08-CWP-G2-REPLAY progress

- base_head: 122bbe3ba142979a2e478f886eb25de76edf2e00
- branch: codex/w08-cwp-g2-replay

## A — 接口冻结（完成）

- 读施工卡/HANDOFF_CONTRACT/INPUTS；实跑候选 CLI 的 --help，未按记忆造参数。
- 冻结 code binding SHA：见 tools/narrative_g2_replay/run.py TRACKED_MODULES
  与 findings F3。
- 环境阻塞先解：见 findings F1（沙箱可写根不含工区），转 danger-full-access 后
  可写，并得到真实基线 F2 = 2 failed / 37 passed / 2 skipped。

## B — 实现（完成）

- 先写 RED：tests/unit/test_w08_narrative_g2_replay.py 固定 oracle 行为。
- 实现 tools/narrative_g2_replay/{__init__,specs,fixtures,oracle,report,run}.py。
- 结果：`26 passed`。

## C — 端到端（完成）

- 真实 E2E 连续两次独立 PASS（attempt-0001 / 0002），exit 0；
  清理后从干净树再做最终验收 PASS。
- run1 = 8 real loopback POST；run2 = 0 new POST 且 pins 相同；
  9/9 公开读取验真；RF 9/9 read ok；owned 容器 restored，remaining=[]。
- oracle 对真实记录 12 项对抗篡改全部正确拒绝。
- 证据（压缩）：`.planning/w08-cwp-g2-replay/evidence/report-*.json`（3 份，147KB）。

## 收尾

- 纯新增：`git status --untracked-files=no` 为空，未改任何已跟踪文件。
- 已知基线失败如实记录（findings F1/F2a/F2b），未修、未改成期望。
- 参数与结果见 tools/narrative_g2_replay/README.md 与
  docs/handoffs/w08-cwp-g2-replay/handoff.{md,json}。
