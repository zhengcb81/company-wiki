# SPACE-S5 独立任务：B2/DB/原件重复量的只读审计

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> 当前状态（2026-10-04）：已交付，只读报告与15项审计测试已绿。不要再启动本卡；生产迁移/清理归MAIN S5/S6。 下文启动基线为历史施工记录，以总计划当前状态为准。

## 现在可以启动；唯一写入目录

`C:\Users\郑曾波\Projects\company-wiki-storage-audit-20261003` 为独立审计工作目录；可以在里面放小型只读工具、测试、结果和局部 PWF。不是新增生产服务，不创建第二catalog/任务库。没有远端时报告本地交付，不为审计开新GitHub仓。

company-wiki、RF、FF、ET、StockWiki、IQS、dayu、Dropbox、全局技能目录均**只读**；不得在这些目录初始化索引、改ACL、生成扫描缓存、运行writer/Worker/VACUUM、删任何文件。root负责真正清理。本包不与任何生产实现线共用写目录，能与 FF-S3、ET-S3、MAIN同时做。

自己目录使用 `.planning/s5-storage-audit-20261003/` 的 task_plan/findings/progress，别写 CWP 共享计划。不存在则创建；已有非本线内容先确认用途，不清空。

## 目标与可信基线

把“约2.87GB还不能删”和“3.06GB库是否能缩”变成具体集合/调用者/数据库页实测。额外测 exact-SHA 原件重复候选，为可选第二轮提供依据；不把原件重复候选当删除授权。

读这些 CWP 文件即可恢复当前背景，不加载历史六十个Phase：

- `docs/plans/narrative-evidence-pilot-2026-09-26/task_plan.md`、`findings.md`。
- 同目录 `harness_lanes/results/gd_storage_final_cleanup_2026-10-03.{md,json}`。
- 同目录 `harness_lanes/results/gd_b1_retirement_2026-10-03.md`、`gd_b3_retirement_2026-10-03.md`。
- `config/source_catalog.yaml`：原件root映射，catalog `.source_catalog/catalog.sqlite3`；不写配置。

已测：合计32,821,613,206B/32.82GB；公司原件25,198,502,813B；库3,055,800,320B；旧derived/index约2.87GB。此前13.06GB已释放，不再次列可清理收益。三managed checkout约0.27GB由app管理，不手工删除。原件及source/location/version/撤回事实不能丢。

Git基线：开工记录 CWP 当前已发布HEAD、目标代码文件SHA、读取时dirty清单；分析代码可从该HEAD的git对象读取，避免main正在修改时混版本。报告不是永不失效的签收：root合入清理前只复核变化的调用者/集合，不再全量重审。

## 实施步骤

1. 有界只读盘点 B2：`.source_catalog` 内 normalized/derived/cache/index 等已存在集合。按业务集合而非几万个逐文件条目统计bytes/files、reparse/不可读项。raw/company/source事实目录排除清理候选；访问错误标unknown，不能算0。
2. 调用者映射：结构问题优先已有CodeGraph；未初始化的外仓不写索引，可读取已知入口/固定Git文件做AST/literal分析并说明覆盖范围。对每集合列实际生产caller及配置/CLI来源；区分仅测试/退休脚本/运行中功能。重点 normalized reader、legacy summarizer、RF兼容入口、全文检索依赖。
3. DB只读页/表/索引：SQLite URI `mode=ro` + `PRAGMA query_only=ON`，记录schema版本、page_size/page_count/freelist_count、WAL/SHM现状。只读同一snapshot处理当前WAL，**不要**用 immutable忽略有效WAL，也不要checkpoint。`dbstat`可用则按对象聚合页与payload；不可用则明确unknown，不复制/完整导出大库。
4. 查询有timeout/progress handler和行数/输出上限，避免扫全span再复制。表/索引占用的候选先定位，留source/document/location/version/retraction/消费者ID事实；垃圾派生与必要元数据分开。DDL/触发器/外键仅SELECT；可收缩收益是测量/估计，真实VACUUM由root以后量。
5. exact-SHA原件候选先使用已有source SHA+byte_size和物理location记录分组；同source多个数据库映射不能当多个实体文件。只对候选核实际物理文件是否不同、size/SHA，硬链接/同物理file ID另计；不可读候选标unknown。大候选按顺序有界流式hash，不重新hash全部25GB。内容相似但SHA不同不算可删量。
6. 给root一份按集合的清理次序：无活动依赖可退出、需caller迁移、需保留事实、unknown待查。对“需迁移”给最小 SourceRef/narrative替代入口与对应现有测试；不在外仓改消费者。最后跑自己的小型只读工具测试、交付报告。

不完整恢复备份、不解压已退休归档、不产生大数据库副本，不做删除/VACUUM演练。原件不丢是本任务不可改变的底线。过期目录是否尚在实际磁盘必须实测，不能把git worktree注册清单全部当现存GB。

## 输出接口（固定，小型）

`results/storage_audit.json` schema=`storage-audit/1`：

```json
{
  "schema": "storage-audit/1",
  "generated_at_utc": "...",
  "code_snapshot": {"company_wiki_head": "...", "file_sha256": {}, "dirty_paths": []},
  "measurement_scope": [],
  "derived_collections": [
    {"path": "...", "bytes": 0, "files": 0, "active_callers": [],
     "classification": "retireable|migrate_first|retain|unknown", "reason": "..."}
  ],
  "database": {"path": "...", "bytes": 0, "wal_bytes": 0, "page_size": 0,
    "page_count": 0, "freelist_count": 0, "objects": [], "unknowns": []},
  "raw_exact_duplicates": {"candidate_groups": 0, "confirmed_groups": 0,
    "confirmed_extra_physical_bytes": 0, "unverified_bytes": 0, "groups": []},
  "cleanup_sequence": [],
  "errors": [],
  "production_mutations": []
}
```

真实unknown用null/unknowns，不拿示例0覆盖。`active_callers`填repo/ref/file/symbol及行为依据；groups只列候选logical来源+审计内部physical定位/hash/size，正文/key不输出。JSON是分析报告，不供自动执行删除。内容过多留前100例和aggregate，不生成百万行CSV。

`results/storage_audit.md`：实测bytes与估计收益分别列；最值得先动的集合、仍有依赖的集合、source事实保留表、root S5/S6实施建议与局限。全部结果/临时产物只写本目录，交付不复制到CWP；root统一摘要与引用。

## 独立测试与完成条件

若写工具，先用小SQLite/小目录测试：mode=ro拒绝写；读取带WAL的正确snapshot；缺dbstat返回unknown；raw/reparse不入清理候选；同physical对象不重复计收益；访问失败不计0。生产查询仅读、无测试下载/模型/API。只在最终责任包集中验证，不设覆盖率/签名/逐查询签收。

测试目录独立短根、同账号创建和finally恢复；已有keep内容不变，新增样本退出删除。交接给root工作目录、报告路径、工具/测试命令与结果、已确认及未确认的bytes、读取前后关键文件stat/配置fingerprint一致性；读大库没有重新全库hash要求。

完成定义是“足以指导主线分批清理的真实集合/调用者/库页报告”，不是“已删2.87GB”。root在S5/S6执行删除/收缩、测实际释放量并做一次来源回读；本线到报告就结束，不继续抢其他项目实施。
