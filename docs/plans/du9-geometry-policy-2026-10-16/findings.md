## 独审发现根因及修复 — 2026-10-17

独立agent /root/du9_policy_final_review 对30df8eae公开入口真实复现：新section_rules浅拷贝绕过旧_sections深拷贝，调用者改aliases/path/questions可污染全局catalog并影响后续公司profile。P1已在原registry投影处恢复每section deepcopy，统一保护全部嵌套值；新增family/fallback/overlay × 四字段12个跨调用/全局catalog不变回归，测试失败也隔离被污染catalog，避免掩盖串扰。独立首次失败收据reviewer-initial-probe.json保留。

P2：原IR公开回放仅有标题和泛业务正文，真实route是generic；已用已有CN_IR_QA问答原文结构，并为全部12类回放增加expected_family强断言（unknown None）。未改生产路由或放宽原测试。修复后集中626PASS/11SKIP、10.48秒，ruff绿，等待同一独立agent对最终delta复核；614是修复前版本，不能合并计数。

---

## ROOT B实现与源数据维护 — 2026-10-17

A真实RED补齐：正常主机隔离Temp为55FAIL/1PASS；首次沙箱为43FAIL/1PASS/12ERROR（Temp创建失败）均保留。旧wire基线SHA在写实现前冻结。第一次B集中282PASS/1FAIL：新增测试helper给定增无实际区分正文而resolver正确保守fallback，修夹具为实际定增标题，不改变生产路由或旧测试。

发现catalog是由既有docs/review/deliverables/families和reading_defaults生成，直接改reading_catalog会被导入覆盖/--check报漂移。ROOT作为集成者将同一typed字段及章节变体同步到这些既有设计源数据和fallback defaults；不改导入工具、不删校验、不新增第二runtime配置。此为必要的数据维护范围补充，不进入PLANNER文件/工区。原24family仍24，旧15profile wire逐字保持；新解析视图带family_id/version与geometry_intent，actual adopted组件和section进入既有因果摘要。

A假设按原接口纠正：完整SHA64非强行截断16；空路径保持[]且意图unknown，不使用字符串unknown替代数组；同路径不同aliases合法，仅完整相同rule_key拒绝；MD&A混合经营表允许on_candidate，行政priority1及纯电话会不自动fine。编译器仅验证/投影已解析policy，不关键词匹配、重路由、读文件、分配预算或猜事实。

---

# DU9-CWP-GEOMETRY-POLICY — 调查

## 0. 状态

- A：进行中（行为RED + 独立期望已冻结，未运行业务测试）。
- B：未开始。
- C：未开始（强制独立审查agent）。
- 工作目录：`C:/Users/郑曾波/Projects/company-wiki-du9-geometry-policy`。
- 分支：`codex/du9-geometry-policy-20261016`。
- 基线：`bf160c8e3fd8b9620f6bbc891ba448fd5647e388`（已读 HEAD `68807088` 仅含 ROOT 落地的种子 commit，无业务改动）。
- 未运行任何业务测试；不能称组件或生产 PASS。

## 1. 白名单与范围（独立复核）

白名单（construction_card.md 与 INTERFACES.md 一致）：
- `src/company_wiki/document_understanding/profiles/{reading_catalog.json, registry.py}`。
- 新增 `profiles/geometry_policy.py`（必要导出可改该目录 `__init__.py`，仅导出本接口）。
- 新 `tests/unit/du9_geometry_policy/` 及同名专用 fixture 目录。
- 自有 `docs/plans/du9-geometry-policy-2026-10-16/`。

排他边界（INTERFACES.md 第 27-28 行，POLICY 不实现调度或章节匹配）：
- 不得改 `geometry_intent` 调度器、strategy_binding、structure、source_catalog、automation、旧 gold、CI、hooks。
- 不读取公司目录/配置文件/网络/clock；不调用真实供应商；不写穿生产原件或配置。
- 不另建 provider 配置、模板引擎、关键词词典或技能分支。

## 2. 24 family 实测枚举（已读 reading_catalog.json，无修改）

下面以 family 为单位列出实际 section_role/priority/heading_path/aliases 摘要（手工核对，9 维度几何：discover ∈ {on_tabular_evidence, context_only, none, unknown}、fine ∈ {on_candidate, explicit_only, unknown}、demand_class ∈ {operating, project, mixed, context, administrative, unknown}）。

### 2.1 经营/募投/混合附注/风险/行政/未知映射

| family | regime | sections (role, priority) | 几何请求意图（独立判断） |
|---|---|---|---|
| cn_annual_report | cn_exchange | business(1), industry(2), management_discussion(1), operating_metrics(2), outlook(1), risk(2), financial_notes(3), administrative(3) | 经营 on_candidate/on_tabular_evidence; industry context_only; management_discussion mixed; outlook context_only; risk context_only; financial_notes on_candidate/混合附注（保留按表候选申请）; administrative unknown（priority=1 误读陷阱，下同） |
| cn_interim_report | cn_exchange | management_discussion(1), business(1), operating_metrics(2), outlook(1), risk(2), financial_notes(3) | 同上但范围更窄；财务附注仍允许按表候选 |
| cn_quarterly_report | cn_exchange | management_discussion(1), business(2), outlook(2), financial_notes(3) | 季度披露短；季报 operating_metrics 未列，必须保守 unknown |
| hk_annual_report | hkex | business(1)+business(1)（重名重 role）、operating_metrics(1)、management_discussion(1)、outlook(1)、risk(2)、financial_notes(3)、administrative(3) | 两条 business rule_key 必须互异；HK MD&A 与 business-review 是同一节点两套 heading_path 根，"业务回顾及展望"已存在 |
| hk_interim_report | hkex | business(1)+business(1)（重名）、operating_metrics(1)、management_discussion(1)、outlook(1)、risk(2) | 同 hk_annual_report；半年报期 risk 风险因素 |
| sec_10k | sec | business(1), operating_metrics(1), risk(2), management_discussion(1), financial_notes(2), outlook(2), administrative(3) | Item-based；risk 与 MD&A 都是 1/2 优先级，priority≠fine |
| sec_10q | sec | management_discussion(1), business(1), operating_metrics(2), financial_notes(2), risk(2), administrative(3)+administrative(3) | 两个 Part；Part 风险因素在 Part II |
| sec_20f | sec | business(1), industry(2), management_discussion(1), outlook(2), risk(1), financial_notes(3) | 风险因素 pri=1，Item3D 与 Item3 都需覆盖 |
| prospectus_cn | cn_exchange | business(1), industry(1), operating_metrics(1), fundraising(1), risk(2), management_discussion(3), financial_notes(2) | 募投 on_candidate；财务附注按表候选 |
| prospectus_hk | hkex | business(1), industry(1), operating_metrics(1), outlook(1), fundraising(1), risk(2), financial_notes(2) | "未來計劃及所得款項用途"已收录 |
| prospectus_us | sec | business(1), industry(2), risk(1), management_discussion(1), fundraising(1), outlook(2), administrative(3) | risk 与 MD&A 都是 1；Use of Proceeds 已覆盖 |
| offering_cn_convertible | cn_exchange | fundraising(1), business(1), operating_metrics(1), financial_notes(2), risk(2), administrative(3) | **缺口**：aliases 含 "募集资金运用"，heading_path 根仅 "募集资金投资项目/本次募集资金投资项目/本次发行募集资金投资项目简介"，缺 "本次募集资金运用" 根变体 |
| offering_cn_equity | cn_exchange | fundraising(1), business(1), operating_metrics(1), fundraising(1)【第二条重复 role】, risk(2), financial_notes(2) | 同一 family 出现重复 rule_key 风险，需以稳定 SHA 区分；heading_path 已含"募集资金运用" |
| offering_feasibility | cn_exchange/other | business(1), fundraising(1), operating_metrics(1), risk(2) | 募投可研；project-class |
| project_change_notice | cn_exchange/hkex/other | fundraising(1), business(1), operating_metrics(1), risk(2) | 募投变更；变更前后对照属 project |
| results_release | sec/hkex/cn_exchange/other | business(1), management_discussion(1), operating_metrics(1), outlook(2), administrative(3) | 业绩快报含表格；on_candidate |
| earnings_call_transcript | sec/hkex/other | management_discussion(1), questions(1), outlook(1), operating_metrics(2), administrative(3) | Q&A explicit_only；管理陈述 context_only |
| investor_qa_record | cn_exchange/hkex/other | questions(1), business(1), operating_metrics(2), outlook(2), administrative(3) | 互动记录 explicit_only |
| investor_presentation | sec/hkex/cn_exchange/other | business(1), operating_metrics(1), outlook(2), financial_notes(2) | 路演 on_candidate；PPT 不强 fine |
| secondary_research | other/unknown | business(1), industry(2), outlook(3), risk(2) | 第三方研报；研报数字不是发行事实 |
| administrative_document | cn_exchange/hkex/sec/other/unknown | administrative(1), business(2) | **priority=1 ≠ fine**：行政件本身只触发 context_only/none；fine 仅在 business role 才允许 |
| container_attachment | sec/hkex | administrative(1), business(1), operating_metrics(2) | 8-K 外壳；Item/Exhibit 优先 native |
| event_response | cn_exchange/hkex/sec/other | business(1), questions(1), operating_metrics(2), risk(2) | 监管问询函 explicit_only |
| lifecycle_revision_overlay | all | unknown(1) | 修订说明；unknown 默认 |
| generic/fallback | unknown | business(2), management_discussion(2), risk(2), unknown(3) | unknown 默认 discover/none |

### 2.2 关键不一致（已识别，尚未修改）

1. **金禾可转债"本次募集资金运用"**：offering_cn_convertible.fundraising aliases 含 "募集资金运用"，但 `heading_path` 根只到 ["募集资金投资项目","本次募集资金投资项目","本次发行募集资金投资项目简介"]。原生书签第八章 "本次募集资金运用" 物理页 223 不能仅靠 alias 命中 root；需补正为 heading_path 根变体而非用 flatten 抹掉。
2. **同名重 role（rule_key 冲突）**：hk_annual_report 与 hk_interim_report 均出现两条 `section_role="business"` section（priority=1 同），只能由"完整 section 规则内容 SHA"作 rule_key，不能只用 role。INTERFACES.md 第 13 行已规定。
3. **priority=1 ≠ fine**：cn_annual_report.management_discussion(pri=1)、administrative_document.administrative(pri=1)、hk_annual_report.business(pri=1)、offering_cn_convertible.fundraising(pri=1) 等多组均 priority=1，但只有 project/operating 类 section 真正需要 fine 扫描；行政件 pri=1 永远 context_only/none。policy 编译必须把这两类区分。
4. **财务附注 on_candidate 保留**：cn_annual_report.financial_notes(pri=3) 与 offering_cn_*.financial_notes(pri=2) 的"客户/RPO/销量"是按表候选申请的真实场景，不能因 pri=3 而强制 none。
5. **季度披露短**：cn_quarterly_report 未列 operating_metrics，但实际季报常含；必须保守 unknown 而非 none。
6. **重复 rule_key 风险**：offering_cn_equity 含两条 `fundraising` 重复 section（按 family 1=fundraising+2=fundraising），互不覆盖内容但 rule_key 必须基于完整规范 SHA。

## 3. 行为 RED（首次失败，独立手算期望）

测试场景与期望以 INTERFACES.md §POLICY → PLANNER → ROOT 为准，独立手算每条：

### R1. 输入只读，无副作用
调用 `compile_geometry_policy(resolved_profile)` 不读取公司目录、配置、文档、网络、clock；同一输入必出同一结果。

期望：调用两次同一输入 → JSON 完全相等（哈希可复算）。

### R2. 必须输出 typed `geometry_intent`
对每条 section_rule 必须新增 `geometry_intent` 字段，缺省 `{discover: "unknown", fine: "unknown", demand_class: "unknown"}`。
枚举值白名单：`discover ∈ {on_tabular_evidence, context_only, none, unknown}`、`fine ∈ {on_candidate, explicit_only, unknown}`、`demand_class ∈ {operating, project, mixed, context, administrative, unknown}`。
非法值（如 `discover="on_table"`）→ 显式 `DiagnosticError`。

### R3. priority=1 ≠ fine 强制
cn_annual_report.management_discussion(pri=1) 与 hk_annual_report.business(pri=1) 的 fine 必须区分；administrative_document.administrative(pri=1) fine 永远不允许 on_candidate。

### R4. rule_key 来自完整规范 SHA
两条同 role 业务 section（如 hk_annual_report 双 business）必须产生互异 rule_key；rule_key = sha256({family_id, version, role, full heading_path, full aliases, priority, questions, geometry_intent}) 截断 16 字符。

### R5. 缺字段保守 unknown
缺 heading_path、缺 questions、缺 aliases → 编译仍允许，但相应字段替换为 "unknown"；不抛出。

### R6. 冲突与 malformed
两条同 family 同 role 同 heading_path 但 aliases 不同 → 显式 `DiagnosticError(GEOMETRY_POLICY_DUPLICATE_RULE, ...)`。
section_role 不在白名单 → `DiagnosticError(GEOMETRY_POLICY_BAD_ROLE)`。
heading_path 不是 Sequence[Sequence[str]] → `DiagnosticError(GEOMETRY_POLICY_BAD_PATH)`。

### R7. 不变式：旧 wire 不被污染
`profile_wire()` / `get_profile()` 输出仍不包含 `geometry_intent`，否则既有 195 测试 FAIL。policy 编译只发生在 `resolve_reading_profile` 之后的层；纯函数。

### R8. Jinhe CB 缺口独立手算期望
现有 `offering_cn_convertible.fundraising.aliases` 含 `募集资金运用`，但 `heading_path[0] == ["募集资金投资项目", ...]`。
政策编译后该 section_rule 必须保留 `aliases=["募集资金运用", ...]` 与一条**新增** heading_path 根 `["本次募集资金运用"]`；否则原生书签第八章物理页 223 不能 root 命中。补正由 reading_catalog.json 实际数据驱动，不在 POLICY 内做 flatten fallback。

### R9. 行政 priority=1 编译产物
administrative_document.administrative(pri=1) 经编译 `geometry_intent={discover: "context_only", fine: "unknown", demand_class: "administrative"}`。rule_key 稳定 SHA。

### R10. HK 双 business section rule_key 互异
hk_annual_report 第 1 条 business (aliases 含 ["Business Review and Outlook","業務回顧及展望","业务回顾及展望"], heading_path ["業務回顧及展望","業務回顧","Management Discussion and Analysis"], pri=1) 与第 2 条 business (aliases 含 ["業務","業務","BUSINESS"], heading_path 同上 root 变体, pri=1) → 两条 rule_key 不同。

### R11. 财务附注按表候选（不是 none）
cn_annual_report.financial_notes(pri=3) → `geometry_intent={discover: "on_tabular_evidence", fine: "on_candidate", demand_class: "mixed"}`（保守可调；手算此处取 mixed）。

### R12. 不增字段污染旧 gold
不写 `signed/authorized` 字段，不写入文件/clock/config/网络；不返回新 IO；profile_version 必须用既有 digest 协议拼接。

## 4. 已知限制（不掩盖）

- A 阶段未运行 pytest，也未跑 fixtures；不宣称组件 PASS。
- 真实补正"本次募集资金运用" heading_path 变体属数据改动；与 policy 模块并行，须以 reading_catalog.json 数据更新为前置，本卡允许同 PWF 内一次提交，但提交时分两 commit（catalog 数据 + 编译模块）。
- A 阶段对 PLANNER/ROOT 不写；仅冻结 POLICY 输入/输出期望。
- 旧 gold 195 条 tests/unit/document_understanding_profiles/ 必须全绿。

## 5. 不写实现，仅冻结期望

A 阶段提交：仅本文件 + 必要 fixture 文件与 RED test（仅 `tests/unit/du9_geometry_policy/` 与本 PWF）。不修改 profiles/registry.py、不修改 reading_catalog.json、不新增 profile。
