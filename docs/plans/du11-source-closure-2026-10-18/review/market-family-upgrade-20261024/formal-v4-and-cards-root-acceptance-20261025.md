# Formal-v4 与独立施工卡 ROOT 验收（2026-10-25）

## Formal-v4：工程流程通过，内容与 RF 验收仍开放

- 样本：Microsoft FY2025 10-K；原件 SHA-256 `99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe`，8,158,067 bytes；gold SHA-256 `4dd0875a81b82508cf02f874e80df6d712da2ee756a26f44feee5f5f7e28a2a8`。运行前后均未变；没有下载或翻译。
- 正式 provider 尝试：恰好 1 次 POST，HTTP 200；累计估算 17,666 tokens / $0.007102。母账从 1,765,712 tokens / $0.717734 变为 1,783,378 tokens / $0.724836。原有未知费用保留，无自动重试。
- 运行级验收：摘要产物持久化；真实 activation recovery / cache 恢复通过；FF 复用既有原件、下载数为 0；RF 已读取同一 SourceRef；隔离临时数据湖已清理。运行器的 `formal-summary.json` 与 `overall.json` 的 `PASS` 只表示受限生命周期链按计划完成。
- 解码器根因：MiniMax 返回的 ranking JSON 带精确 `schema_version=narrative-model-request/6`，原 decoder 将其误判 `RANK_INVALID`。当前允许的只有 `decisions` 及精确常量 `schema_version` / `type=json_object`；仍拒绝未知根字段、错误常量、额外决策字段、重复/未知 task ID 和非法枚举。对所捕获响应离线重放后为 50/50 唯一 task ID、没有缺失或多余项，coverage 完整。原响应 SHA-256：`f86a2e64051022871bb269970178dddeb9ef9e588eab3caa00a9ccb6b63bf6d2`。没有新增 provider 请求。
- Decoder 验证：`tests/unit/test_narrative_extractive_runtime.py` 19 passed；该文件与 `tests/test_phase_c_activation_recovery.py` 合计 24 passed / 28.36s，精确 pytest 临时目录 `.tmp-phasec-focused` 已清理并核实不存在。独立 follow-up 审查确认允许字段仍为封闭列表，且测试覆盖精确 schema echo、正确/错误 type 与未知顶层键；结论 PASS。审查所见 SHA-256：源码 `f93b4925b72162d352d5a17d62782207b8409c2683372a319a0dea31be270af3`，测试 `94d2393fa09de890ec6ebbf46d6a51228d837619ef56f16cf10a4d8fb9b5734`。
- 内容/RF 验收仍 OPEN：选材为 112/484 candidates，selection=`partial`，314 个候选单元 deferred；layout `complete=false`，0 pages / 0 tables；摘要有 43 条 claim，43 条均为 `company_statement` + `uncertain` + `needs_review`。RF receipt 为 `not_consumed` / `needs_review`。Ranking 修复仅修正排序响应解析，不能把不完整选材或未采用的待审 claim 改记为完整业务摘要。
- 下一步：先从根因处理“112-span 限额、未分配单元和 incomplete layout 导致下游不消费/低质量摘要”的选择与分批策略；先用捕获响应和离线夹具验证，只有确定真实业务改善且预算/原件指纹通过预检后，才考虑新的有界真实摘要。不得把本次运行报告的 `PASS`写成真实内容质量 PASS。

完整运行证据位于 `.planning/shared-reading-production/du11/live-us-10k-m31-formal-v4-20261025/`；付费响应、请求、母账与启动恢复子收据均留在隔离运行目录，不在本文件复制原文。

## 三张独立施工卡：ROOT 接收交付，不等于跨仓并线

| 卡片 | 冻结代码 SHA / 当前作者分支 tip | ROOT 接收依据 | 边界 |
|---|---|---|---|
| QA-RAG-SAFE-REBUILD | `c762e4de96feff3ac0f2b3d3bd3bfe9d72398f99` / `5e5f22b2d7d652738e54bbfaced1982117616c7a`（tip 后续仅文档/日志） | 最终独立 R2 `PASS-with-findings`，残留 O1/O2 仅信息项；28 focused、97 repository tests 通过；vector_db SHA 与原仓不变 | 独立仓交付已验收；此处不合并或推送外部仓库 |
| IR-REPORT-GENERATION | `e5be80c877aba61f6e2b60c587a72b7d89262f0a` / `1e84336eda1505748e5497b3910e29ba55cd43fe`（tip 后续仅文档） | R1 `PASS-with-nits`、R2 `PASS`，均绑定最终代码 SHA；67 unittest、py_compile 与 deterministic golden 通过，清理收据存在 | 作者仓无 remote；不声称已推送或并线 |
| MC-OUTPUT-INTEGRITY | `efbb51da26b98e990f97817a88e2b16bc66bb2f8` / `ecf9ae82e77d6b9629e0919dd28d581540c800b8`（tip 后续仅文档） | 最终独立复审 `PASS` 绑定代码 SHA；57 pytest、Ruff 通过；原仓 `.coverage` 保持；清理证据存在 | 作者分支尚未并线/推送；ROOT 本次只接收交付 |

ROOT 接收记录基于每卡 handoff、最终独立审查、测试/清理收据与冻结版本相互核对。各卡仍保留在独立作者 worktree/branch；跨仓发布需各自项目维护者按其计划处理，本项目不跨仓写入。
