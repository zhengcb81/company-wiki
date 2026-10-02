# 叙述性证据规划：执行入口

> **2026-10-02 最新状态：**CI 主因由真实 step timing 定位：#168 job 4m33s、workflow 总计 4m37s；Contract 用例 3m30s（约 77% job 时长），Unit 11s、依赖安装 24s；此前全量 coverage 曾耗 25 分钟至 1h46。CI 与本机 push/pre-commit 收敛为同一精选契约集（11 个显式 node IDs，含 worker ownership、reader-chain、叙述抽取和既有红灯回归），保留完整 Unit，移除日常 2,120 项 portable Contract 执行及自动 coverage。新方案已由 [Actions #169](https://github.com/zhengcb81/company-wiki/actions/runs/37074907164) 验收：单 job 全绿，job 59s、workflow 总计 1m04s（比 #168 总时长缩短约 77%）。参数路由和失效的 pre-commit 标记也已修复；详情见 task_plan Phase 53 与[CI 交接卡](ci_red_handoff_2026-10-02.md)。

> **2026-09-29 入口更新：**先读[多余门禁统一清理方案](gate_and_contract_simplification_2026-09-29.md)，再读[六仓独占施工与总指挥计划](parallel_harness_orchestration_2026-09-29.md)。两页依次裁定要清理的真实代码/历史规则、各仓独立写入范围、接口与汇合测试；`task_plan.md` Phase 25 记录本轮规划状态。2026-09-28 的[跨仓总图](cross_repo_mainline_and_delivery_plan_2026-09-28.md)保留历史基线和详细施工背景，冲突时以 2026-09-29 两页为准。本项目已取消逐文件人工审批、review receipt 和常规独立签字；自动测试/完整性断言是常规依据。旧 provider policy 与人工 review 文档不得作为新实施门槛。

> 2026-09-27：F0–F5 旧库退役、G1 离线选择试点和 D0 本地只读文件/引用盘点已完成各自允许范围；检索原型现含 query-local BM25 与 pilot-only raw resolver，12 件 manifest 样本 E2E 对全部已选 evidence groups 做原件重放和 SHA/locator/text 校验。最新合并回归为 12 个检索/回源单测 + 两个隔离 E2E（P06/T02 双样本链路、12 件样本 selected-anchor/raw-replay），共 **14 passed in 130.77s**；历史全绿收据为 122.56s；`ruff check` 通过。唯一 basetemp 清理后复核不存在，`tests/e2e/.runtime/` 运行前后均不存在，样本副本、package、metrics 与临时状态随 run root 清理，测试目录恢复基线。13 条摘要草稿通过引用/角色机械校验并经实施者逐条核源，但全部仍 `needs_review`。本轮 transcript 接口审计确认当前没有可调用 MCP tool，且 filing-fetch 没有 companion request/response；G1e 需先冻结独立上游接口合同。pilot resolver 不等于正式 G2 service 或共享 consumer 放行；StockWiki strict Source Provider v1 与 pilot bundle v0.2.0 不兼容，revenue-forecast G0 未通过；invest-quick-scan 仅做可选身份映射，不读取叙述包。Worker 仍暂停。

> 2026-09-27 后续状态校正：earnings-transcripts 工作树现已有尚未提交的 transcript_api.py 与 transcript_tool.py。上段“只有 scraper.py CLI”是旧审计时点事实；filing-fetch 尚未接线，G1e 仍需正式合同和跨仓 E2E。来源/采购预算新增 [外部来源成本卡](provider_cost_and_capability_2026-09-27.md)，当前结论先不买订阅。

## 先读顺序

1. [gate_and_contract_simplification_2026-09-29.md](gate_and_contract_simplification_2026-09-29.md)：当前多余门禁清理裁定、准确代码位置和测试替代。
2. [parallel_harness_orchestration_2026-09-29.md](parallel_harness_orchestration_2026-09-29.md)：总指挥、六仓独占、接口冻结和 G-0/G-A/G-B/G-C/G-D 汇合。可单独派发：[CWP](harness_lanes/company_wiki.md)、[ET](harness_lanes/earnings_transcripts.md)、[FF](harness_lanes/filing_fetch.md)、[RF](harness_lanes/revenue_forecast.md)、[StockWiki](harness_lanes/stockwiki.md)、[IQS](harness_lanes/invest_quick_scan.md)。
3. [clean_architecture_tdd_execution_plan_2026-09-27.md](clean_architecture_tdd_execution_plan_2026-09-27.md)：L0–L7 分层、TDD 和旧 M1–M4 节点的技术背景；实施顺序以本页前两项为准。
4. [findings.md](findings.md)：10 PDF + 2 TXT 的真实样本、11 个正例、2 个负例及已验证边界。
5. [implementation_plan.md](implementation_plan.md)：项目目标、来源/证据/摘要/跨仓合同和 W0–W7 历史工作包。
6. [milestone_review_cadence.md](milestone_review_cadence.md)：关键自动化测试节点与何时重跑的规则。
7. [execution_cards.md](execution_cards.md)：W/N/D 实现范围与失败关闭断言。
8. [worker_parallel_execution_plan.md](worker_parallel_execution_plan.md)：Worker 多文档并发的详细实施入口；[worker_parallel_recovery.md](worker_parallel_recovery.md) 只留故障背景。
9. [test_acceptance_plan.md](test_acceptance_plan.md)：测试分母与对抗场景；`review_protocol.md` 只列机器可判定的放行条件，不要求人工 reviewer。
10. [task_plan.md](task_plan.md)、[progress.md](progress.md)：本计划状态与本轮调查记录。
11. [ci_red_handoff_2026-10-02.md](ci_red_handoff_2026-10-02.md)：给后续模型的 CI 根因、当前未提交文件、可复用命令和单一最终验收点。
12. [g1_summary_source_support_audit_v1.md](g1_summary_source_support_audit_v1.md)：13 条人工摘要逐条来源支持、时点、语气、角色审查；不构成独立审稿签字。
13. [end_to_end_test_plan.md](end_to_end_test_plan.md)：旧 G1–G4 样本与隔离运行目录；当前节点对应关系见并行总计划。
14. [early_catalog_retirement.md](early_catalog_retirement.md)：46 GiB 旧主库提前退役的历史实施卡和实际收据。
15. [raw_disposition_plan.md](raw_disposition_plan.md)：旧 D0–D5 的原文处置研究；当前原始下载文档全部保留。
16. [stepwise_space_budget.md](stepwise_space_budget.md)：逐步新增/释放空间、临时峰值、旧库压缩计数与待试点变量。
17. [implementation_run_2026-09-26.md](implementation_run_2026-09-26.md)：F0–F5 实际运行卡和空间释放收据。
18. [cross_project_coordination_2026-09-26.md](cross_project_coordination_2026-09-26.md)：与 revenue-forecast 的源码/数据交叉、消费者 SHA 门禁和唯一 owner 约束。
19. [d0_inventory_receipt_2026-09-27.md](d0_inventory_receipt_2026-09-27.md)：D0 本地只读文件与旧引用盘点。
20. [provider_cost_and_capability_2026-09-27.md](provider_cost_and_capability_2026-09-27.md)：SEC/FMP/Koyfin/Seeking Alpha 的来源、月调用预算及采购闸门。

## 实施时的硬边界

- Worker 当前暂停；自动测试通过后，按用户已授权的任务范围实施，不另索逐 job/逐文件授权 receipt。Worker 只有在持久任务、恢复、资源上限及原件保护等自动技术断言通过后才可运行。
- R4 C05 已指定**唯一现有**持久 job/attempt 入口。实施者先检查 `src/company_wiki/automation/` 实际状态；不得在 catalog 再造任务表，也不得直接多开现有 Worker。
- 按 `N0→N1→N2→N3→N4→N5→N6` 实施 Worker：先原子领取/完成与恢复，再让不同文档并发解析/模型计算，catalog 单写短事务；多 agent 核验是后续可选功能。
- 旧实施卡中的 SQL/API/CLI 有些已实现到 E4.8，有些仍是设计；实施者先核当前代码与测试，不按历史状态重做。生产并发与跨仓消费仍须在 G-C 等大节点验证。
- 小步骤跑受影响测试；G-0/G-A/G-B/G-C/G-D 各跑一次对应真实 E2E 并记录自动结果。质量、费用、吞吐、来源身份或原件保护断言失败时，只暂停受影响能力；无需独立人工复审或签字。不能调低阈值、删除负例、以 mock 充真实提速。

## 当前实际结论

- 真实样本共 10 PDF + 2 TXT，覆盖年报、半年报、季报、招股、定增/可转债、投资者关系和英文电话会。v16 主样本选出 **1,289** 个 evidence span，1,289/1,289 locator 回读、18/18 锚点通过；分类为 2 selected、6 partial、2 skipped、2 needs_review。P09/P10 的跳过只代表不做业务动态摘要，不代表可删原文。v11 回归集 401/401 回读、5/5 锚点通过；这是回归集，不是盲留出集。
- 13 条人工草稿在 v8 通过引用/角色/语言/问答关系机械校验，并逐条对照原件做来源支持审查；支持审查记录在 [审计文件](g1_summary_source_support_audit_v1.md)。IR 表格 locator 不稳定、英文 T02 的上下文推断等项目仍待独立审稿；**所有草稿保持 `needs_review`**。未调用 LLM/API。
- 主样本序列化 evidence JSON 为 **542,820 B**（原文 52,196,853 B 的 **1.0399%**）；四件回归集为 **202,661 B**（原文 14,939,109 B 的 **1.3566%**）。该数字不包含完整生产 DB/索引布局，不是实际持久增量、最终摘要体积、总召回率或空间回收承诺。
- `20260926T170825Z-4a9c67e1` 的 F0–F5 已完成：旧 49,677,344,768 B DB → 新生产 3,055,796,224 B active-only DB，保留 6,198,704,362 B 完整 zstd 备份；两轮间隔 658 秒的烟测通过。F5 删除旧主文件，同卷准备前到清理后实际可用空间净增 **37.630 GiB**。按用户要求没有完整备份落盘恢复演练；F3 未运行真实下游业务流程。详见 [本轮收据](implementation_run_2026-09-26.md)和 [实际空间账](stepwise_space_budget.md)。
- D0 的 F5 后复测：`.source_catalog/`、`source_manifests/`、`companies/` 当前逻辑长度合计 **39.744 GiB**；这仍含 6.199 GB 压缩回滚包、5.207 GB 退休证据归档、2.826 GB derived 与全部原文，不代表可继续删除的容量。catalog SHA 识别的本地双路径重复候选理论上限约 **98.8 MB**，须经 D1–D4 才能清理。见 [D0 盘点收据](d0_inventory_receipt_2026-09-27.md)。
- 当前 Worker 仍 paused，且不能直接多开旧 Worker：`service.py` 长锁与旧 `LLMClient` 状态会损害吞吐和恢复。后续复用 R4/Worker v5 的唯一持久 job/attempt 入口，G3 一次集中验证多文档 1/2/4 在途、故障恢复和共享费用限流；不逐 N 卡重复审查。
- revenue-forecast 的 I-05-C/I-06-A 与未来 DAG/producer/job 状态有真实重叠。最新可见为 Round 120 / REMEDIATION_REGISTER §161；I-05-C 有 `accepted_scoped` 但保留 producer、consumer owner、事件 schema 开放项；I-06-A 的最新 `accepted_scoped` 限于 store-side lifecycle，调用/消费和跨进程项仍在。G0 仍关闭；只继续不写共享路径的离线工作。见[跨项目协调](cross_project_coordination_2026-09-26.md)。
- `skipped_*` 只表示不用做业务切片。旧 raw/derived 的物理删除还需 D0–D5 的处置合同与 G4 **批次**审查；执行器对每个待删文件在真正删除前只做一次完整 SHA/路径核对。当前未删除任何 raw。
