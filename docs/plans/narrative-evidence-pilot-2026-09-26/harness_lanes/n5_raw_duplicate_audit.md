# N5-RAW-DUP：原件重复空间只读实证与工具

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**已交付e40b4ec，MAIN集中修正/51项与CLI绿，已合入master a41244a并推远端、精确CI37523080920/57秒绿；不再重派。** [验收卡](n5_raw_duplicate_main_acceptance_2026-10-06.md)。 原件目前仍占主要空间；既有S5清理仅处理派生，不能证明原件可以继续安全降容。本包产出可实际运行的只读盘点工具，回答“还有多少完全相同字节被重复存放、是否值得下一阶段去重”。不删除、不移动、不硬链接原件，不实施对象存储迁移。

## 1. 独占范围

- 源仓`C:/Users/郑曾波/Projects/company-wiki`。
- 工作树`C:/Users/郑曾波/Projects/cwp-lanes-20261006/raw-duplicate-audit`；分支`codex/n5-raw-duplicate-audit`。
- 基线`e46108b4f30d5b7e47bfc712e360f173c00b702c`。
- 写集仅新`tools/raw_duplicate_audit/`（含测试与说明）、`.planning/n5-raw-duplicate-audit/`、`docs/implementation/handoffs/N5-RAW-DUP/`。不改src/scripts/现有tools、生产配置、公共合同、总PWF或其他包目录。

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/n5-raw-duplicate-audit 'C:/Users/郑曾波/Projects/cwp-lanes-20261006/raw-duplicate-audit' e46108b4f30d5b7e47bfc712e360f173c00b702c
```

先读SourceCatalog当前schema/配置/正式reader、S5收据及tools/legacy_storage实际说明；遵守CodeGraph结构查询。原件定位是此存储层工具职责，消费者仍pathless。生产SQLite仅显式`mode=ro`，不实例化会迁移/创建catalog的writer，不拿写锁、不VACUUM。

## 2. 实际工具与输出接口

CLI显式输入只读catalog/配置和output，支持metadata候选扫描、有限候选实际字节复核；默认限最多100组、读入量512MiB、截止5分钟，可由明确CLI改范围，不偷偷扫描全部磁盘。SHA流式1MiB，先按已登记sha/size筛候选，实际open验字节后才称exact duplicate；未实读、ACL错误、文件消失/变更另列，不混入确认节省。

识别不同source/version/location指向同一路径、同一个实际文件/hardlink、不同实际文件的相同内容、不同字节的相似文件；不能把前三种都按重复副本累加。处理Windows大小写、junction/reparse、不同root、网络/Dropbox占位文件：保留显式诊断、不追随未知外部目录、不触发云端hydrate下载。未知物理身份按不确定报告，不能伪算释放量。

`report.json` schema `raw-duplicate-assessment/1`：catalog/config SHA或只读snapshot标识、scan_scope、elapsed、limits_hit、candidate/verified/unresolved数量、重复组、保留所有source/version/location引用计数、每组distinct physical copies、logical_duplicate_bytes_upper_bound、physical_allocated_bytes可得则值否则null、实际deleted_bytes=0、protected before/after。小组项只有ID/hash/size及root-relative locator；本机绝对路径单独非Gitlocal输出。

不额外存正文、全文索引或第二来源库；Git报告≤1MiB，详细行数最多5000并明确截断。估计量是未来可能减少的逻辑副本字节，不能写“已释放X GB”。建议部分至少比较保留现状、按SHA对象化、文件系统链接三方案对source版本/移动/引用/可恢复性的影响；只给建议，不修改架构。若收益小直接建议不做。

## 3. TDD、实施与一次验收

1. 先在独立fixture设计重复/非重复集合和预期字节数，含一个文件3条location引用、hardlink两名、不同物理副本、同size不同bytes、source metadata SHA错误、变更中、ACL拒绝；RED先写计算与读取预算反例。
2. 实现只读扫描与有限流式实读；在deadline/byte cap前停止，保留部分报告。输出原子且不覆盖未知旧报告；不创建生产DB/WAL/cache/清理清单副作用。
3. Unit算账；Integration使用当前真实schema隔离DB、真实文件/hardlink（平台不支持须明确skip）；E2E在真实生产catalog只读筛候选，实际复核有限组，前后原件SHA/size/mtime与catalog/config关键文件不变，记录实际耗时/读入量。没有候选也是合法真实结果，不伪造收益。
4. finally恢复本worktree测试目录原状；小报告留下，原件从未复制/删除；0LLM/HTTP/provider。一次集中责任包和lint，不扩日常CI。
5. 提交代码与`docs/implementation/handoffs/N5-RAW-DUP/HANDOFF.md`/统一handoff.json，带精确CLI、真实scope和未验证组。未来生产去重是否实施由MAIN依据真实收益与引用兼容决定，不靠外线签收自动删除。
