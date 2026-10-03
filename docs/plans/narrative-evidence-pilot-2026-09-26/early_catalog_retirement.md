> 2026-10-03 当前施工由 [task_plan.md](task_plan.md) 的S0–S6统一定义。本文保留历史技术背景，旧审批/签收、原件处置和逐小步审查要求不再执行；原件全部保留。

# 46 GiB 旧库提前退役：可执行审查卡

> **2026-09-26 的 F0–F5 已完成。** 本卡保留此次 46 GiB 旧库退役的原设计与严格运行门禁；实际文件大小、查询差分、两轮烟测、删除和空间收据见 [本次运行卡](implementation_run_2026-09-26.md)与[空间账](stepwise_space_budget.md)。用户排除完整落盘恢复演练，已用 `zstd -t` 与全量解压流 SHA/长度替代；旧库已按精确路径删除，新库与完整备份保留，Worker 仍暂停。以后同类迁移按[大节点审查节奏](milestone_review_cadence.md)避免重复扫描 46 GB；新叙述性证据流水线仍按 W0–W7 独立实施。

## 1. 为什么可以提前做

2026-09-26 只读实测：生产 `catalog.sqlite3` 为 49,677,344,768 B（46.266 GiB），WAL 0 B，freelist 9 页。完整目录/历史元数据只有 17 张非 `evidence_spans` 表，共 189,580 行。用只读 immutable 源库在系统临时目录复制这些表、原始 DDL 和非 span 索引，临时库为 **225,280,000 B（214.84 MiB）**，`foreign_key_check` 无错误，`quick_check=ok`；演练产物已自动清理，未改生产。

通过 `idx_documents_status_kind` + `idx_spans_document` 精确索引计数，`source_status='active'` 文档对应 **1,490,530** 条旧 span。第二次临时演练复制全部 17 张目录表与这些 active span，并重建所有现有索引：临时库 **3,059,200,000 B（2.849 GiB）**，共 1,680,110 行，`foreign_key_check` 无错误，`quick_check=ok`，耗时约 143 秒（含完整性检查）；临时库已清理。这是实测的**逻辑活跃子集**大小，不等于未来生产重建速度或服务质量已经过关。

另有 `.source_catalog/derived` 约 2,826,010,634 B、`.source_catalog/index` 约 45,052,670 B、`source_manifests/archive/2026-08-07/retired-evidence.jsonl.gz` 约 5,207,478,767 B。ADR-009 称该 gzip 包于 2026-08-07 归档 25,708,956 条 retired span；H01 独立复核指出它缺逐项 hash/不可覆盖发布保证，**不能把该包直接当唯一可恢复备份**。这些目录另行审查，不随主库切换清理。

当前 `worker_control.json` 的 desired_state 为 `paused`。StockWiki 当前 `config/source_provider.yaml` 中 company-wiki provider 为 `enabled: false`；revenue-forecast 经 filing-fetch/company-wiki 来源解析使用上游目录信息；invest-quick-scan 的有限代码搜索未发现直接打开本生产 SQLite。后两项及 StockWiki 的旧快照/缓存仍须在 F3 用真实合同测试核对，不能凭本轮搜索宣布无消费者。

## 2. 选项与推荐

| 方案 | 切换后的本机活跃 DB | 旧证据查询 | 提前释放的本机空间 |
|---|---:|---|---|
| **A：保留目录表 + active span（推荐）** | 实测约 2.849 GiB | active 旧 locator 继续可查；retired 旧 locator 必须明确提示归档/暂不可读 | 若完整旧库压缩快照留 C 盘，净释放 = 46.266 − 2.849 − **实测快照 GiB**；若快照在外部独立卷，本机约释放 43.417 GiB |
| B：仅保留目录表 | 实测约 0.210 GiB | 所有旧 span 暂不可查，必须显式报 `legacy_evidence_unavailable` | 本机释放更多，但当前证据服务退化更大；只在用户明确接受该功能窗口时选 |
| C：等全新流水线建好才迁移 | 待测 | 旧服务保持 | 46 GiB 持续占用，不能满足尽早释放空间目标 |

推荐 A。新增[逐步空间账](stepwise_space_budget.md)已对当前未变化的完整旧库运行只读 `zstd -3 --stdout` 压缩计数：输出流 **6,198,704,362 B（5.773 GiB）**；没有真正写备份。若正式快照字节数相同并留在 C 盘，A 在 F5 后预计净释放 **37.644 GiB**；正式收益仍按快照文件与切换后同卷可用空间结算。当前 C 盘空闲实测 85,058,437,120 B（79.217 GiB）；遵照用户取消完整恢复演练后，旧库、影子库和备份同时留在 C 的预计新增峰值约 **8.622 GiB**，理论余量约 70.595 GiB，尚未计 WAL/其它进程与安全缓冲。

## 3. F0–F5 顺序与硬门禁

| 卡 | 操作 | 完成证据与停止条件 |
|---|---|---|
| **F0 冻结范围** | Worker 保持 paused；确认无生产扫描、解析、prune、下载写入或其它 catalog writer，WAL 为 0；登记 DB/SHM/WAL、schema、所有表行数、源状态、文件 stat、C 盘可用空间、ADR-009 90 天保留要求与 H01 风险。锁定确切目标文件及当前 Git dirty 状态 | 有不可解释的写入/打开句柄、WAL 非零且无法一致 checkpoint、来源目录异常或空间不足即停；不删整个 `.source_catalog/`，不运行 `prune_retired_evidence`/`VACUUM` |
| **F1 制作活跃影子库** | 固定可审计脚本：复制现有全部非 span 表的 DDL/数据/索引及所有 active 文档的全部旧 span；保留 PK、UNIQUE、FK、索引和原始 source/document/artifact ID。给 `catalog_meta` 加明确 `legacy_evidence_retention=active_only`、旧库 hash/截止时间/快照 ID；不复制 retired span 到热库 | 原生产 DB 只读；目录表行数和稳定主键集合相等，active span 数与逐行 digest 相等，`foreign_key_check` 无错误、`quick_check=ok`，无额外 active span 丢失；重复运行同输入产物语义一致。不能用 `CREATE TABLE AS` 丢约束 |
| **F2 完整旧库备份与流式验证** | 在锁定无写窗口生成唯一名 `.partial` zstd 全文件快照，记录原 DB SHA-256/长度与快照 SHA-256/长度；运行 `zstd -t` 并把**完整解压流直接送入 SHA-256 计数器**，结果与原文件 SHA-256/长度完全一致后原子发布；原库只读 `quick_check` 与源/文档/active/retired 样例查询仍独立执行。**不写完整恢复库。** | 不能仅相信 2026-08-07 gzip 包、抽样解压或单独 `zstd -t`；字节同一性未证、备份位置/容量不稳定、原库 `quick_check` 失败、源文件或 WAL 在窗口内变化即停。此法证明备份字节可完整解压且与原库相同，未验证未来恢复到磁盘时的环境/时间；压缩快照保留到逐来源保留期与新方案验收/引用审查完成 |
| **F3 服务与下游差分** | 同输入比较旧/影子 `query`、`resolve`、filing-fetch 复用、实体/类型/时间过滤、缺失/退役状态、artifact handle 和 active `evidence/evidence-list`；检查 StockWiki 当前 provider 与已有快照、revenue-forecast、invest-quick-scan 的真实读路径 | active 查询定位与数据一致；retired 旧 locator **显式返回归档不可用**或经验证的冷读结果，绝不伪报 `not_found`/空结果。现有 `EvidenceQueryService` 对空表会报 `NotFound`，必须先做版本/覆盖标记及失败关闭适配；下游所有者按其当前合同签收 |
| **F4 文件级切换** | 按维护窗口确保 writer 停止、Worker paused；以确切路径把旧主库暂改为待退役文件并把 F1 验证库切到 `catalog.sqlite3`；检查 DB/WAL/SHM 与运行锁，跑 F3 核心烟测；失败立即切回。持续观察一段预注册窗口 | 切换只涉及 catalog DB 文件与必要 WAL/SHM 处理；`worker_control.json`、运行/抓取/清理审计、security master、raw、source_manifests、derived、index 不动。切换后不得恢复旧全量 normalize 或自动 prune |
| **F5 删除旧原文件** | F2 完整解压流与原库逐字节同一、F4 稳定、切回旧文件已演练后，重新核验**待退役旧 DB 的绝对路径、长度和 SHA-256**与冻结清单完全一致，再对该单个文件作非递归删除；提交删除 receipt 与实际磁盘增量 | 任一身份不符、活跃查询失真、归档提示未生效、Worker 不再 paused、下游引用仍需要热 retired span、流式校验失败或净释放未达预注册目标，即保留旧文件。禁止通配符/目录删除 |

完整旧库的压缩快照保证旧数据仍可恢复，因此可以比新解析/摘要系统更早地释放 46 GiB 原 SQLite 的本地空间；若快照留在 C 盘，它仍占压缩后的空间。ADR-009 的 90 天保留原则不能靠旧目录日期给全体 retired 记录一刀切，H01 指出的自动 prune 路径继续硬禁用。以后是否清理该压缩快照与另有 5.21 GB 的退休归档，要逐来源验证保留期、引用和恢复性，另列审批。

## 4. 给实施者的明确边界

1. 用户本轮已授权实施 F0–F5，但明确排除完整恢复演练。F4/F5 只能在实际 DB 文件路径/大小/hash、备份流验证、F3 差分、切回步骤和审查 receipt 都具体可复核后执行；授权不使未通过的门禁自动通过。
2. F1 的临时演练证明大小和关系完整性，**没有**验证所有 API/下游，也没有创建可用于生产的脚本或快照。实施时须把版本化脚本、输入/输出 hash、命令、耗时、故障注入和独立复审写成 receipt，不能复用一次性试验输出。
3. 假如 F3 无法让 retired 查询明确失败关闭，可暂时只发布经过审查的只读目录/resolve 接口，不得把 active-only 库直接冒充完整版 EvidenceSpan catalog。若当前活跃消费者必须同步 retired span，则保留旧库或先实现经验证的冷读。
4. 新文档的 W2/W3 路径必须另行通过选择性证据、业务表、IR 问答、中文检索与净新增字节测试。F0–F5 只解决旧库本机占用；它不会自动阻止未来再次生成 46 GiB。

## 5. 新仓库与逐文档迁移的适用范围

2026-09-26 只读 `PRAGMA` 确认旧库 `auto_vacuum=0`、`journal_mode=delete`、freelist 仅 9 页。旧 46 GiB 是**一个共享 SQLite 文件**；对某份文档执行 `DELETE FROM evidence_spans ...` 后，空页留在库内，Windows 看到的文件通常不会按文档缩小。每处理一份就在旧库删除对应行还会制造大量写事务和索引维护，最终仍需重建/切换整库文件。不能把“已删行数”当作已释放磁盘字节。

可以建立一个独立的 **v2 数据目录**，必要时将新版代码放在新 Git 仓库；但 Git 仓库本身不是省空间手段。当前 `.gitignore` 忽略 `*.pdf`、`**/raw/` 与 `.source_catalog/`，克隆代码不会自动带上原文。把 PDF/TXT 再复制入新仓库会在迁移期增加占用，提交二进制进 Git 还会保留历史版本。若另开代码仓，必须明确它是 company-wiki 上游来源系统的继任实现，通过版本化只读 export 服务下游，不与旧仓同时宣称 canonical 数据状态。优先选择同项目的隔离 `catalog_v2` 数据根，复用同一份 immutable raw 和 SHA/source manifest。

新版按 `source_sha256 + parser_version + selection_version` 输出**每来源一个可原子发布的小型证据包**，保存选中的业务片段、多锚定位、覆盖/跳过账本与来源摘要；中央小索引只留身份、状态和包位置。每件文档按 `discovered → parsed → selected/skipped → verified → visible → old_derived_reclaimable` 记录版本、hash、错误与重试。只有 raw SHA、原文回读、类型/角色/时间、业务表和 IR 问答抽检、检索/导出差分、下游版本协商及回滚包都过，才把该来源的旧 `derived/{sha[:2]}/{sha}/` 文件列入精确清理清单。唯一 raw 若最终被判为不重要，可另按[原文处置 D0–D5](raw_disposition_plan.md)删除；`skipped_*` 本身不构成删除资格。sidecar/source manifest 和仍被旧消费者引用的旧产物须按各自合同审查。

逐文档清理旧 `derived` 可逐步释放其合计约 **2.83 GB** 的文件空间；已有 5.21 GB retired gzip 是整包归档，也不能按文档直接删。**46 GiB 主库仍应优先走本卡 F0–F5 的活跃子集替换与完整压缩备份**，先释放主要压力，再让 v2 逐文档迁移提高内容质量并清理其余派生文件。若日后还要清理 2.849 GiB 活跃子集中的旧 span，也应在若干批后重建小库/文件级切换，不能以逐行删除假报已释放空间。

如果决定把 raw 也搬到新数据根，应按“复制到临时路径 → SHA-256/长度/PDF 或 TXT 可读性核验 → source manifest 新位置发布并保留旧位置映射 → 所有读取方切换与回滚演练 → 删除**已核验的旧重复副本**”逐件推进。每件只清理明确列出的旧文件路径，保留迁移 receipt；同盘复制期间先占额外空间，跨盘迁移则要核对目标卷的容量和备份。原文尚未在新位置成为可恢复的 canonical 副本、或旧绝对路径仍被消费者使用时，不得删除旧文件。此步骤与 SQLite 主库退役分别验收，不能用“某份 raw 已迁完”触发旧库中的逐行清除。

对新方法判定**无需保留的唯一旧原文**，另走 D0–D5：完整覆盖和独立复审、来源/消费者处置合同、确切文件身份及可恢复性损失审查通过后，可逐件删除并留下轻量历史来源与删除 receipt。不能只因零切片、旧版 `retired` 或文件类型是通知/制度，就直接删原文。此清理不影响 F0–F5 对共享 SQLite 的整体替换顺序。
