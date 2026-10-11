# 推送范围集中独立验收

结论：无 material finding。六个独立 selector 微型 probe 全部通过。只读停写源码、既有 hooks/CI 与 RED→GREEN。

- 实际 ee293769037d0a9a205d75d15d64f0600929eaad → d3d807691efa68a30ae50fffb9980db4942eccae 40 个变更路径只选 tests/unit/test_docx_heading_normalization.py。
- docs/plans 先按归档责任过滤；未知区间、删除/未知 runtime、global config、shared fixture 仍全 Unit；runtime 修改仍保留 computed/CLI support 消费者；变动的动态 runtime 仍 full Unit。
- test-only 修改保留两跳相对 helper 与已知 consumer，未变的无关 CLI 不全 seed。
- 原 20 个测试函数 AST 一致；src/config 对 d3 无 diff；审查前后 selector、tests、gate、hook、workflow 的 SHA 相同。
- 既有 RED 5 failed / 43 passed；GREEN 48 passed / 1.35s；Ruff exit 0。读取并核验 log SHA，未重跑这些 suites。

源码 SHA-256：

- tools/changed_unit_tests.py: 4c589d12bc467fc14aefcad3dbfffce8bcea0a217c67bb2fda5d05320a171b19
- tests/unit/test_ci_push_selection.py: 37e848b78ea8957bd678edd90a2016b7fd26404d6b4dc655eb106413f308be81
- tools/pre_push_gate.py: 58f50f6467dfc52f67d9a2a7dbadb943e683313e5efe6f514d4ac9d95b6752d4
- .githooks/pre-push: 365cf3a7a63a1bcd4173934b28af6a1023cc850cdd5360d48aa694e016ed96ab
- .github/workflows/ci.yml: 9f2864979058658089bb9d4edd879e05a733404f3d1a6d1de06ec012a63359b8

实际命令：python -X utf8 -B <本目录>/probe.py --retry-fixture-failures；最终 exit 0。六组独立 probe，首轮 4 pass / 2 Windows 长路径 fixture 写入失败 / exit 1；只重验这两组，保留首轮真实错误。Git 子命令及各自 exit 在 review.json，均为 0。

证据范围：本目录 probe.py/review.json/review.md；合成 fixture 仅在本目录临时子目录创建并自动清理。未修改源码、原 tests/config、ROOT PWF 或公司执行包。0 GET / provider / model 调用与费用。

工具诊断：CodeGraph 对隔离 tree 未初始化，按卡读取已定位文件；默认沙箱 Git 的 work-tree 错误保留于 JSON，require_escalated 只读 Git 成功，未变更 Git 配置。

限制：d3 精确 CI success 仅覆盖 DOCX 修复；本 selector 新 HEAD CI 尚待正常 commit/ff/push 后观测。selector 局部验证不能代签 full CI。

STOP：此单一集中节点已完成，不增加审查门。
