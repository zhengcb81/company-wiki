## ROOT接收更新 — 2026-10-16

ROOT接收组件验收通过，待正常提交/并线/远端；不是生产摘要接线完成。独审6类RED：partial碎片假整体数值、无观察的首格标签导致丢值、耗尽后O(rows*cells)扫描、坏格丢弃仍complete、fine页矛盾、header跨scope。隔离修复后43短测通过；逐row索引一次、排序/复制预付，耗尽尾部扫描由12万/49万/194万line变72/72/72。真实名创年报p12单parse、2表28格16值（12bound/4ambiguous），所有引用核对；2M预算用1,162,753、原件/配置SHAmtime不变，0供应商。集中557PASS/24SKIP/2FAIL均为ROOT稀疏树漏检出旧DU2资产，补既有夹具后原两项2PASS/4.03s，原失败保留，不改旧断言。六个本次作者新测试的错误首格/耗尽假设已保存原zip并纠正，旧binder/layout金标没改。全局e2e runner移入本PWF/e2e避免未来外包冲突。深页223/224因上游64页capture未覆盖，未知merged/空格/行标签及正式selection/summary/RF仍OPEN，由ROOT来源层后续解决。

**Next Step：** 正常提交并主线、可用远端发布和相关技能文件定点同步，由ROOT归总母PWF。

---

# 进度

ROOT只建立独占代码工作树与启动PWF，0原件副本/0供应商调用/0生产写入。业务测试与A/B/C均待作者实施。

- A（完成）：只读调查真实代码，findings.md A-1..A-5（字段映射表、手工期望、语义决策与反例、RED 说明）。
  首个行为红收据 `receipts/red-1-pre-implementation.log`；修正测试夹具后隐藏实现重放完整行为红
  `receipts/red-2-behavior-replay.log`（缺口/错误假设演示 3 passed，组件缺失 3 failed+6 errors）。
- B（完成）：先行为测试后实现。组件 `src/company_wiki/document_normalization/pdf_table_observations/`
  与 `tests/unit/pdf_table_observations/` 30/30 全绿（`receipts/component-tests-final.log`）；
  旧 TABLE/layout 集中回归 516 passed/24 skipped/0 failed（`receipts/old-suite-regression.log`）；
  Ruff 通过（`receipts/ruff-final.log`）。未改旧断言/金样/冻结面。
- C（完成）：`e2e/run_e2e.py` 真实原件单 parse 端到端 4 次（名创 p12、恒锋 p61/62、金禾 holdout
  p223/224、金禾附注 p25/26），逐值回切原文+SHA、原件 SHA 前后一致、Temp 全部回收
  （`receipts/e2e-*.json`、`receipts/cleanup-c.json`）。holdout 暴露上游 layout 捕获 64 页硬上限
  （真实未覆盖项，交 ROOT）。交接见 handoff.md/handoff.json。
