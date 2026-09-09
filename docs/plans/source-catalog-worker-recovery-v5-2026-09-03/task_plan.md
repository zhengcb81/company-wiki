# Worker v5 独立基线与重新冻结 — 工作计划

> 2026-09-08衔接检查点：按[R4计划](../painpoint-outcome-audit-2026-09-05/simplified-execution-plan.md)C/D引用本目录worker合同，不另造冻结；旧WP06.G1编号不再是活动准入。本目录V5-1/2/3仍未完成。H01可信归档或经独立证明的危险入口硬禁用、持久任务、安全scope、取消/circuit、v5适用前置及明确恢复批准按实际运行能力保留，不能仅SQL变快或D.SAFE通过即启用。A/B只读不等待本目录。仅文档同步，不勾选实施、不运行旧checker。

用户授权：新开目录放 v5；最新要求删除原 v1–v4 独立目录。已导入的 v5 基线及原调查报告保留。
最终目标仍是完整、可审计、弱模型不会跑偏的改进计划；本阶段**不实施 worker 修复**。

## Phase V5-0（隔离与导入）— 状态：completed

- [x] 新目录原先不存在；不与旧计划或主线目录重叠。
- [x] 读取 planning-with-files 技能，先创建三份工作文件。
- [x] 从旧 manifest 的精确名单选择 48 份当前规范文件。
- [x] 另选原 v3/v4 manifest、旧 progress/revision、漂移报告、原调查报告，共 6 份历史/来源文件。
- [x] 对每个源/目标验证 resolved path、拒绝 reparse，复制前记录 raw SHA-256/size。
- [x] 只复制明确列出的普通文件，不递归搬运数据库、日志、配置、源码、秘密或其他任务文件。
- [x] 复制后核对目标字节以及源前后字节；有任何漂移则不批准该次导入。
- [x] 保存 import_manifest.v5.json；它只描述导入，不是正式计划冻结 manifest。
- [x] 检查本目录有效 Git text/eol/filter/working-tree-encoding 属性以及零 tracked 文件。
- [x] 一名独立 agent 只读审查导入完整性、原目录未写、历史与活动身份区分和 Git 边界。
- [x] 主 agent 保存真实审查结果；reviewer 回读后确认摘要忠实，不能代填 PASS。

结果：`IMPORT_REVIEW_PASS`；独立reviewer已确认保存记录`FAITHFUL`。见
`reviews/import-review-2026-09-03.md`。该结果不批准V5-1/V5-2、项目实现或worker恢复。

## Phase V5-R（用户授权退役旧 v1–v4 目录）— 状态：completed

- [x] 精确定位唯一旧目录，确认v5/原调查报告位于删除范围之外。
- [x] 核验53份文档精确副本；唯一生成pyc明确列为缓存例外，完整目录只送回收站。
- [x] 独立agent复核并返回SAFE_TO_RECYCLE，执行前再次核验54份库存与路径/无reparse。
- [x] Windows回收API成功、旧路径不存在，并在回收站确认同名/原位置匹配的目录。
- [x] 删除后v5导入检查54/54 PASS，原报告和import manifest hash未变。
- [x] 更新活动入口和退役记录；不修改baseline/历史manifest，不stage/commit，不恢复worker。

证据：`reviews/old-plan-retirement-inventory.json`、`reviews/old-plan-retirement-result.md`。

## Phase V5-1（版本合同）— 状态：completed（2026-09-09；rev4 获独立复审 `accepted`）

- [x] 独立设计审查选择一种一致方案：明确拆分协议 revision 与冻结 generation（rev1 rejected → rev2 accepted_with_findings → rev3/rev4 闭合 G1 → rev4 复审 `accepted`）。
- [x] 枚举全部 schema 常量、机器实例、活动文档、CLI、validator、路径和版本引用。
  → [v5-version-reference-inventory.json](v5-version-reference-inventory.json) / [.md](v5-version-reference-inventory.md)（V5-2 冻结时点 56 文件；范围与计数偏差见 [v5-freeze-record.md](v5-freeze-record.md) §4 D4）。
- [x] 将 10 份未证明与原 v4 等价的输入作为新基线，从零内容审查，不声称是 v4 字节恢复。
  → [v5-baseline-equivalence.json](v5-baseline-equivalence.json)：21 v4_exact / 17 crlf_only / **10 unproven_new_baseline**；逐件从零审查在 V5-2 三路审查中执行。
- [x] 新活动入口必须明确取代哪些旧入口；历史文件保留在 baseline，不能并列作为权威。
  → [版本合同 §6](v5-version-contract.md)；并记录旧目录复活事实（N9）。
- [x] 建立版本一致性负例：旧 manifest、新 manifest、错 schema、混合节点、错路径一律拒绝。
  → N1–N17（[版本合同 §7](v5-version-contract.md)），待 V5-2 以机器检查实现。

## Phase V5-2（冻结与独立审查）— 状态：completed（2026-09-09；三轴复审全部 `accepted`）

- [x] 明确稳定审查边界；不把仅有前后 hash 或 .gitattributes 当作不可变性证明。
  → [v5-freeze-boundary.md](v5-freeze-boundary.md) 协议 B1–B6 + 机器可读处置块（manifest `boundary_record` 绑定）+ 调用方式要求（`python -I`，三种调用形态守卫）；[v5-freeze-record.md](v5-freeze-record.md)。
- [x] 重跑计划一致性、schema/实例、DAG、测试 registry、vectors、prose 全套检查。
  → 预冻结 `PASS: 7720 checks`（fixed_nodes 115/schemas 29/tests 315/vectors 18）。
- [x] 冻结前保存精确输出，生成新的正式 plan_manifest.v5.json，再做冻结后逐字节核验。
  → [plan_manifest.v5.json](plan_manifest.v5.json)（51 项）+ [plan_freeze_check.v5.txt](plan_freeze_check.v5.txt)（172 字节、0 CR）；`--verify-manifest` 9188 checks 通过。
- [x] 以机器检查 + 测试 ID 实现 N1–N17，并证明每条负例都被拒。
  → `--self-test` **17 例 / 32 变异 + 4 项默认模式检查 + 3 项守卫检查**，全检查与隔离两种模式全拒。
- [x] 三路独立 agent 从零审查 + 四轮复审；每路绑定同一冻结输入、独立复算。
  → 审查与关闭记录共 13 份；SQL/性能 `accepted`、生命周期/安全 `accepted`、测试/DAG `accepted`，均无 P0/P1。
- [x] 关闭首轮 9 条 P1、二轮 2 条新 P1、三轮 3 条新 P1、四轮 3 条 P2。
  → 整改表见 [v5-freeze-record.md](v5-freeze-record.md) §7/§8；共 17 条（P1 14 + P2 3）逐条有复现与验证。
- [x] 结论：本计划可作为未来实施的**输入**（仍不授权启动 worker、不改协议语义、不实施任何修复）。

## Phase V5-3（交接）— 状态：pending

- [ ] 更新新目录的 findings/progress，给出清晰活动入口、历史索引、剩余风险与实施顺序。
- [ ] 只读复核 worker 暂停和已知自启动入口关闭。
- [ ] 保持与现有主线计划隔离，等待用户以后决定并入或实施。

## Errors Encountered

| 错误 | 处理 |
|---|---|
| 更新 README 时多余的末尾 patch 上下文不匹配，整包拒绝 | 只读确认没有部分写入，去掉无关上下文后精确重试成功 |
| 旧目录退役库存发现54文件而导入映射53份，预检拒绝继续 | 定位唯一生成pyc，记录缓存回收例外并取得独立复核SAFE_TO_RECYCLE后才执行 |

历史 v4 字节漂移和额度中断记录见 findings.md 与 baseline/history/。
