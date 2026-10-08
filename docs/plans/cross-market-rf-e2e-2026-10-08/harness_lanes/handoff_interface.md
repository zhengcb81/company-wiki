# 三线共用交接格式

这是结果记录格式，不是新的人工许可或任务状态库。各 harness 在本线允许的 docs 目录交付下面五个文件；MAIN 最后读取这些记录验收一次。

## HANDOFF.md 必须回答

1. 修的共用机制、原实测问题/最小 RED；与公司特判的区别。
2. 公共接口的实际导入路径、签名、字段、版本、一个可运行最小例；如和卡有差异，给兼容理由和 MAIN 需要改的调用点。
3. Git 基线、分支、全部交付提交、当前 HEAD、未提交文件的用途；不要带 owner WIP。
4. 单元/集成/E2E 的精确命令、退出码、通过/阻塞数和耗时；哪些是真实原件、哪些是 fake HTTP、哪些只是固定输入。不用“全部通过”隐藏 NOT_RUN。
5. 测试根的初始/结束状态、清理证明、峰值/保留字节，是否改生产配置或原件（应为否）；有收费调用则给统一账中的 reservation/settlement 引用。
6. 需要 MAIN 接线的事项和仍存在的外部限制。未实现功能不写成完成。

## handoff.json 最小结构

```json
{
  "schema_version": "cmrf-lane-handoff/1",
  "lane_id": "R6-FORMAT | R6-RF-INPUT | R6-FF-CAUSE",
  "status": "ready_for_main | partial",
  "repository": "绝对工作树路径",
  "baseline_commit": "40位SHA",
  "branch": "codex/...",
  "commits": ["40位SHA"],
  "head": "40位SHA",
  "files": [{"path": "仓内相对路径", "sha256": "最终字节SHA"}],
  "interfaces": [{"name": "真实接口", "version": "版本", "path": "相对路径", "example": "文档/测试的相对定位"}],
  "tests": {
    "red": [{"command": "精确命令", "exit_code": 1, "mechanism": "为何应失败"}],
    "green": [{"command": "精确命令", "exit_code": 0, "passed": 1, "seconds": 1.0}],
    "e2e": [{"command": "精确命令", "mode": "offline | real_original | live", "status": "PASS | BLOCKED | NOT_RUN", "report": "小结果相对路径"}]
  },
  "isolation": {"test_roots": [], "initial_state": "描述", "restored": true, "retained_bytes": 0, "originals_changed": 0, "production_configs_changed": 0},
  "model_calls": 0,
  "limitations": [],
  "main_actions": []
}
```

字段填写实际值，不把模板的示例数字复制成结果。预算额度是全项目累计 USD20 / 2,000,000 tokens；这三张卡默认不用收费模型，也不分给每条线一份 USD20。需要真实模型时先把用途交 MAIN，由统一配置/账本执行，不新建凭证或第二本费用账。

## 操作共识

- 在指定独立工作树自己的 `codex/` 分支施工；可提交/推该分支。MAIN 独占主线合并与安装目录同步。不要 reset canonical 主目录，不碰 Dayu、StockInfoDLSimple、IQS 等其他工程。
- 三个工作树已创建，基线/干净状态见 worktrees.json。CWP/RF 使用稀疏检出，避免复制原件和历史缓存；在 CWP 工作树先执行 `git sparse-checkout add docs/implementation/cmrf-format-normalization-20261008`，以便登记自己的 docs。如测试确需别的**只读代码**可 add 对应目录，不扩写范围，不检出 companies/output/assurance 历史资料树。新解析子目录在已检出的 src/tests 下正常创建即可。
- 共享施工卡在 canonical CWP 的绝对路径 `C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/harness_lanes/`，三个工作树开始SHA不要求含这轮新卡。只读该目录；本线PWF仍写自己的允许 docs。若使用planning-with-files hooks，将 PWF_PLAN_ROOT/任务选择指向本线目录，不让自动恢复覆盖canonical或另一条线的计划。
- 遵守仓内 AGENTS/技能，结构问题先 CodeGraph；不要凭名字猜文件。当前卡和共享根因计划优先于过时的历史 TODO。无法确认的新接口先报告，不扩大写目录。
- 测试必须独立 TMP，不写生产配置；已有原文只读，测试副本退出恢复。只清本次解析过绝对边界且有 ownership 的根；原样就不存在的根，最后仍不存在。
- 不改已有金额/事实 oracle 来迎合实现，不固定 seed、不放宽 hash/身份/期间、不得掩盖未知发布日。合理的契约升级须说明数学或官方依据及新的反例。
- 重测试只在集中节点；不加每 commit 的网络/大模型/全量覆盖门。不提交 PDF、全 MD、拆页图片、虚拟环境、密钥或庞大执行缓存。
