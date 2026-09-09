# company-wiki 根 planning 文档独立全文审计

日期：2026-09-04。Reviewer：`/root/v4_test_dag_review`（首轮独立审查）、`/root/cw_root_full_read`（独立全文补读与覆盖封板）。

## 授权与状态

- 使用并完整读取 `planning-with-files` 技能。本轮仅允许新增/更新本审计文件；原根文档、历史副本、代码、配置、数据库、worker 与启动项不得修改。
- 不运行生产命令，不访问网络。仅以只读文件、Git 与 CodeGraph 对照资料。
- 审计 HEAD：`a0c7629be6608fb668bbaf8856950df1b265d61b`。
- **当前状态：ROOT_FULL_TEXT_AUDIT_COMPLETE；这只表示根 planning 正文已完整读取与分类，不是生产/worker/计划 Gate PASS。**
- 下方报告已补齐全部正文；历史文件保持原字节，纠偏应写入外部统一状态入口，不回写或“修正”旧 receipt/历史叙述。
- 原始文件位置均相对于 `C:/Users/郑曾波/Projects/company-wiki/`。

## 精确读取覆盖

行号使用 `Get-Content` 的实际行数组（包含空行），不是 `Measure-Object` 默认非空行计数。首次读取因工具输出截断的部分已重新补读；不会把搜索或机械校验视为正文读取。

| 文件 | 字节数 | 实际行数 | 已逐行读取 | 未读 |
|---|---:|---:|---|---|
| task_plan.md | 370251 | 4417 | 1–4417（全文） | 无 |
| findings.md | 173223 | 892 | 1–892（全文） | 无 |
| progress.md | 170324 | 1348 | 1–1348（全文） | 无 |
| task_plan_v2.md | 15856 | 313 | 1–313（全文） | 无 |
| task_plan_cw_recovery_20260725.md | 89721 | 1166 | 1–1166（全文） | 无 |
| review_plan.md | 1461 | 42 | 1–42（全文） | 无 |
| verification_CW-2.24_plan.md | 5763 | 56 | 1–56（全文） | 无 |
| .recover-task_plan-before-cw-merge-20260725-115819.md | 13240 | 183 | 1–183（全文；截断块已补读） | 无 |
| .recover-task_plan-current-20260725-114504.md | 13240 | 183 | 1–183（全文） | 无 |

最终实际覆盖 **8600/8600 行**，另完整读取 `TERMINAL_NOTICE.json` 13/13 行；所有分块均有明确行界，截断块已整段重读。审计结束时再次核对十个文件的行数与 SHA-256，全部与本文件的基线一致，读取期间未发生内容漂移。

## 首轮发现与处置建议

### ROOT-P1-01：历史入口与当前状态必须在外部统一纠偏

证据：

- `TERMINAL_NOTICE.json` 明确覆盖根 `task_plan.md/progress.md/findings.md`，状态 `closed_superseded_incomplete`，指定 `revenue-forecast/assurance/unified_completion/state.json`。
- `task_plan.md:3` 仍把旧 FCAP r2 指为唯一活动入口。
- `task_plan.md:9–16` 的 `Current Phase` 展示 8 月 2 日 worker、旧 PID、代码指纹及登录自启动验收。
- `findings.md:12,21,29,37,892`、`progress.md:3,30–38,1348` 仍含历史健康/自启动表述。

结论：这些是历史记录，不能证明当前 worker 正在运行，不能作为恢复启动授权。终端声明让根三件套退役；直接改正文或继续记进度会制造活动入口歧义。

建议新增 `PLANNING_STATUS.md` 外部入口，分开三条状态线：历史统一账本（117 accepted 非本次重验）、当前 GP 补缺（2026-09-02 remaining-gap-closure）、worker v5（baseline ready 非正式技术验收或恢复授权）。当前暂停/自启关闭/旧目录回收状态由主代理近期证据支撑；本子任务未重新读取生产运行态。

### ROOT-P2-02：历史 runbook 中有被后续决策取代的步骤

- `task_plan.md:55,100` 已记载轻量快照替代 24.3GB 整库备份；`:135,149,156,158` 仍保留整库备份/副本要求。
- `progress.md:61–68` 记录删除 `database_backup_path` 门槛并引入受影响行恢复。
- 当前 CodeGraph：`src/company_wiki/source_catalog/focus_cleanup.py:489` 的 `apply()` 无 `database_backup_path`；同文件 `:687` 存在 `restore_database(snapshot_path, database_path)`。

影响：直接执行历史“下一实施者逐步 runbook”可能使用过时 CLI/备份流程。外部入口应明确不可直接执行；将来迁入活动计划必须重验 CLI、权限、测试、回滚和独立审查，不改写历史决策。

### ROOT-P2-03：CW-2.24 记录不能证明 618 项测试实际通过

- `verification_CW-2.24_plan.md:25` 勾选“618 contract tests 是否真绿（实际跑一次）”。
- `:40` 实际只记录相关 52 项与 source_catalog 160 项通过；`:3` 限定当时 R1/R2 窄范围。

结论：该文件自身不足以支撑 618 项实跑通过，不等于证明当时失败。外部历史说明记录证据差异；找到原始日志前不补写 PASS，不继承为当前测试 Gate。

### ROOT-P2-04：恢复副本的旧活动标记不能重新成为 backlog

- 两个 `.recover-task_plan*.md` raw bytes 完全相同，均无历史 banner；`:7–9` 写 Phase 9 正在运行，`:131–176` 写 worker 修复 in_progress/待执行。
- `task_plan_cw_recovery_20260725.md:3` 已为 `archived_reference`，但 `:13` 保留旧“唯一活动计划为根 task_plan.md”；`:1093–1153` 保留生产 canary/reindex/冷启动施工指引。

建议外部库存将两个副本标为 `HISTORICAL_RECOVERY_COPY / NOT_ACTIVE`；草稿保持 `archived_reference`。不勾选旧待办，不删除重复副本，不执行旧操作。

### ROOT-P3-05：历史行号和完成标题不能当成当前证据

- `verification_CW-2.24_plan.md:15` 引用根计划 4836–5166 行；现根计划总共 4417 行。
- 根计划 `:4413–4417` 与恢复草稿 `:1162–1166` 以 CW-2.17 标题和目标结束，没有随后的实施正文。
- `task_plan_v2.md:3` 已取消旧研究型路线；后续事件总线、研究 Wiki、投资评估等设计不得复活。

建议以文件身份、历史章节、冻结版本定位；行号失效不等于当前实现缺失，`completed` 标题不构成未展示的证据。

## 外部入口建议字段

1. 生效日期、审查 HEAD、读写范围、全文覆盖状态。
2. `TERMINAL_NOTICE.json` 优先级、根三件套不可续写。
3. 当前活动计划、历史账本、worker v5 三条独立路由。
4. 每份根文档的历史角色、写入规则、替代入口。
5. 历史 PID/测试数/receipt 不证明当前状态。
6. GP-008、GP-010、legacy periods 引用主代理实证，不从统一 117 accepted 推导完成。
7. 迁入活动计划必须重新核对命令、前置条件、证据和独立 reviewer。

## Raw SHA-256 基线

| 文件 | SHA-256 |
|---|---|
| task_plan.md | 69d941cd174589563b567d48343a76a10e4d5a691d66466504a167a0cda1809a |
| findings.md | a45b89d5e801a5c7584e93e77453ba743b9280ce09fa4bb50bf98429273d9f5f |
| progress.md | 80ca072916744c19be4ddd8d6dbabf422674054872b36d83a8801d7bc47d721f |
| task_plan_v2.md | acf03f6ed32804021235c60754d5e572e59e9390e1a5c28629bd305c9b37fc42 |
| task_plan_cw_recovery_20260725.md | 962a8d0a78b1fafdb2b6a529a21a03da5daf49c7725433bf8cb8126adafe168d |
| review_plan.md | 767218b2668ceea722f0deafac39cd0f4170cb17eca198393cb54152072e6fb9 |
| verification_CW-2.24_plan.md | 083a7c8a19050e7a22a017fd8ca013079630c159e6d0305c58ab155fca128b12 |
| .recover-task_plan-before-cw-merge-20260725-115819.md | bc73a980ac565a603bd7d2d8f95aafd54e4db5c34c9551b0c7219bafee9bbf76 |
| .recover-task_plan-current-20260725-114504.md | bc73a980ac565a603bd7d2d8f95aafd54e4db5c34c9551b0c7219bafee9bbf76 |
| TERMINAL_NOTICE.json | b3f3ceb22f17e8a174bf5bd535bddef619132c9e6d72277eae3eea1e4eac9103 |

所审原文件 scoped Git status 未显示变更；Git 同时报全局 ignore 文件权限警告，因此不扩张为整个仓库干净。只读尝试 `git -C .../dayu-agent rev-parse --is-inside-work-tree` 返回非 Git 仓，与 CW-2.24 历史该项一致；本审计不进一步扩展 Dayu 范围。

## 续读工作日志

- 首轮有界审计已持久化；现在补读 recovery 101–1066，随后 root task_plan 181–4367、findings 101–842、progress 101–1298。全文完成后再给最终覆盖结论。
- recovery 补读完成：101–220、221–380、381–560、561–780、781–960、961–1066；每块工具输出完整。该文件现全文 1166/1166 行已读，总覆盖增至 2473/8600。
- recovery 全文新增解释：CW-2.26 `completed`（193、244、274）与当时 CN 失败/待调查（254–256）并存，6.11E/F（125–183）已经纠正“仅 DNS”以及错误 official E2E 归属；不可把 recovered original 的 completed 抬升为三市场全绿。CW-2.27 保留原 pending 计划与后插入 offline completed（279、822–828），只完成当时 A/B，不是整项恢复完成。CW-2.24 Phase 5（1038、1044）标题 completed 但可追踪交付仍待 gate，也属于原始历史不一致。统一外部 archival 分类比修改这些证据正文更安全。
- task_plan 补读 181–330、331–490、491–680、681–880、881–1080，均无输出截断；当前总覆盖 3373/8600。
- task_plan 新增历史注意：181–202 自称“最高优先级”的角色/实施授权仍是 8/1 局部历史，必须服从 8/31 terminal notice；不能当当前授权。BG-4（526）和 FR-7（819）明确 deferred，但总览/复选框完成，不可用全部已勾推导这些优化已实施。BG-5（540）标题已 apply，而542仍写等用户授权；应保留时序差异。WR-3/WR-4（1048、1078）实施记录/文件名为空白；未来证据迁移必须找到实际receipt，不能仅因历史 completed 就填造路径。
- task_plan 补读 1081–1260、1261–1430、1431–1600、1601–1760、1761–1940；1431–1600 输出仅1519行发生10token截断，已单行完整回读1519补齐。当前总覆盖 4233/8600。
- task_plan 该段归档解释：WR-9/WR-10 明确保留生产观测 FAIL receipts（1316、1403、1426），后续PASS不追改旧失败；此原则也适用于v4冻结事故。WR-4旧3PASS/3skip与1097–1098的100%目标后来由1212最终0skip记录取代，不应把早期局部结果独立认作最终验收。1601后是合并恢复文本，但CW-1~4已回填、CW-2.25于1695转covered，与独立recovery草稿有真实差异，因此不能只凭看过副本就跳过主文件。
- task_plan 补读 1941–2140、2141–2340、2341–2540、2541–2740；各块输出完整。当前总覆盖 5033/8600。
- task_plan 该段进一步证明正文是多轮计划与事后回填的历史拼接：CW-2.27 的 Phase 0–9 runbook（1990–2418）包含 live network、真实下载、生产 catalog/raw 与跨仓写入步骤，2424 又以 2026-07-25 事后状态覆盖，并保留当时 pre-existing failure/遗留项（2428–2455）；其后 2464 起再嵌入 CW-2.24。任何这些命令都不能因旧 `completed` 标题而获得当前执行授权。
- 2342 的“先备份 catalog DB”与后续根计划已记录的轻量快照/受影响行恢复路线不一致；2574–2605、2707–2739 还保留当时 worker enabled/stopped、生产 reindex/canary 和可恢复备份路径。外部入口应明确：这些是时间点证据/旧 runbook，不是当前 worker 恢复、DB 写入或跨仓变更的操作说明。
- task_plan 补读 2741–2940、2941–3140、3141–3340、3341–3540；各块输出完整。当前总覆盖 5833/8600。
- CW-2.28 段存在正文内已明确纠正的证据冲突：2796 总标题声称 0R–10R 最终全部 PASS，但 3020/3046 标记旧 attempt invalidated，3097/3124/3156/3210/3281/3334/3380 又保留 not accepted/review failed/reviewer FAIL；3419–3441 的 implementer `Actual` 把含 1 xfail、1 failure、缺 independent reviewer 的项目仍写 PASS/PENDING，3443–3471 才由独立 reviewer 推翻。外部索引应把该段归类为“多轮历史修订；以最终 receipt/terminal notice 路由，不以较早表格或标题判定”。
- 2861、2886、3127–3144、3132–3135、3271–3277、3342–3378 均包含生产 DB backup/backfill、worker pause/恢复、跨仓测试和 Git 命令；这些在旧 WU 中有严格授权门槛。当前 terminal notice 之后不得复用为常规施工手册，尤其不能据 3144“恢复原 desired 状态”改变目前明确暂停及关闭自启的安全状态。
- task_plan 补读 3541–3740、3741–3940、3941–4140、4141–4367；与既读 4368–4417 合并后，`task_plan.md` 已全文 4417/4417 行逐行读取。当前九份根文档总覆盖 6660/8600。
- 3506–4138 的“审查后返工唯一执行手册”在当时已明确覆盖较早 implementer 记录，且 4132–4138 只证明“计划设计足够详细”，不证明产品 Gate；但 3768–3821 又要求恢复 worker、保留开机启动并跑后台 backfill，与当前用户后来明确要求暂停/禁自启相冲突。外部状态入口必须显式声明：`TERMINAL_NOTICE.json` 与当前 worker v5/暂停决定优先，旧 12.x 手册不再授权执行。
- 4140–4367 的 CW-2.29/2.30 在段首仍残留 `in_progress`（4144），随后所有 phase 与 WU 却标 completed（4180、4198、4211、4224、4238、4252、4263、4277、4309、4325 等）；这是典型内部状态滞留。它们又引用旧安装路径 `.agents/skills/...` 而本次用户审计对象是 `Projects/revenue-forecast` 仓，应由跨仓当前索引路由，不改写历史根正文。
- 错误记录：首次合并读取 `findings.md:101–500` 虽限定 400 行，但该段单行较长、原始输出 18,894 tokens，工具在约 184→415 之间截断；本次不计覆盖。改为每 100 行独立输出并全部重读，不把截断前后可见片段拼作全文证据。
- findings 重读 101–200、201–300、301–400、401–500，各块完整无截断；当前九份根文档总覆盖 7060/8600。
- findings 自身保存了关键的证据纠偏链，不能只提取最后一次乐观句：旧 PID/worker healthy、自启入口、生产吞吐只属于 2026-08-01 时间窗；192–200 又证明一次 44.1 分钟零吞吐由 stale operation-lock PID reuse 导致，206–208 另识别 900 秒 watchdog 杀合法慢 PDF 的独立瓶颈。当前外部入口应引用后续 v5 调查，不让这些旧运行快照覆盖“现已暂停/禁自启”。
- 365–418 的 CW-2.25~2.27 证据链明确推翻根 task_plan 的整体 completed：CW-2.25 不可证明，CW-2.26 历史 WU 未完成而能力后来补齐，CW-2.27 无独立 reviewer、三公司 8C 与静态/交付门禁不完整；418 给出最终裁决。外部索引应把这一 findings 裁决作为历史根文件内部的纠偏证据，而非采用 task_plan 较早 completed 标题。
- 453–500 的 CW-2.29 “进行中”记录随后已经包含实现、全量回归和 3.10.0 验证事实，和 task_plan 段首 `in_progress`/后续 completed 的时序差异一致；当前真值必须转由 `Projects/revenue-forecast` 自己的现行 planning/receipt，不再由 company-wiki 根文档裁决。
- findings 补读 501–600、601–700、701–842；与既读 1–500、843–892 合并后，`findings.md` 已全文 892/892 行逐行读取。当前九份根文档总覆盖 7402/8600。
- 560–633 的独立 reviewer 最终把 CW-2.28 判为 FAIL，并给出当前稳定门禁仍有 fail/xfail/Ruff/diff、fingerprint backfill 未接 worker、resolver KeyError、严格五公司仅 2/5、receipt 缺失与交付不可复现等证据；692–706 较早 `CANDIDATE/10 phases completed` 摘要已被 713–724 的最终 FAIL 明确取代。外部索引应列出这条“较早摘要 → 独立复核推翻”的优先级。
- 761–842 又展示 worker 状态在同一天和后续数日多次变化：旧进程可工作但新代码不可启动、随后 stopped/paused，再修复并在 7/29 短窗 healthy，7/30 又出现 overnight stopped。任何单个“healthy/running/stopped”行都是时点证据，不能替代 2026-09 当前暂停状态或 v5 的根因/性能计划。
- 813、820–832 给出旧性能根因：semantic duplicate 的 per-document 相关子查询曾导致分钟级 export，窗口查询降到亚秒级；完整导出仍约 38–49 秒；单线程 batch=3 且 PDF 1–2 分钟使 backlog 清空慢。这些可作为 v5 历史证据来源，但不能据旧优化就断言当前瓶颈已消失。
- progress 补读 101–200、201–300，均完整无截断；当前九份根文档总覆盖 7602/8600。
- progress 不是按时间严格排序：101 起为 8/1 WR-10.15，128 又是暂停检查点，149 回到 WR-10.12/13，160 回到 WR-10.9，268 是实施冻结，277 又回到 7/28 FINAL。外部入口不能用“文件尾部/靠后段落=最新”推断当前状态，必须按时间、receipt 与 terminal notice 路由。
- 同一 8/1 历史中存在明确角色切换与状态漂移：107–115/268–275 说 Codex 只审查，119/160–193 又记录用户后来授权实施；137 写 worker 仍运行，167 写 pilot FAIL，189 又写 post-fix pilot PASS。它们是可保留的审计时间线，不是当前 worker 启动授权或最新健康证明。
- progress 补读 301–400、401–500，完整无截断；当前九份根文档总覆盖 7802/8600。
- 301–350/464–500 大量使用 `FINAL`、`ALL DONE`、`HARDPASS`、`COMPLETED`，但同一根 findings 后来的独立审计已明确推翻 CW-2.27/2.28 的部分完成结论。外部入口必须声明：progress 是事件日志/实施者记录，不是脱离 receipt 与独立审查即可采用的权威状态表。
- 332 记录 10GB 全库 backup、342/350 记录 worker desired=enabled/running；这些只是 7/27–28 生产历史，且与后续轻量快照决策、当前暂停/禁自启均不一致，不能作为当前操作建议。
- progress 补读 501–600、601–700，完整无截断；当前九份根文档总覆盖 8002/8600。
- 501–700 是 2026-04 legacy Wiki/研究助理路线：包括批量修 wiki、矛盾检测、综合评估和“自维持研究助理”目标。它已被 2026-07-16 AGENTS 职责边界和 `task_plan_v2.md` 取代；只能保留为历史实施日志，绝不能从这些 completed 状态恢复投资研究 writer 或对现有 wiki 做批量清理。
- 511–564 还记录删除新闻/模块等历史破坏性动作，688–697 记录清理 wiki 条目。外部索引应把这些标为 `LEGACY_EXECUTION_HISTORY / NOT_A_RUNBOOK`，避免弱模型把旧 Actions taken 当当前可重复步骤。
- progress 补读 701–800、801–900，完整无截断；当前九份根文档总覆盖 8202/8600。
- 701–747 的 legacy “自维持研究助理/评估”仍属被职责边界废止的旧目标；749–759 又记录根 task_plan 曾被旧 Git HEAD 意外覆盖后从会话日志恢复，因此根大文档本质上是恢复/拼接档案，不能成为无外部索引的唯一活动入口。
- 760–791 的严格审计已经明确纠正 CW-2.25/2.26/2.27：整体不得 100% complete。805–890 的 CW-2.29–2.31 则记录 revenue-forecast 后续迁移、同步和推送，但这些 commit/版本是当时状态；本次三仓同步应以 `Projects/revenue-forecast` 当前 HEAD/receipts 为准。
- progress 补读 901–1000、1001–1100，完整无截断；当前九份根文档总覆盖 8402/8600。
- 1015–1045 的实施者 `CANDIDATE` 声称 all phases/receipts、Phase 9 PASS，尽管同段承认 62/11,706、1 xfail、StockInfo 2 failed、5-company 4/5、无 reviewer；1052–1060 随后由 independent reviewer 正式 FAIL 并退回 Phase 2。外部索引必须明确后者覆盖前者。
- 1083–1100 开始的新一轮 Phase 2R 属 7/26 当时 implementation authorization；即使后续 receipt 链存在，也已被 8/31 terminal notice 封存。当前不得据这些步骤继续写生产 DB、恢复 worker 或重启旧 WU。
- progress 补读 1101–1200、1201–1298；与既读 1–1100、1299–1348 合并后，`progress.md` 已全文 1348/1348 行逐行读取。九份根 Markdown 最终覆盖 8600/8600。
- 1103–1148 显示 Phase 2R/3R 后续曾通过、Phase 4R–8R blocked、Phase 9R FAIL、Phase 10R NOT_RUN；1150–1161 又是 worker repair FAIL，1170–1210 再修复至 7/29 `healthy`，1232–1245 次日却再次 stopped 并定位 PowerShell native stderr/launcher 问题。该时序证明任何孤立 `PASS/healthy` 都不能当永久现状。
- 1272–1298 保留 watchdog clean-pilot 多次 FAIL/fixture 修订，最终停点明确为生产 worker 当时仍运行、第三次 clean pilot 未开始。它与文件更靠前的 8/1/8/2 后续记录、8/31 terminal notice、当前 v5 安全状态有先后关系；外部入口必须按日期与 supersession 显式排序。

## 全文审计后的外部索引建议

建议由主代理在统一 `PLANNING_STATUS.md`（或本次三仓同步目录的等价入口）至少写入以下不可歧义路由；不修改这些历史原件：

| 根文件/组 | 建议分类 | 外部索引必须说明 |
|---|---|---|
| `TERMINAL_NOTICE.json` | `TERMINAL_AUTHORITY` | 覆盖根 `task_plan.md/findings.md/progress.md`；三件套 closed/superseded，不再续写或执行。 |
| `task_plan.md` | `HISTORICAL_COMPOSITE_PLAN / NOT_ACTIVE` | 4417 行由多轮恢复、实施、事后覆盖组成；内部 `Current Phase`、`completed`、旧授权及命令均不代表当前状态。 |
| `findings.md` | `HISTORICAL_EVIDENCE_LOG / NOT_CURRENT_RUNTIME` | 保存重要根因与独立复核纠偏；PID、队列、性能和健康结论全是时间点证据。 |
| `progress.md` | `HISTORICAL_EVENT_LOG / NOT_STATUS_INDEX` | 非严格时间排序；较早 implementer PASS 多次被后续 reviewer/现场证据推翻。 |
| `task_plan_v2.md` | `SCOPE_SUPERSESSION_RECORD` | 以 source-only 上游边界取代 legacy 投资研究路线；不得复活旧 writer。 |
| `task_plan_cw_recovery_20260725.md` | `ARCHIVED_RECOVERY_REFERENCE` | 保留恢复文本和旧 runbook；不得以其“根 task_plan 为活动入口”的旧句路由。 |
| 两个 `.recover-task_plan*.md` | `HISTORICAL_RECOVERY_COPY / NOT_ACTIVE` | 两份 raw SHA 相同，内部 Phase 9/worker in_progress 仅是覆盖事故时快照。 |
| `review_plan.md` | `HISTORICAL_REVIEW_PLAN` | 仅按其日期/范围解释，不提升为当前 gate。 |
| `verification_CW-2.24_plan.md` | `HISTORICAL_NARROW_VERIFICATION` | 52+160 实跑记录不能支持文件中“618 项实际跑一次”的勾选；不继承为当前测试 PASS。 |

统一入口还应分开三条当前路线：

1. 三仓统一/剩余缺口的现行权威入口（由 revenue-forecast 当前 planning/assurance 决定，不从根历史三件套推导）。
2. company-wiki worker recovery v5：当前仅 baseline/import ready、版本合同/正式 freeze/独立审查待完成；不是恢复运行授权。
3. 当前安全运行态：worker paused、开机自启关闭；任何旧计划中的 `restore desired enabled`、保留登录启动、生产 backfill、真实下载、DB restore/backup 或跨仓 Git 操作均需重新授权与新鲜证据。

外部索引应明确：历史原件中的测试数字、PID、DB 大小、Git HEAD、文件路径、网络/下载授权、receipt 状态和性能结论均不得自动外推到 2026-09-04；迁入新计划时必须重新验证，并在每个关键 gate 安排独立 agent 审查。
