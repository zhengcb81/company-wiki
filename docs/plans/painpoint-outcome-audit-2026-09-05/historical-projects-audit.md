# 旧独立项目的原痛点审计

2026-09-06。只读代码、计划、历史receipt说明与文件stat；没有打开生产SQLite、执行归档/回收/VACUUM或改worker。旧71 FC/10waves/5closure通过继承表映射到本次CA/ZR审计，不再次把旧空框当实施队列。

## H01 空间治理：工具交付部分成功，不等于生命周期安全闭环

原目标（`docs/plans/catalog-space-remediation/task_plan.md`）：纠正9578状态不一致、证据退役→归档→回收、控制pending增长与避免磁盘填满。

可保留成果：历史progress记录8/7退役9499、删除77stub、mismatch归零；归档25,708,956行与当时count相等；prune默认dry-run、90天未到时拒绝；D4“不迁D盘”是有效取消，不是遗留失败；粒度提案按“只交设计”完成也不应冒充实现。

当前文件stat：catalog.sqlite3=49,677,086,720 bytes；旧pre-remediation备份=49,314,422,784 bytes。这里仅是文件逻辑长度，不是当前SQLite活跃页/实际占盘/可回收量，不重复读取大表统计。

### 高风险反证

`src/company_wiki/source_catalog/prune_retired_evidence.py::prune_retired_evidence`只检查archive目录下最早YYYY-MM-DD子目录与今天差≥retention_days，连目录内归档是否存在/可读/完整都不验证。随后`_DELETE_BATCH`对所有当前source_status=retired文档删span，不绑定哪个文档已归档、何时退役、归档source/parser/hash或下游引用。

因此“空旧目录 + 新近retired且未归档文档”就能满足due逻辑，apply会把新文档纳入删除范围。此为静态可达风险，不是声明生产已经误删；本轮绝不运行apply。每批独立commit、receipt只在全部删除后写，若中断也缺逐批恢复账本。

生产接线已确认：`worker.py:795`周期内直接调用prune_retired_evidence(...,apply=True,retention_days=config.prune_retention_days)，不是仅提供手动危险命令。当前已知archive日期目录为2026-08-07；worker持续暂停使风险暂未因本审计触发。不能自动恢复worker并等90天后再处理此门。修复/审批前应把自动prune纳入恢复阻断条件（本轮仅记录，不改开关）。

测试也锁定了错误验收：`tests/contract/test_source_catalog_prune_retired.py::test_prune_apply_deletes_spans_when_due`仅建空日期目录、retention_days=0，便要求所有span删除。没有验证归档存在。`test_prune_apply_within_retention_does_nothing`用硬编码2026-08-07作today，日历推进后断言会失效；时间应注入而非硬编码。归档测试仅行数及首行字段，不覆盖同日覆盖/中断/逐项恢复。以上为读测试发现，未执行测试中的删除。

`archive_retired_evidence.py`每天输出固定`retired-evidence.jsonl.gz`并gzip.open(...,'wt')：同日再运行会覆盖既有归档，失败可留下不完整文件；ok只比较总行数，非逐文档/逐span内容hash；无原子publish、没有稳定读事务或归档manifest供prune逐项核验。仅“旧目录日期”替代archived_at的ADR等价方案不足以保证原始安全不变量。

结论：状态对账/工具交付属于HISTORICAL_ONLY/PARTIAL；“证据生命周期已安全治本”被当前删除门反证（CONTRADICTED）。不能因为90天还没到就忽略此风险，也不能通过缩短保留期快速验证。

### 后续必须补的验收

逐文档归档coverage/hash/parser/locator与retired_at绑定；归档不可覆盖且原子发布；恢复抽样必须能重建原定位；回收只接受已验证manifest列出的精确span集合且保留期逐文档满足；所有引用策略/owner授权独立审核。空旧目录、gzip截断、同count换内容、新retired、重激活、归档后新span、并发中断均需红例。生产回收另有显式授权，不从本报告自动执行。

## H02 核心章节提取

旧年报/半年报/招股书章节实现、SectionQueryService与历史测试是有效局部资产；不能拿旧Phase1–5完成推断broker已完成。GP010由0到5/7是真进展，但两个列表式broker缺section、真实EvidenceSpan/归属与生产cohort安全仍需wiki-audit的结论。新section_extractor未提交改动属于其他任务，本轮不覆盖。判定PARTIAL，对旧限定三类文档的历史结论保留HISTORICAL_ONLY。

## H03 Portfolio reuse fix / automatic

旧Strategy A自动提升已取消/回滚、Strategy B配置驱动只读复用有历史2020.HK成功。这不是失败，也不应重新启用A。原“必须复制到companies才能复用”已有局部缓解，但当前请求级eligible、policy跨路径降级、第四root完整旅程仍存在F-F01/02及ZR409缺口。判定：旧A SUPERSEDED；B窄范围历史成果保留，多根完整用户目标PARTIAL。

## H04 Worker v5与8/12故障

v5是隔离修复规划，不是已实施产品。worker持久paused及已知HKCU入口停用不等于旧慢查询已修；8/12日志、相关EXISTS/整段fetchall、周期末checkpoint和supervisor失败清零问题详见wiki-audit。恢复必须先完成性能/取消/失败账本与安全cohort门，不能因任务已accepted恢复生产。

## H05 旧Wiki研究型计划

2026-07-16职责边界已明确投资研究状态归StockWiki。旧assess/synthesis/研究writer不再是company-wiki当前目标；按SUPERSEDED处理，不以恢复这些writer作为修复。来源解析、locator、只读export的实际缺口仍属于本次范围。

## 调查错误/限制

猜测tests/contract/test_prune_retired_evidence.py不存在；随后按文件清单定位测试，不重复猜路径。未核实时下全部磁盘/后台服务、不解压4.6GB归档；历史行数来自日志，未重测。后续容量模型必须测活跃页、freelist、WAL、归档、备份与增速，不能把文件逻辑长度直接当可删除空间。
