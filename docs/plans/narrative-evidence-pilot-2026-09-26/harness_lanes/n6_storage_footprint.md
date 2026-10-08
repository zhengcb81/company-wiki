# N6-FOOTPRINT：实际空间占用与保留状态的只读盘点工具

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**ready，可独立立即实施，与两条质量线同时跑。** 较大的工具+真实实证包。它回答“本目录现在究竟多大、哪里又增长、哪些是原件或可恢复材料”，与N5跨根exact-SHA重复候选调查不同；本包不清理、不删原件、不迁移、不改运行时。

## 工作目录/上下文/写集

- 源company-wiki：`C:/Users/郑曾波/Projects/company-wiki`只读被测目标。
- **施工`C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-footprint`**已建，分支codex/n6-footprint，基线`58b74d07dd4f8b589c134ef9060a689864a8c089`，精确CI37528050044成功/75秒。
- 只新建`tools/storage_footprint/`（代码/README/tests/小fixture均在此）、`.planning/n6-footprint/`三PWF、`docs/implementation/handoffs/N6-FOOTPRINT/`。PLAN_ID=n6-footprint，已放启动草稿；HEAD/status先核，其他旧卡不是任务。
- 不写src、现有tools/raw_duplicate_audit、benchmark、CI、总PWF、源仓配置/数据库/原件，其他工作树与RF/ET/StockWiki/IQS/Dayu零写。不创建常驻监控、自动化或清理命令。

已完成S5：7104旧派生文件、8191handle退休、1490530旧span退出，DB3055841280→222408704 B，净释放5659443210 B、原件删除0。N5-DUP所谓7.27GiB是跨CWP/Dropbox/Dayu的候选上界，只有3组151MiB实读；不等于本CWP目录当前空间或已释放。旧GetCompressedFileSizeW被误当物理簇分配量，不能重犯。新包须用真实目录元数据回答本目录占用，不拿catalog登记的35GiB当本目录占用。

## CLI与输出接口（交付须实现）

```powershell
python tools/storage_footprint/run.py --project-root 'C:/Users/郑曾波/Projects/company-wiki' --max-files 100000 --max-seconds 60 --output '<本线tmp中新报告.json>'
```

显式root/文件数/时间上限，不开启模型/网络。支持fixture根和真实CWP根；默认不走外部根/其他worktree，不复制原件、不读其正文。完整扫描或partial必须明确，不能将预算内部分数字标为全量。报告`cwp-storage-footprint/1`，≤256KiB：

```json
{
  "schema_version":"cwp-storage-footprint/1",
  "scope":{"project_root":"explicit root","started_at":"UTC","complete":false,"stop_reason":"budget|complete|errors"},
  "limits":{"max_files":100000,"max_seconds":60},
  "totals":{"entries_seen":0,"files_measured":0,"logical_path_bytes":0,"allocated_bytes":null,"unknown_files":0},
  "categories":[],
  "top_directories":[],
  "retention_notes":[],
  "errors":[],
  "calls":{"original_body_reads":0,"llm":0,"network":0,"deleted":0},
  "limitations":[]
}
```

按当前存储布局分别列raw/原始TXT/来源侧录、精选/最终摘要、数据库/WAL/SHM、恢复中的AUTO任务材料、tmp/测试/缓存、计划/报告、Git与已跟踪代码、未知。只凭可证的路径/manifest类别分类，不按扩展名把业务原件判为废料；无法判断就unknown。路径属于维护存储层，在报告用root+相对路径；投资消费者仍走SourceRef，不引入路径耦合。

logical_path_bytes是按路径的逻辑长度，硬链接/稀疏/压缩可能使其与磁盘分配不一样。没有可靠平台API实证，allocated_bytes为null并注明原因，不用逻辑size/cluster估计/GetCompressedFileSizeW冒充。能只用metadata识别同file ID时另报重复路径量与口径，不将其混入已确认可删收益。云占位/离线/reparse跳过正文，不hydrate；目录遍历错误/未知属性如实partial，错误列表/路径长度有硬截断。

## 实施（先TDD，再一个集中节点）

1. 读源AGENTS、已提交S5小收据、N5-DUP说明与当前storage布局/配置模式（只读）。先列实测口径/分类表，独立PWF三个阶段：工具与反例→fixture联调→真实限额扫描/交接。不要复做duplicate SHA长测或旧migration。
2. Unit先RED：目录合计与分类不双计、原件/业务TXT/最终摘要与tmp分开、hardlink/reparse/cloud未知、越界根、权限错误（mock不改真实ACL）、预算精确停、partial非全量、输出碰原件/未知旧文件拒绝、报告体积截断、失败临时输出清理、逻辑与物理量区别。
3. 实现只读metadata扫描和聚合；不跟随链接到root外，不读原件正文/环境变量密钥/.env正文。数据库仅量文件体积，不开启/迁移生产SQLite；要逻辑条数可引用已提交只读收据并标时间，不备份整个大库或另造writer。
4. active/retry/prepared/未ACK材料不能标为可删除；无法只读证实终态时标unknown，绝不能仅凭mtime判断。原件不进建议删除列表。只形成处置建议及确定/不确定理由，不实现purge/hardlink/delete。复用既有合同事实，不新增状态库或审批签收。
5. fixture Integration用独立小目录精确给已知size、状态/分类、异常和中途停止；CLI实际子进程E2E断言JSON/stdout/exit/零正文读/原状恢复，不仅调用内部函数。源配置不动。输出原子写且上限，已有未知目标绝不覆写；测试结束新raw副本/报告/DB全部删回absent。
6. 一次真实source-root限额扫描（60秒/100000文件/≤256KiB报告），如果partial保留真实部分结果和原因，不无限重扫凑全量。明确扫描的是CWP本目录，外部根/旧工作树不偷偷计入；不读正文SHA因此不冒称重复已验证或原件全文完整。真实保护采用配置/生产库指纹与原件metadata，原件零内容读；保留本线小报告，清除临时材料。

责任测试全在tools/storage_footprint/tests，用本工作树短tmp、PYTEST_DISABLE_PLUGIN_AUTOLOAD=1、CW_BASETEMP_FALLBACK_ROOT=$PWD/tmp，命令python -m pytest -p no:cacheprovider --basetemp tmp/n6ft tools/storage_footprint/tests；再ruff check tools/storage_footprint。收口一次集中审查，日常CI/commit不新增长测/平台矩阵，不测试真实ACL。

## 交接

提交工具/短fixture/≤256KiB真实小报告、README与本线PWF，推codex/n6-footprint，不推master。HANDOFF.md/handoff.json放docs/implementation/handoffs/N6-FOOTPRINT（schema cwp-independent-handoff/1）：base_head、delivery_head、branch/worktree、changed_paths、测试/RED/GREEN/seconds、public_commands、report schema、real_vs_fixture、完整/partial扫描口径、protection、cleanup、calls、open_items。

建议按“现在保留/可另开处置/无法判断”归类，列收益口径与成本，不自动执行。MAIN验收后决定保留处置并与现有存储层对接；本工具不阻候选/预算两线的质量节点。done仅指工具可信、真实限额扫描和小报告交付，不等于空间已释放。所有owner生产文件保持、本线tmp回原样，没有新许可/签收。

已放本线PWF启动草稿/本卡副本，可随本线提交。真实文件树可能在扫描期间变化（两线共享Git对象），声明测量窗口与不稳定项，不能冒充文件系统原子快照；不为等静态树去停其他harness。
