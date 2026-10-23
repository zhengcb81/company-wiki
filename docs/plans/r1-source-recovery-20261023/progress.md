# W11-CWP-SOURCES 进度

## 2026-10-23 ROOT交包准备

已创建独立稀疏工区、核实branch/base且实际检出，写START_HERE与本独立PWF。此前no-checkout工区仅有.git的问题已在派发前修正，初始产品代码无改动。施工本身尚未开始；A/B/C均pending。无需等ROOT逐小步签收。

最终必须调用独立agent审查，修复及复审后按固定handoff接口交ROOT，不能把开工包已准备当任务完成。

## 2026-10-23 A 阶段实施（本 harness）

- 核对工区：HEAD `0d7ada21`（dispatch.json start_head 一致），tree clean，两模块 `__file__` 落本工区 src。✅
- 实读卡片/INTERFACES/INPUTS/模板 + W11 原卡 + fetch.md + faa5bf… 全套 capture + events.jsonl + web_discovery.json。✅
- 486789B 正文有界查找完成：两条根内 0 命中（精确大小、400–600KB 全 hash、sqlite/WAL needle、catalog 90 sources）。`body_available=false`，如实进 evidence_inventory。✅
- 基线回归：7 passed（RED_not_observed）。✅
- PWF task_plan/findings 更新为本线实测事实。✅
- 待办：evidence_inventory.json、期望表、B 缺陷假设中性验证、补丁、离线 E2E、独审×2、delivery 交付、commit/push。

## 2026-10-23 B 阶段实施

- 中性 fixture 缺陷验证（13 组 probe，输出见 findings A5 表）：证实 3 项确定性内部缺陷、其余 17 项行为如实记录通过。✅
- 产品补丁（只改 `official_discovery.py` 三个定位点，无共享分类器/transport/DTO 改动）：
  1. `_TRANSCRIPT_TITLE_TOKENS`：transcript 身份要求 call/transcript 线索，"earnings" 一词不再覆写 kind；
  2. `_MATERIAL_TITLE_TOKENS`：候选要求 title 带材料文档线索；文件后缀不再单独放行；
  3. `_NON_MATERIAL_TITLE_TOKENS`：法律/站点导航（privacy/terms/cookie/contact/sitemap 等）永不做候选。
- 新增 `tests/integration/test_official_discovery_offline.py`：26 测试，覆盖卡 §5 最低矩阵全部行（分类正负控、时间/主体、URL/去重、页面载荷、有界/公共入口、CLI subprocess 双 issuer 交换语义）。
- 兼容性：既有 W03/CN 语义保持（notice→index_notice、会议通知→meeting_notice、可转债/招股分类不变），现有 7 个 discovery 回归全绿；补充 W03 excluded 断言强化。
- 修复过程中环境教训：subprocess env 必须 `{**os.environ, ...}`（剥离 env 会致 Windows asyncio WSAStartup 失败）。
- 状态：26 新增 + 7 既有 = 33 passed；in-session 模块 `__file__` 核验通过。
- 待办：C 阶段 E2E 清理核验、独审×2、delivery、commit/push。
