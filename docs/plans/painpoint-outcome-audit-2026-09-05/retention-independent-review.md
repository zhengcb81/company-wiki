# H01 证据归档/回收风险的独立静态复核

日期：2026-09-06。审查者：audit_filing（非historical-projects-audit.md作者）。范围：H01、prune_retired_evidence.py、archive_retired_evidence.py、source_catalog/worker.py相关入口与两份直接contract测试。仅静态读取，未执行任何测试、archive/prune函数、SQL、worker、进程控制或磁盘清理。

## 结论

H01核心安全风险成立，且不是只存在于手动工具：自动worker路径在检查周期到期时显式传apply=True。prune的保留期只依赖最早日期目录名，删除集合却是执行当时所有retired文档的EvidenceSpan，二者没有逐项归档绑定。存在潜在不可恢复的派生证据/locator丢失风险，应作为worker恢复前的P1阻断项。没有证据证明生产已经误删；本复核不检查现场事故记录或实际暂停状态。

## 1. 自动apply的可达证据

`src/company_wiki/source_catalog/worker.py::SourceCatalogWorker.run_cycle`：

- 行784–790：检查timestamp-last_prune_check_at是否达到prune_check_interval_seconds。
- 行791：在尝试前更新last_prune_check_at。
- 行795–800：调用prune_retired_evidence(self.catalog.config, self.project_root / source_manifests, apply=True, retention_days=self.config.prune_retention_days)。没有在此要求独立归档manifest或逐项批准。
- 行802–805：异常只记录last_prune_error，然后继续cycle收尾。这不是删除事务回滚机制；先前各批commit已发生时，异常记录不能恢复证据。
- WorkerConfig默认prune_retention_days=90、prune_check_interval_seconds=604800；当前配置文件同值。这两个参数必须为正整数，没有独立自动prune禁用布尔门。
- run_forever在persistent paused时退出，确实可阻止常规后台周期继续；但这是运行入口的暂停机制，不是prune自己的安全验证。未重查当前持久状态，也未把“暂停”表述为所有手动入口不可执行。

结论必须写成“worker进入该周期尾部、检查间隔到期且prune due=true时自动apply可达”，不能写成“每次启动必然删除”或“现在正在删除”。代码本身足以确认可达性，无需风险性实跑。

## 2. P1：目录年龄与删除集合脱钩

`prune_retired_evidence.py:59–78`只枚举archive_root/archive下名字长度10且可解析为ISO日期的目录，取最早日期并比较当前UTC日期。未检查gzip文件存在、内容可解压、已完成状态、行数、hash、逐文档coverage或归档创建时间。

`_DELETE_BATCH`实际谓词是：从evidence_spans选择document_id属于当前documents.source_status=retired的所有span，每批上限100000。没有archive manifest join，没有retired_at或archived_at比较，也没有source/parser/hash及下游引用约束。

因此以下反例在静态控制流上成立：一个足够老的空日期目录存在；某文档今天刚退役且未曾归档；apply=True时due可为true，而该文档span满足DELETE谓词。CatalogOperationLock只处理互斥，不能补上归档安全性。

影响对象是本catalog内的EvidenceSpan，不是本函数直接删除外部root原PDF/其他目录文件。原文档可能还存在且部分内容可重解析，但不能据此保证旧parser版本、locator、人工修订和下游hash引用可完全复原。应称“潜在证据丢失/不可精确恢复”，而非未经验证宣称所有原始资料被永久删除。

## 3. P1：同日归档覆盖与不完整产物风险

`archive_retired_evidence.py:47–54`每日固定目录和retired-evidence.jsonl.gz；`:69`用gzip.open(..., wt)直接写目标。第二次同日执行会替换旧文件内容，没有唯一runID、拒绝覆盖或临时文件完成后原子publish。

目录在数据库打开前已创建；写入失败、异常或中断时没有回收未完成目录/标记quarantine。故“不完整甚至仅目录存在”本身也能以后满足prune年龄门。即使不是人为建空目录，当前归档流程也可能留下这种状态。此为代码风险推理，不是现场已发生事实。

归档字段包括span_id/source_id/document_id/locator/parser字段，是有价值的恢复资产；但ok仅比较rows_written和开始时COUNT(*)，没有内容hash及逐项manifest；多次SELECT分页没有显式BEGIN稳定读快照。数据库只读不等于跨查询一致快照，不能以“retired一般不再处理”的注释取代对重激活、退役状态变化、恢复或并发维护的保护。

## 4. 测试是否支持H01

| 测试/入口 | 静态确认 | 审查解释 |
|---|---|---|
| test_prune_apply_deletes_spans_when_due | fixture生成span并刚退役；仅mkdir archive/2026-05-01；没有调用archive；apply=True, retention_days=0；断言deleted_rows==before、remaining==0 | 直接把“空日期目录可删未归档span”写成预期行为。没有运行测试也能核实其验收语义。 |
| test_prune_dry_run_reports_span_volume | 空旧目录即预期due=true | 可证明数量预览，不证明归档安全；日期硬编码，未来/历史clock环境会改变结果。 |
| test_prune_apply_within_retention_does_nothing | 固定2026-08-07目录注释today；没有注入clock，使用真实datetime.now | H01所说“用硬编码日期作today”应准确改为“把固定目录日期注释为today，实际now仍为运行日”。日期推进到保留期后其not-due断言会反转。不是本次日期下必失败。 |
| test_archive_exports_retired_evidence_with_row_reconciliation | 校验行数与首行document_id/字段存在 | 是基础序列化测试，未验证所有内容hash、每项恢复、同日覆盖/原子性/中断。不能推出完整归档安全。 |
| test_archive_empty_when_no_retired_documents | 无retired时生成0行归档仍ok | 合法空快照与“以后所有退役文档都已归档”必须分离；当前prune无法区分。 |

使用rg -g扫描test_source_catalog_worker*.py未见prune/last_prune/archive直接引用；仅说明本命名范围未找到相应自动入口测试，不能声称全仓绝无间接测试。

## 5. P2：每批commit、终局receipt以及异常状态

prune每个batch一个store.transaction；完整循环完成后才写receipt。中途失败可能已有删除但没有对应终局receipt；receipt本身只含oldest_archive/retired_documents/span_rows_before/deleted_rows，没有精确已删span列表或归档hash绑定。重跑可继续删，但“可继续执行”不等于“有独立可审计且可恢复的事务账本”。

worker在尝试前推进last_prune_check_at并捕获异常，可延后下一次检查；last_prune_error有记录是保留资产，但应增加独立告警/失败状态和恢复计划，不能把整个cycle completed理解成prune成功。

## 6. 供计划采用的最小验收节点

1. 独立agent先审安全合同：逐项retired_at、archive completion、hash/locator/parser一致、引用保护与恢复保障；区分合法空archive和可删除集合。
2. 只在隔离夹具建立红例：空旧目录、新retired、截断gzip、同count换内容、同日二次归档、写中断、重激活、归档后新增span、目录名伪旧。默认不运行生产apply，禁止缩短生产retention来验证。
3. 归档使用不可覆盖runID+临时文件+完整校验+原子publish+manifest；独立恢复agent从归档重建并对精确span/locator/hash验证，不让写归档者自证。
4. prune只删除已验证manifest精确列出的且逐项满足保留期/引用条件的集合；所有未覆盖、状态变动、缺文件、hash不符fail closed。按batch持久intent/result，异常后可重放且不丢事件。
5. worker恢复前必须独立审查自动调用合同和默认禁用策略；真实归档/删除/恢复演练分别取得明确授权。不能仅改手动CLI默认dry-run而漏掉worker apply=True。

## 7. 本复核的错误/边界

首次rg把Windows文件glob直接作路径参数导致os error123；改用rg -g限定文件名完成查询。未改系统/工具配置。

本次仅新增retention-independent-review.md，未改主报告/项目代码/计划、数据库、归档或配置；未解压旧4.6GB归档、未核验历史误删或备份可恢复性。H01风险结论获独立静态支持，不是事故确认书。
