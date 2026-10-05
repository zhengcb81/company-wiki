# P5-STORAGE：旧派生与数据库降容执行工具

**ready，可以立即开工；较大代码包。** 源码属于company-wiki，但必须在独立worktree，仅新增工具/专属测试。外线交付可执行工具，MAIN负责旧caller退休、新质量语义、合入和实际生产清理；本卡不执行生产删除。

## 1. 目标与实测依据

旧derived历史实测7,104 files/2,826,010,634 B，其中normalized正文约97.3%；DB约3.06 GB，1,490,530条旧EvidenceSpan全部属于active来源。旧`prune_retired_evidence`只面向retired文档并依赖archive流程，不是本次active旧全量派生的解法。用户底线只有原始下载文档不丢、来源事实保留；不做46GB/完整DB备份恢复演练，不创建第二个庞大归档库。

实现可重复执行的四个维护操作：**inventory、retire-derived、prune-spans、vacuum**。每一步能在当前真实schema的隔离fixture端到端证明；报告实际逻辑删除、实际文件释放和VACUUM物理释放，不把freelist或历史估值当释放量。不能仅再写一个只读审计报告。

## 2. 隔离、写集与固定边界

- 源仓：`C:/Users/郑曾波/Projects/company-wiki`，已发布基线`f7754065ecc501d54054c3531fbe77a201b48afb`；当前源仓只有用户`config/source_acquisition.yaml`dirty，不复制/修改它。
- worktree：`C:/Users/郑曾波/Projects/cwp-lanes-20261005/cwp-storage-tool`。
- 分支：`codex/p5-storage-retirement`，基于最新origin/master且至少含f775406。

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/p5-storage-retirement 'C:/Users/郑曾波/Projects/cwp-lanes-20261005/cwp-storage-tool' origin/master
```

目录/分支已存在时先核身份/status，只复用本卡树或新兄弟目录，不reset/切MAIN树。

**唯一写集**：新`tools/legacy_storage_retirement.py`、新`tools/legacy_storage/`模块、新`tests/unit/test_p5_storage_retirement*.py`、新`tests/integration/test_p5_storage_retirement*.py`、worktree内`.planning/p5-storage-retirement/`与`docs/implementation/handoffs/P5-STORAGE/`。不改`src/`、现有测试、DDL/schema、pyproject/CI/hook、config、producerwire、总PWF或任何外仓。不要新增另一个Store/任务数据库或后台Worker。

复用当前catalog配置/锁/数据库读模型/SQLite和SourceRef公开reader；运行时可调用本仓已发布模块，但不改它们。新工具部署路径属维护层，不把物理路径加入业务DTO。MAIN不会改这批新路径；本包也不改MAIN正在处理的runtime/source_catalog。

## 3. 维护入口与输出接口

统一薄CLI（参数命名可按本仓惯例细化，handoff给最终精确命令）：

```text
python tools/legacy_storage_retirement.py inventory --config <isolated catalog> --output <small manifest>
python tools/legacy_storage_retirement.py retire-derived --config <same> --manifest <same> --receipt <small report>
python tools/legacy_storage_retirement.py prune-spans --config <same> --selection <explicit parser/source selection> --keep-refs <actual protected refs> --receipt <small report>
python tools/legacy_storage_retirement.py vacuum --config <same> --receipt <small report>
```

inventory严格只读，不调用可建库/迁移的Store初始化。mutating入口是一次明确操作，不要求签名、授权JSON、人工review、等待窗口或gold gate。没有隐式“自动删全库”；范围来自明确的old generator/role/path或parser/source选择，执行时核当前对象及来源事实，未知对象报告并保留。

报告schema `cwp-storage-retirement/1`核心字段固定：`operation`、`dry_run`、`status`、`error_code`、`selection`、`source_facts_before`、`source_facts_after`、`protected_objects_before`、`protected_objects_after`、`candidates`、`deleted`、`already_absent`、`files_bytes_before`、`files_bytes_after`、`database_bytes_before`、`database_bytes_after`、`page_count_before/after`、`freelist_before/after`、`foreign_key_check`、`integrity_check`、`resume_notes`。无错误error_code=null；数值实际测量，不填伪0或“预计已释放”。这是工具结果，不是新的许可合同。

manifest只含必要ID、范围、当前对象hash、聚合digest/计数与恢复信息。150万span用流式aggregate/digest，不逐行复制raw_text/span_json到manifest或归档；不得持久保存另一套全文。保持小报告，实际bytes写到handoff。

## 4. 数据分类与操作顺序

### A. inventory与保护快照

读现有schema与source事实表，逐表分类，保守保留未知表。来源/版本/位置/根/身份/metadata assertion/撤回恢复/amendment/supersession等事实保留；原件永不入candidate。新`narrative_artifact_versions`与`.source_catalog/artifacts`（新对象）保留，prepared/visible和AUTO预算/未知请求/恢复材料不碰。

旧候选只来自明确旧`artifacts` role/generator及`catalog_dir/derived`下对应对象，支持normalized/summary/sections；不是只凭扩展名递归扫删所有Markdown。坏路径、逃逸、junction/reparse、未知generator、实际hash改变、非本库对象具名排除。报告缺失文件/悬空记录，不伪称它们刚被删除。

对source事实做确定性逐表count/digest，针对candidate和保留对象测字节。不得创建整个生产DB备份；隔离fixture可以小数据库用于故障测试，不跑生产全备份恢复。

### B. retire-derived（只退物理旧正文及其复用句柄）

使用现行schema支持的不可复用状态或删除对应旧artifact记录，并证明旧handle不会再以completed可消费状态指向不存在文件；不能凭空造成功handle或让raw/source变retired。若有真实FK/关联记录，按当前schema处理，仅派生状态受影响。来源事实digest与所有新narrative objects必须不变。

库事务/既有catalog锁负责写入一致性；元数据先确保不再可消费，再unlink精确旧文件。若中断在两者之间，rerun根据当前记录/小manifest完成余项；已有缺失只计already_absent。异常只停止本批并保留小恢复信息，不把2.8GB全文复制回来。

不得删除整catalog目录、companies/dayu/Dropbox、staging、security_master、git目录、AUTO DB或新final对象。每个删除target最终绝对路径包含检查，Windows端到端原生路径操作；不跨shell拼命令删除。

### C. prune-spans（与物理文件分开）

只处理明确旧parser/version/source范围的旧全量span，保留`keep-refs`实际指向的source+locator/span ID和未知parser。不能按“来源active/retired”决定所有派生价值，也不能一键DROP evidence_spans或删除source/document。

当前真实span表有document/source/locator、raw_text/span_json、parser_name/version/parse_status；不是artifact_id关联。读实际schema实现筛选，不猜外键。source事实和新narrative bundle内的精选span/locator不变。清理前后验证keep集、引用定位、FK和新公开reader可用；不把旧EvidenceQuery空结果伪称全文已解析。

本包只提供精确选择/保留/执行能力。MAIN必须先核旧span消费者去向；不要为工具编码引入“下游人工签收文件”。如果当前没有足够事实证明某parser属于旧全量，inventory报告hold并保留它，不猜测生产删除。

### D. vacuum与实际空间

事务外单独VACUUM，复用SQLite标准能力；核活动writer/剩余临时空间，错误具名停止，不截断/替换原库来腾空间。记录vacuum前后文件逻辑bytes/page_count/freelist及实际可测磁盘变化；两者口径分开。

测试证明删除后source facts/new final/raw reader不变、FK/integrity正确。VACUUM中断库仍可读或有明确小恢复定位；不承诺未经验证的整个46GB恢复。成功后清理测试工作文件，生产恢复点处置留MAIN的大节点。

## 5. TDD和测试包

1. 读本卡、[S5/S6细则](../s5_s6_legacy_storage_implementation.md)、当前store/schema、artifact validator、SourceRef/narrative公开reader与旧prune/archive模块；用CodeGraph做结构调查，字符串/schema用原生搜索。不要复活已删除一次性archive脚本。
2. 先RED保护边界：只读inventory零DB/文件写；原件/新final/unknown对象不入候选；实际路径或bytes改变拒绝；相同请求重复不重复删除/夸大释放。
3. 实现A/B，fixture使用真实CatalogStore/schema及旧normalizer/summary等现成测试生产者，不能自造一个省略约束的SQLite表。验证retire后handle不可复用、SourceRef raw实读成功、span仍在、源事实未改。
4. 先RED再实现C/D：explicit parser/source与keep定位保持；外键/事务异常；DB阶段和file阶段中断后幂等；PRAGMA freelist与VACUUM物理bytes分开。故障测试小fixture，不整库备份演练。
5. 一次离线真实原文E2E：只读复制CWP中微2025年报（SHA `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`）及本地TXT样本进入独立短根。生成旧derived/span与现有Replay新final作为混合fixture，顺序执行四操作，公开SourceRef raw read及新narrative CLI replay前后通过；metadata明确fixture，模型用本地Replay，网络/下载/外部LLM0次。
6. 跑新工具责任包及有影响的既有artifact/SourceRef/narrative reader回归，节点一次静态/快速门。将新integration真实原文测试保留节点opt-in，不塞每commit或日常CI多分钟强门。

独立根运行前记录存在状态与小快照，finally关DB/WAL/pipe/子进程并恢复原样；开始不存在则结束删除。测试报告在根外，含实际文件/DB变化与校验摘要；不保存全文、生产库副本或大trace。

## 6. 完成标准与MAIN边界

- 四维护入口真实可运行；不是只有设计/audit或空占位。
- 正常/中断/重复fixture执行有明确小恢复信息，源事实、raw bytes、新final、keep引用都保持；错误不伪报释放。
- 清理前后files/bytes、DB/freelist/VACUUM实测，原件公开CLI及新final完整locator replay仍可用，测试根恢复。
- 只改新工具/专属测试/本线文档；没有schema、CWP核心、生产DB/derived/config或外仓写入；0付费调用。
- 单仓工具交付≠生产已清理。MAIN合入后迁CWP旧caller及RF默认，处理质量/metadata_only语义，再执行真正S5/S6并发布总收据。

## 7. 交接

提交`docs/implementation/handoffs/P5-STORAGE/HANDOFF.md`、`handoff.json`及小型示例manifest/report。遵循[统一交接字段](p5_parallel_packages_2026-10-05.md#统一交接格式)，`metrics`填写逐operation实测files/bytes、DB/page/freelist、source facts count/digest、新final/keep对象摘要、raw read/replay结果、异常恢复与临时root前后值。

列出实际旧generator/parser分类、工具命令、被保留的未知对象与必要MAIN接线，不交生产删除建议的假已执行状态。正常提交到本codex分支；MAIN核新增写集、集中节点测试后统一合入，外线不合main/执行live清理。
