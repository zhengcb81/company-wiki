# D0 原文与派生物只读盘点收据（2026-09-27）

## 范围与方法

- 通过 SQLite `mode=ro&immutable=1` 读取当前 catalog；对 29,409 条 `original_primary` / `original_attachment` location 逐路径执行文件系统元数据核对。
- 同时只读遍历 company-wiki 自有的 `companies/`、`source_manifests/`、`.source_catalog/derived/` 和 `.source_catalog/index/`；不打开原文内容，不跟随 reparse 目录，不运行解析、扫描或 Worker。
- 对 catalog 记录的 artifact 路径逐路径 `stat`，再按规范化路径去重；没有读取内容，也没有计算新的 SHA-256。
- 整个核验约 94 秒。它是盘点快照，不是删除清单；外部 dayu/Dropbox 根只核对 catalog 已登记路径，仍为只读来源。

## 结果

| 范围 | 文件/记录数 | 当前文件逻辑字节 | 发现 |
|---|---:|---:|---|
| 公司原文目录 `companies/` | 33,131 个文件 | 25,189,914,642 B | 登记的本地原文除 3 条已标记 `missing` 外均存在且大小与登记值一致；目录中另有 16,561 个非登记原文路径、36,886,680 B，需按 wiki/sidecar/遗漏文件分类，不能视为删除候选。 |
| 本地 `company_raw` 原文 location | 16,573 条 | 25,153,027,962 B（不含 3 条已缺失路径） | 7,524 active / 6,511,169,498 B；9,046 retired / 18,641,858,464 B。retired 只表示版本状态，不构成删除资格。 |
| 本地 `future_lake` 原文 | 1 条 | 545 B | 当前存在，登记大小相符。 |
| 外部只读原文 location | 12,835 条 | 按当前文件 stat 均与登记大小相符 | dayu 与 Dropbox 的登记路径均可访问；不归 company-wiki 删除。 |
| `source_manifests/` | 2 个文件 | 5,207,479,410 B | 只统计实际路径及长度；归档/sidecar 的逐文件引用映射尚未完成。 |
| `.source_catalog/` 全目录 | 8,214 个文件 | 12,277,797,132 B | 含 6,198,717,464 B `retirement/`、3,055,796,224 B 主库、2,826,010,634 B `derived/`、45,052,670 B `index/` 及其他控制/审计文件。 |
| `.source_catalog/derived/` | 7,104 个文件 | 2,826,010,634 B | 全目录文件级逻辑长度；不等于可回收量。 |
| catalog artifact 路径 | 8,191 条记录 / 6,714 个唯一路径 | 2,794,944,096 B（按唯一现存路径计） | 所有登记路径均存在；1,477 个路径被多条记录复用。620 个唯一路径的历史 `byte_size` 记录互相不一致，须先按当前引用和版本关系核实，不能逐旧行删除文件。 |
| `.source_catalog/index/` | 8 个文件 | 45,052,670 B | 仅元数据统计。 |
| 当前 `.source_catalog/catalog.sqlite3` | 1 个文件 | 3,055,796,224 B | 当前 active-only 主库文件长度；本轮未写入。 |

`companies/`、`source_manifests/` 与 `.source_catalog/` 三个本地目录当前合计 **42,675,191,184 B（39.744 GiB）逻辑长度**。与 F5 前同口径 83,081,999,800 B 比，目录逻辑长度减少 40,406,808,616 B（37.632 GiB）；F5 实测同卷可用空间净增 37.630 GiB。两者口径不同，物理净增以 F5 的磁盘可用空间收据为准。

本地 owner root 中，catalog 的来源 SHA 标识出 52 组双路径别名（104 个 location；登记长度合计 197,690,786 B）。按登记 SHA 与长度计算，除留一份外的 **98,845,393 B 只是重复候选上限**，不是确认可删除或已释放空间；删除前仍需 D3 冻结具体 canonical 路径、消费引用与保留状态，并由 D4 对精确路径重新完整计算 SHA。

本地引用关联补充：只读索引扫描得到 1,490,530 条 `evidence_spans`，涉及 1,636 个 source ID；其中 1 个 source ID 没有登记的原文 location，329 个 source ID 在多个 root 有 location。当前 catalog 中没有 evidence span 只挂在 `retired` location 上。artifact 记录 8,191 条均有 `source_id` 和 `document_id`。这些数据按 source ID 聚合，不能将跨 root 的 span 计数相加成各 root 的独立体量。

sidecar 树中有一个 643 B 的 SourceManifest，记录一份 115,427 B PDF 的 SHA、source ID、相对原路径及 `immutable_status=verified`；这条路径已经包含在原文 location 盘点中。另有一个 5,207,478,767 B `retired-evidence.jsonl.gz` 历史归档；本轮只 stat，未解压或读取其内容，也不把它视为可删除备份。

原文 location 核验未发现登记大小偏差、访问错误、超出 root 的解析路径或多硬链接；三条缺失路径在 catalog 中原本已标为 `missing`。owned-root 目录遍历未发现 reparse 项。artifact 历史大小冲突已在上表单独列明。以上只证明当前元数据/路径状态，不能证明内容 SHA 与 catalog 一致，也不能排除目录树中未覆盖的消费者合同。

协作变更排除项：`companies/` 中有 5 个文件的修改时间晚于 2026-09-26 00:00 UTC，合计 16,120,320 B：紫金矿业 2023 年年报 PDF（16,052,552 B）及 sidecar，以及 Microsoft 两个 8-K HTML 和 `.source.json`。它们与 revenue-forecast 当前记录的 AR2023/Microsoft 资料工作相符；本次按确切路径查询 catalog 后确认 5 个文件均**尚未登记为 location**。D0 按目录统计已包含它们，但在其来源 owner 完成接管/catalog 注册前必须保持 `hold`，不得纳入 D1–D3 删除/迁移候选；不能为“补齐盘点”擅自启动 scan/normalize。本轮没有读内容或哈希。

## D0 状态与后续

本收据完成 **D0 本地只读盘点**：登记原文路径及自有目录的当前文件/字节基线、本地 SourceManifest/artifact/evidence span 到 source ID 的引用盘点。1,490,530 条 span 涉及 1,636 个 source ID；1 个 ID 缺登记原文位置，329 个 ID 跨 root 有位置。完整跨仓 consumer 合同不属于本次本地 D0 物理盘点结论；consumer 的可用性和删除后的响应仍须通过 G0/D1 冻结，不代表可以按本收据删源。

本轮没有写生产 catalog、创建 Worker job、改 Worker 状态、删除/移动/改名 raw 或 derived 文件，也没有对外部 root 执行修改。后续每个待处置文件仍须遵守 D4 的精确路径、锁内身份复核和单次完整 SHA 门禁。
