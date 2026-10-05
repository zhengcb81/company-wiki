# P5-STORAGE 集成审查与修复顺序（2026-10-05）

状态：**交付已收到，尚未验收合入，不执行生产删除**。

- 功能提交：7ac1e3d236e22a263b88540f89a611675b5b8ab1；交接文档：f8f414a。
- base：a2563f9。17个功能新文件/3181行均在允许写集；handoff列出的报告在后续文档提交中，不能把未提交文件当功能提交的一部分。
- MAIN原有源码/现有测试写集与该卡新工具/专属测试不重叠。工具交付后的整改由MAIN收口；RF/FF外线未交付目录不改。
- 原件、不变的来源事实与新final是实际保护对象，不增加人工许可、签名或逐文件审查。

## 四项实证失败

[小样本JSON](p5_storage_review_red_2026-10-05.json)使用真实CatalogStore/schema和已有旧producer；四个独立短根均finally恢复absent。0网络/下载/LLM，生产及外包工作树零写。仅fixture副本受试验影响。

| 缺口 | 当前结果 | 正确行为 |
|---|---|---|
| manifest managed_files可指向raw | fixture原文被unlink，报告仍succeeded，来源DB digest仍一致 | 当前DB/index和路径/字节必须共同决定删除集合；raw与新final绝不能由manifest指定删除 |
| `_sections_index_sweep`扫描整个derived | 没有DB登记的孤立sections/index.json被删除 | 只处理本次当前登记的旧对象；未知/孤立index保留并报告 |
| commit后、unlink前中断 | retired行被忽略，已知旧文件永久留下；rerun报成功 | 在来源/role/generator/path/hash仍相同条件下续删已退休文件，不重复修改事实 |
| file已缺失 | completed句柄保持不变，报告failed | 同一旧记录退休，文件只计already_absent，不虚报释放 |

这些是实现/测试覆盖缺口，不是凭审查偏好加门。原handoff的26单测与真实年报E2E没有覆盖它们，不能据此执行生产清理。

## 下一实施顺序（两个集中节点）

### 节点一：候选准确性、原文保护与恢复

1. 以当前交付代码为被测对象先加入四项RED，加上当前DB角色/generator/path被换后的负例。保持真实schema的小fixture。先失败后实现，不在测试里复制实现判定。
2. manifest仅用于限定artifact IDs与已观察hash；重新读取当前DB的document/role/generator/version/path/hash/status，并与manifest/配置核同一对象。处理已知旧completed/retired及缺失对象；unknown角色/generator/位置保留。重新派生sections managed集合，每个目标限定到当前index对应sections目录、准确文件名/登记内容、字节hash、非reparse，拒绝raw/new objects路径与任何已登记original位置。不能信任manifest追加的managed路径或字节数。
3. 元数据在既有catalog锁+事务中先退休，随后逐对象unlink并实际计量。已退休但尚有旧文件可重入续删；文件缺失则只记already_absent。删除主index前保存足够小的已验证managed恢复信息，恢复不要求复制正文。去掉全derived sweep。文件unlink失败具名返回partial/failed，不报成功；重复执行不夸大释放。
4. inventory与所有dry-run用只读连接；不创建DB/schema/WAL/SHM、不拿写事务。静态无WAL的库可复用现有immutable-read策略；活动WAL需要现有SHM，否则具名诊断。报告当前before/after，不用忽略WAL/SHM的快照证明零写。

### 节点二：大库适用性与真实组合验收

5. prune不构造全库source/locator Python set、百万doomed list或逐span candidates JSON。keep集合只验证所需精确引用；在显式parser/version/source/document范围以SQL或有界流式批次删除并保留keep。计量cursor真实rowcount；protected rows计kept，不计already_absent。未知parser保留，dry-run真实只读。报告聚合而非另一份150万条清单。
6. VACUUM在操作前取source/new-final事实，操作后再读；不能像交付版把两个快照都放在VACUUM后。使用当前catalog锁，检查真实临时空间、SQLite错误与checkpoint结果；busy/中断不伪称整个数据库未动。before/after计文件/逻辑page/freelist，物理释放与磁盘free-space分列。
7. 复用当前MAIN明确的quality/metadata_only和caller迁移计划，工具不篡改source身份、公开日、期间、撤回事实。历史P5 fixture直接使用底层旧生成器，无需恢复已退役SourceCatalog方法。新对象实际根来自对象存储位置，不能只检查错误的catalog/objects空目录。
8. 集中执行工具专属Unit/故障测试；复用现有真实年报+TXT的四操作CLI E2E，前后SourceRef原文实读、新NarrativeRef完整locator replay、原件SHA/来源事实/new final全等、fixture根恢复。既有producer golden已由MAIN纠正，复核当前reader责任包，不重复全仓长包。慢E2E保持节点opt-in，不纳入日常commit/CI。

全部行为GREEN后合入main、提交并推送，更新总PWF和精确CI结果。工具接受不等于生产derived/DB已释放：仍先等P5-RF默认来源消费迁移及CWP旧底层正文消费者/质量语义退出，再按S5/S6实施生产清理，不要求重跑全部历史文件。


## MAIN节点一接续收据

独立验收树 `.codex/worktrees/p5-storage-integration/company-wiki`，分支 `codex/p5-storage-integration`。基于已发布MAIN18da250，导入原交付为候选d6b6e36/4387661；没有merge main。八项真实schema故障TDD先8 RED/26.63s；修复包21 case先20 passed/1 failed/60.48s，失败为managed子项缺artifact_id字段，修正后该幂等case GREEN3.64s。追加事务内全身份匹配后8保护/恢复cases再次GREEN21.51s。节点一提交72b11160b926e7ead0f163786f141ce2ead5f470；Ruff tool/helper/recovery全绿，commit host guard通过。旧底层业务代码src未改，真实原文/消费者E2E整体尚未复验，节点二仍pending，不把21项局部GREEN当工具全验收。

边界/spans/vacuum/recovery均调用实际parser/SQLite，已从unit移到`tests/integration/test_p5_storage_retirement_*.py`，共享夹具在`tests/support/p5_storage_catalog_fixture.py`。它们不进入CI默认全Unit包，CLI也无额外门。维护metadata只记录验证过的sections小型managed hashes以续删，不复制正文。没有新增授权JSON/签名/审批。

主线S5公开writer退休18da250已推送，pre-push快速合同GREEN，精确CI37371220690最新queued。节点一原文保护与恢复可接续，工具整体仍在候选树；下一步按本报告节点二执行。8项RED、21项组合、幂等及最终8项测试根p5red/p5green/p5final/p5bind全部恢复absent。已附着旧n4t2 worktree记录的目录实际不存在，未复用/恢复；新建托管验收树成功，无生产数据复制。


- 72b1116存储工具节点一候选已推到origin/codex/p5-storage-integration；从primary checkout运行相同baseline的正常快速pre-push GREEN，新工具专属行为此前在实际候选树验证。未merge主线、未伪称工具整体验收或生产释放。
