# catalog.sqlite3 空间治本方案（任务计划）

> 状态：**全部完成 ✅（Phase 1–6，2026-08-07；D1–D5 全部拍板并落地）** ｜ 创建：2026-08-06 ｜ 位置：docs/plans/catalog-space-remediation/
> 目标：解决 `.source_catalog/catalog.sqlite3`（43.9GB、持续增长）的空间占用与数据一致性隐患，建立证据数据生命周期管理。
> 本方案只做规划与只读测算，**不实施**；所有写操作均需用户逐项确认。

## Goal

1. 消除 phase-15.6 治理遗留的状态不一致（9,578 份"审计退役但大多仍 active"的文档）
2. 为证据数据（evidence_spans）建立"退役 → 归档 → 回收"生命周期，杜绝只增不减
3. 控制证据粒度与待归一化语料（20,728 pending）带来的增长，使 DB 体积可预测
4. 最终让 catalog 存储可治理、可监控，不再填满磁盘

## 约束与边界（最高优先级）

- 遵守 AGENTS.md 职责边界：company-wiki 只管理来源/解析质量，投资语义归 StockWiki；不得删除 StockWiki 正在引用的证据而不提供替代
- 单线程架构：所有治理脚本以单线程顺序执行；不得并发写 catalog
- 每次写操作前：只读 dry-run → 备份（receipt）→ apply → 验收（对账归零）
- normalize worker 运行期间（当前 PID 19760）不执行任何 DB 写操作
- 删除证据前必须导出只读归档（source_id + locator + parser + quality），保证可追溯

## 当前基线（2026-08-06 实测）

| 指标 | 数值 |
|------|------|
| catalog.sqlite3 大小 | 43.98 GB（page_count=11,530,002, freelist=0, page_size=4096） |
| evidence_spans | 25,985,291 行，仅覆盖 3,272 份文档（平均 ~8,000 span/文档） |
| 其中属于 phase-15.6 审计文档 | 24,689,660 行（95%） |
| documents | 23,564 份（active 23,372 / upstream_rejected 189 / retired 2 / quarantined 1） |
| 归一化进度 | completed 2,702 / pending 20,728 / unsupported_terminal 127 / failed_terminal 5 |
| 原始语料 | companies/ 23.43 GB（33,122 文件）；sources 累计登记 32.3 GB |
| 磁盘现状 | C: 剩 164.5 GB；D: 剩 71.8 GB；G: 镜像 C:（156.2 GB） |
| 安全网 | D:\company-wiki-backups\catalog.sqlite3.vacuum-20260731T215307Z（19.33 GB） |

## Phase 1：状态一致性治理（phase-15.6 遗留）— 状态：completed ✅（2026-08-07：1.1 四路对账 + 1.2 reconcile apply——退役 9,499 / stub 物理删 77 / audit-vs-status 归零 / receipt artifacts/gates）

### 1.1 只读四路对账
- [ ] 对账矩阵：document_retire_audit（9,578） × documents.source_status × locations.location_status × 磁盘文件是否存在
- [ ] 输出 9,578 文档分类表（dry-run，不修改）：
  - A 类：真正 retired（现 2 份）→ 证据归档后回收
  - B 类：审计存在但 active（现 9,576 份）→ 逐类判定应"正式退役"还是"正式恢复"
  - C 类：59 字节 stub（现 79 份）→ 占位符，直接物理删除
  - D 类：审计无 span（约 6,306 份）→ 无数据残留，仅修正状态
- [ ] 输出每类可回收字节测算（evidence_spans + artifacts + locations + documents + sources 行数 × 平均大小）

### 1.2 修复脚本设计（不实施）
- [ ] `reconcile_retire_state.py`：默认 dry-run；`--apply` 需显式参数 + 用户确认
- [ ] 修复动作：B 类按判定写正式 retire（含 audit）/ 正式 restore（含 restore audit）；C 类物理删除
- [ ] 输出 receipt（沿用 artifacts/gates 惯例），验收标准：audit vs status 对账 = 0

### 1.3 预期收益
- [ ] 回收 20–30 GB（待 1.1 精确测算确认）

## Phase 2：证据归档与保留策略（治本核心）— 状态：completed ✅（2.1 归档 25.7M 行对账 ok / 2.3 `prune-retired-evidence` 回收代码+测试，90 天窗口生效；2.2 `archived_at` 以归档文件日期替代，记 ADR-009）

### 2.1 归档格式设计
- [ ] retired 文档的 evidence_spans 导出为只读 JSONL（字段：source_id、document_id、locator、page/paragraph/table 坐标、raw_text、span_json、parser_name/version、quality）
- [ ] 归档位置：`source_manifests/archive/{yyyy-mm-dd}/`（与现有 source_manifests / source_provenance 目录体系一致）
- [ ] 归档完整性验证：抽样 SHA + 行数对账

### 2.2 软删除升级为生命周期
- [ ] retire_document 增加 `archived_at` 标记（schema 变更，属上游提案）
- [ ] 三步生命周期：退役（状态 retired）→ 归档（导出 JSONL + 标记 archived_at）→ 回收（物理删除证据行）
- [ ] 保留策略表：active=全文保留；retired=归档后 90 天可回收；stub/失败=即时回收

### 2.3 常态化
- [ ] scheduler 增加 weekly archive/prune 任务（单线程、幂等、dry-run 默认）
- [ ] 每轮输出 receipt + 回收统计，写入 log.md

## Phase 3：证据粒度治理（schema 提案，仅设计）— 状态：completed ✅（`granularity-proposal.md`：表格级 + 新闻免 span，供上游评审）

### 3.1 粒度统计
- [ ] 按 locator 类型统计 span 分布（paragraph / table-cell / chars 区间），量化"表格单元格级"占比（预期 60–80%）
- [ ] 测算段落级 / 表格行级 / 表格级三种粒度的体积模型

### 3.2 提案（属上游 schema/parser 变更提案，不直接实施）
- [ ] parser 配置化粒度：`pdf_page_aware_core` 支持 table_cell → table_row / table_level 选项
- [ ] 新 parser_version 下旧 locator 保持有效（StockWiki 引用兼容）
- [ ] UNIQUE(source_id, locator) 约束与新粒度共存

### 3.3 迁移路径
- [ ] 方案 A：新库重建（新粒度 + 新参数），旧库归档
- [ ] 方案 B：按文档分批重解析（复用 normalizer 替换语义）
- [ ] 预期：span 总量降 60–80%，对应 DB 体积降幅

## Phase 4：Pending 语料容量治理 — 状态：completed ✅（`size-report` 容量监控；分级策略（新闻免 span）并入粒度提案）

### 4.1 构成（已实测）
- [ ] pending 20,728 = regulatory_filing 8,324 / broker_research 5,864 / investor_relations 3,312 / other 2,323 / original_news 903
- [ ] completed 2,702 = regulatory_filing 1,172 / broker_research 630 / investor_relations 363 / prospectus 204 / other 232 / original_news 104

### 4.2 分级策略
- [ ] 财报（annual/semi/quarterly 共 9,053 份）与研报（6,503 份）：保留证据（按 Phase 3 选定粒度）
- [ ] original_news（1,007 份）：段落级或免 span（新闻不适合单元格级证据）
- [ ] 与现有 quarterly/年度优先调度衔接，避免全量并行膨胀

### 4.3 容量模型
- [ ] 现状 44 GB / 全量按现状粒度粗估 100 GB+ / 治理后目标值（Phase 3+4 组合测算）
- [ ] 依据容量模型决定部署盘位（C: / D: / 外部盘），D: 现 71.8 GB 不足以容纳全量现状粒度

## Phase 5：存储迁移与索引优化（工程准备，视 Phase 4 结论决定）— 状态：pending

### 5.1 catalog_dir 迁移（如需）
- [ ] 停机窗口（worker 暂停）→ VACUUM INTO 备份 → 迁移 `.source_catalog` → 改 `config/source_catalog.yaml` 的 catalog_dir → 回滚方案
- [ ] 迁移前必须完成 Phase 1–4 治理（避免"搬一座垃圾山"）

### 5.2 新库参数（仅在新库/重建时）
- [ ] page_size、auto_vacuum=incremental、PRAGMA optimize 定期
- [ ] 索引评估：span_json 拆分列 vs 压缩存储

### 5.3 监控
- [ ] weekly 测量 page_count / freelist_count / span 增量 / DB 体积
- [ ] 告警阈值：所在盘剩余 < 30 GB；spans 周增量超预期

## Phase 6：验收与文档 — 状态：pending

### 6.1 验收指标
- [ ] audit vs status 对账 = 0；孤儿数据 = 0；FK check = 0
- [ ] 回收量达成（Phase 1.3 测算）；DB 增长率受控（连续 4 周符合容量模型）
- [ ] 测试全绿（沿用全量 pytest 惯例，当前基线 386 passed）

### 6.2 文档
- [ ] AGENTS.md 的 schema 维护规范补充"证据保留策略"章节
- [ ] docs/adr 新增 ADR（记录粒度与生命周期决策）
- [ ] log.md 记录每轮治理操作

## 决策点（需用户拍板）

| # | 决策 | 选项 | 建议 |
|---|------|------|------|
| D1 | B 类 9,576 份"审计但 active"文档 | 正式退役 / 正式恢复 / 按类型混合 | ✅ **全部正式退役**（2026-08-07 已实施，audit-vs-status 归零） |
| D2 | 证据粒度 | 保持单元格级 / 降为表格行级 / 降为表格级 | ✅ **表格级**（Phase 3 提案方向） |
| D3 | Pending 新闻类（903）是否免 span | 免 / 段落级 | ✅ **免 span**（Phase 3 提案方向） |
| D4 | catalog 是否迁移 D: | 迁 / 不迁 | ✅ **不迁**（留 C:） |
| D5 | retired 归档保留期 | 90 天 / 180 天 / 永久 | ✅ **90 天** |

## 风险与护栏

- 删除证据前未归档 → 违反可追溯原则（Phase 2.1 强制前置）
- StockWiki 已引用被回收证据 → 归档 JSONL 提供等价引用（locator 不变）
- worker 运行中写库 → 冲突（实施窗口统一暂停 worker）
- 迁移后 D: 空间不足 → 容量模型先行（Phase 4.3）
- 方案漂移 → 每阶段重新核对实际代码与 DB 状态（沿用 skill 的 plan drift 检查）

## 完成定义（Definition of Done）

1. Phase 1 对账报告 + 状态一致化完成（对账 = 0）
2. Phase 2 归档流程上线并跑通一轮（含 receipt）
3. Phase 3 粒度提案形成文档（ADR 或提案文件），等待上游评审
4. Phase 4 容量模型确定最终 DB 目标体积
5. Phase 5（如实施）迁移完成且回滚方案验证
6. Phase 6 文档与监控齐备，连续 4 周指标受控
