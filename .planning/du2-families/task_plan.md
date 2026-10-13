# DU2-FAMILIES 施工计划（PLAN_ID=du2-families）

- 任务卡：docs/plans/document-understanding-2026-10-13/review/cards/DU2-FAMILIES.md
- 工作目录：C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/families
- 分支：codex/du2-families-20261013
- base_sha：5a297244549d54c34f382835b876ec3d181fcd24（记录时工作树 clean，sparse checkout 17%）
- 目标：把各类文档"如何识别、先读什么、哪些限定不能丢"做成可导入唯一策略库的数据规格与证据
  （du2-family-spec/1 + du2-reading-case/1），不改 router/selector，不接生产，不新建 skill。
- 可写范围：docs/plans/document-understanding-2026-10-13/review/deliverables/families/**；.planning/du2-families/**
- 禁写：原 profiles/structure/benchmark/ROOT 模块、FACETS、LAYOUT、共享 PWF/接口/config/CI/安装/其他仓。

## Goal

在 deliverables/families/ 交付 README、index.json（du2-family-index/1）、records/（每形态一个 du2-family-spec/1 记录）、
cases/（du2-reading-case/1 真实短引文+合成反例）、tests/（仅结构不变量）、coverage_matrix.md、acquisition_requests.json，
并写 .planning/du2-families/handoff.json + handoff.md；包内 pytest 全绿后提交本分支，停止等 ROOT 接收。

### Phase 1 上下文与基线记录（Status: complete）
- 读 AGENTS、review/report.md、strategy_matrix.md、review/INTERFACES.md、原 design.md/INTERFACES.md、sample_manifest.json。
- 记录 base_sha/status；建立本 PWF 三件套。
- 核对 20 份开发样本原件可读性与 SHA。

### Phase 2 节点A：两个代表规格+正反例+覆盖清单（Status: complete）
- 先写测试记录 RED（16 failed/14 passed，progress.md#RED），再落 cn_annual_report、sec_10k 两份代表记录与真实 case（中微公司年报、微软10-K）。
- index.json 覆盖清单把每个文档形态独立登记 spec/evidence/integration 状态与 gaps（28 行）。

### Phase 3 节点B：全数据一致性与反例（Status: complete）
- 覆盖矩阵其余形态：定期年/半/季（A/H/US）、A/H/US 招股、定增/可转债/可研/项目变更、IR/call、release/deck、
  容器/附件、摘要/更正/制度、问询与重大经营事件、研报/新闻/政策按需。
- 多市场/生命周期变体；10-K/20-F/10-Q Part 不混；同 role 别名可组合不丢；重复规则去重。
- pytest 全绿。

### Phase 4 节点C：原文对照核实与交接（Status: complete）
- 真实 case 短引文/原SHA/定位/关系逐条对照原文复核（c_node_quote_check.py：97 项 0 失败）；两家不同公司（中微公司 A 股、名创优品 H 股，另微软/TAL/VRSK/腾讯佐证）验证可复用规则。
- 未覆盖清单、恢复/范围检查（20/20 原件 SHA 不变、无 scratch 残留）、handoff.json/handoff.md 已写。

## Decisions Made
- 角色只用 DU/1 角色枚举（business/industry/management_discussion/outlook/risk/operating_metrics/fundraising/financial_notes/questions/administrative/unknown），不新增可执行 role。
- case 的 locator 一律填 null + page/line + exact_quote（quote anchor 交 ROOT 解析为正式定位），不伪造 SourceRef。
- 识别信号只用 literal_phrase / metadata_equals（field 限 title/regime/form_type/declared_kind/mime_type/language/revision），不写 regex/DSL，不含公司名或固定页码。
- 摘要/修订/补充/更正作为正交修饰单记录处理，不为每个 family 复制策略。
- 自动测试只查结构不变量；语义反例标 NOT_RUN_ROOT_INTEGRATION，真实含义对照集中在节点 C。

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| case_id 含连字符被 ID_RE 拒绝（测试过严，非数据错） | 1 | 测试改用 CASE_ID_RE=[a-z0-9_-]*，记录于 progress.md#RED |
| contains_forbidden_token 把 “Capitalization” 误判为公司名 TAL（子串匹配） | 1 | 拉丁词改整词边界匹配，中文保持子串 |
| c_node_quote_check 的 WORKTREE_ROOT 层级算错（parents[6]→docs） | 1 | 改 parents[7]，并复跑通过 |
| bindings.local.json 中 us-10k 路径 “\r” 被 JSON 解析成回车 | 1 | 路径改双重转义，复跑通过 |
| 同一消息并行 write 有 4 个文件未落盘（工具报成功但文件缺失） | 1 | 重写缺失文件并逐一核对存在性；后续写入串行 |
| 引文与原文差在 PDF 换行处空格（逐字节引文不可行） | 1 | 确立“剔除空白等价”比对规则并写入 README/handoff；1 处全角冒号引文按原文修正 |

## Next Step
Phase 1-4 全部 complete；提交本分支后停止，等待 ROOT 接收（不合并主线）。
