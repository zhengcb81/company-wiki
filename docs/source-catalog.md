# 分布式原始资料目录与 Markdown 索引
> **当前状态（2026-10-03）**：旧的全库 Worker/登录启动与 `normalize`、`summarize`、`run` CLI 入口已退役。当前维护命令和替代叙述批次方案以 [company-wiki 主计划](plans/narrative-evidence-pilot-2026-09-26/task_plan.md) 与根 README 为准；本页随后内容保留为历史实现背景，不能照旧命令启动 Worker。


## 目标与边界

source catalog 只读扫描多个原始资料目录，记录内容 SHA-256、所有位置、文档类型、实体、来源状态和派生文件。Dropbox、dayu portfolio 等外部原件不会被移动、复制、改名或写回；SQLite、normalized Markdown、summary Markdown 和 CSV 索引全部写在 company-wiki 的 `.source_catalog/`。只有用户或上层研究流程显式请求一个确认缺失的来源时，统一 acquisition writer 才会把 adapter staging 中的新原件写入 company-wiki 自己的 `companies/{公司}/raw/**`。

索引扫描与后处理彼此解耦：`scan` 完成后即可查询所有原件；规范化和摘要由登录后常驻的低优先级 worker 逐份续跑，鼠标和键盘活动不会暂停它。worker 摘要使用 `config.yaml` 配置的 MiniMax M3，并沿用 MiMo 2.5 Pro fallback；输出仍只允许来源事实，不产生目标价、买入/卖出评级、仓位、估值、SOTP、正式研究报告或 accepted/rejected 投资结论。dayu 的 `.rejections` 只映射为 `upstream_rejected` 来源/解析状态。

## 配置

默认配置是 `config/source_catalog.yaml`，支持两个显式路径 token：

- `${PROJECT_ROOT}`：company-wiki 根目录；
- `${USER_PROFILE}`：当前 Windows 用户目录。

当前配置扫描：

1. `companies/*/raw/**`；
2. `../dayu-agent/workspace/portfolio/**`；
3. `${USER_PROFILE}/Dropbox/Stock/**`。

`directory` root 只接收文档 allowlist，自动排除 `.git`、`node_modules`、虚拟环境、缓存和 `.py/.go/.ts/.vue/.lnk/.partial` 等非文档文件。

## 数据模型

| 层 | 含义 |
|---|---|
| `sources` | 以 SHA-256 为 identity 的不可变内容；同内容只保留一条 |
| `locations` | root、相对/绝对路径、mtime、文件角色和位置级 SourceManifest；同内容可有多个位置 |
| `documents` | 以原始 primary 内容为 identity 的逻辑文档、类型、日期、实体和来源质量状态 |
| `artifacts` | `original`、`processed_docling`、`normalized`、`summary` 等文件 |
| `evidence_spans` | 绑定 Source ID 的页码/段落/表格 locator 与 parser/version/quality |
| derived duplicate view | active `original_primary` 同 document/source SHA 的 canonical location 与 `exact_copy` 位置；sidecar/attachment 不误标 |
| semantic duplicate view | 共享 `documents.text_fingerprint`（归一化文本 SHA）但字节 SHA 不同的文档组（`semantic_copy`）；仅展示，不可回收 |
| acquisition journal | query-first、下载、下载后二次去重、失败等结果的 append-only receipt |

现有 SourceManifest/EvidenceSpan v1 不修改。位置级 manifest 仍可用自己的 root 验证；跨 root 去重由外层 location catalog 表达，避免同 source ID 的不同 `original_path` 在 SourceExport v1 冲突。

## 重复检测：exact 与 semantic

- **exact（字节级）**：whole-file SHA-256 完全相同的不同文件名/路径归为同一 `exact_copy` 组，canonical 受保护、其余可经控制中心回收。这是默认且唯一可回收的重复类型。
- **semantic（文本级）**：`documents.text_fingerprint` = 抽取文本经 NFC + 空白折叠后的 SHA-256。同指纹、但字节 SHA 不同的文档归为 `semantic_copy` 组（如被另一程序重新编码/加水印/重存的同内容 PDF）。**零误报**：文本必须归一化后完全一致才匹配；不抓小幅文字修订。`semantic_copy` **仅展示/提示，不可回收**——回收流程只认字节级 `exact_copy` 并校验 SHA。

`text_fingerprint` 在 `normalize` 时自动计算。对迁移前已 normalize 的历史文档，用 `fingerprint-backfill` 补齐（只重解析原件取文本、只 UPDATE 指纹列，不动 normalized/summary 产物，幂等）。扫描型 PDF/不可解析格式指纹为 NULL，自动排除在 semantic 分组外。

查询与导出：`duplicates --include-semantic`、`semantic_duplicates.csv`、`index.md` 的 "## Duplicate groups" 与 "## Semantic duplicate groups" 两个小节。

## dayu-agent 兼容

dayu portfolio 的一个 filing 目录被视为一个逻辑文档：

- 原始 PDF/HTML 是 `original_primary`；
- XBRL/XML/XSD 等是 `original_attachment`；
- `meta.json`/manifest 是 `metadata`；
- `*_docling.json` 是 `processed_docling`。

当 `meta.json.pdf_sha256` 与 primary PDF 一致时，normalizer 优先使用 Docling Markdown、page provenance 和 table provenance；否则回退到 page-aware PyMuPDF，不猜测页码。

## 当前可用命令

旧版全库转换、常驻 Worker 和登录启动命令已退出。当前以 `task_plan.md` 中的有限叙述批次为处理入口。

```powershell
# 只读统计来源候选
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --dry-run

# 查看目录状态与剩余旧 Worker 状态
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml status
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-status

# 只在发现残留旧进程时停止；清除可能遗留的登录任务
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-stop
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml uninstall-startup

# 显式发起一份来源下载
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml ensure \
  --entity "公司名" --document-kind annual_report --as-of-date YYYY-MM-DD \
  --allow-download

# 维护查询与导出
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml query "公司名"
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml export
```

### Source-only scheduler policy

登录自启动的 live worker 使用不可由 YAML 扩展的固定顺序：`scanning → normalizing → fingerprinting → summarizing → exporting`。每次调用 catalog 前，policy 都校验 stage 与精确方法名；unknown、错配或 research/valuation/assessment/wiki writer token 一律 fail-closed，且在 catalog 或 LLM 调用前停止。worker 不导入 legacy `scripts/scheduler.py`，不调度投资研究、评估、估值或 Wiki writer。

其中 summarizing 只使用既有来源整理 prompt 和投资语义输出拦截，LLMClient 的职责标签固定为 workload=`source`；provider、model、base URL、credential 与fallback仍由既有配置控制。`extraction-quality` 目前保持 on-demand 的只读API/CLI：没有bounded quality queue前，live worker不会每轮无界遍历全部文档。单线程、pause/stop、AC-only、低优先级、失败退避、自适应poll与现有状态字段保持不变。

`ensure` 的 adapter 命令、版本、外部项目 cwd、timeout 与 staging 路径在 `config/source_acquisition.yaml` 中版本化。港股/美股适配器不导入或修改 Dayu：它调用 Dayu 已有 `python -m dayu.cli download`，传入 `--ticker/--forms/--start/--end/--base/--config/--quiet`，让 Dayu 仅写入 company-wiki 分配的隔离临时 `--base`；本项目只按退出码和该临时目录中的公开 `portfolio/{ticker}/filings/{document_id}/meta.json` 读取结果，导入主原件后清理临时 workspace。Dayu 的长期 portfolio、源码和仓库状态均不写回。

证券身份缓存位于 `.source_catalog/security_master/{cn,hk,us}.json`，每个市场独立原子更新。CN 使用 CNINFO；HK 优先使用 HKEXnews 中文证券表与 HKEX Full List 的 Equity 交集，Full List 异常过小时改用 HKEX Standard Transfer Form 代码交集；US 使用 SEC company tickers 与 Nasdaq Trader symbol directory 交集。生产刷新要求每个市场至少 1,000 条，低于门槛的解析结果不得覆盖旧快照。港股 canonical name 保留 HKEX 官方繁体名称，`catalog` extra 中的 OpenCC 只生成简体 alias。刷新某一市场失败时保留该市场旧快照；没有对应快照时返回 unavailable，不把“主数据不可用”误报成“公司不存在”。不指定 market 的跨市场识别要求三份快照齐全。LLM 不参与身份确认；ticker exact、官方名称/alias exact 或唯一强模糊匹配以外的情况都返回候选并停止。

整体流程固定为：下载前查索引 → adapter discovery → 带 provider ID 再查索引 → 只写 request staging → SHA/MIME/路径校验 → 下载后再按 SHA 去重 → 新内容原子写入 company raw 并创建 immutable `*.source.json` provenance → 定向重扫与 provider 强身份复验。相同字节已存在时不会创建第二份 canonical 原件；结果仍进入 `acquisition_attempts.jsonl/csv`。

默认没有自动“猜缺什么并批量下载”的任务。revenue-forecast 等上层只能先调用 read-only resolve，并在明确缺口时显式调用 ensure。Pause 状态会拒绝带 `--allow-download` 的 ensure，因此在不希望占用网络/磁盘/浏览器资源时，双击控制中心选择 Pause 即可同时阻止后台处理和统一下载入口。

## 旧 Worker 已退役

旧版周期扫描、全库 Markdown 规范化、EvidenceSpan 批量生成、后台摘要及 Windows 登录启动均不再是支持的运行路径。CLI 不提供 `normalize`、`summarize`、`run`、`worker`、启动/恢复或安装登录任务命令；旧 PowerShell/VBS 启动器已删除。

旧目录中的 worker 状态与运行日志仍作为历史诊断数据保留；`worker-status`、`worker-stop` 与 `uninstall-startup` 仅用于检查和收尾。当前有限叙述批次、空间预算及迁移顺序以 [主计划](plans/narrative-evidence-pilot-2026-09-26/task_plan.md) 为准。

## 输出

```text
.source_catalog/
├── catalog.sqlite3
├── worker_control.json
├── worker_runtime.json
├── worker_instance.lock
├── worker_state.json
├── worker_runs.jsonl
├── acquisition_attempts.jsonl
├── duplicate_cleanup_events.jsonl
├── staging/
├── derived/{sha256[:2]}/{sha256}/
│   ├── normalized.md
│   └── summary.md
└── index/
    ├── documents.csv
    ├── locations.csv
    ├── duplicates.csv
    ├── acquisition_attempts.csv
    ├── duplicate_cleanup_events.csv
    ├── artifacts.csv
    └── index.md
```

`artifacts.csv` 是完整索引表：每一个 original location、normalized Markdown 和 summary Markdown 都是一行。`documents.csv` 是逻辑文档视图，`locations.csv` 标记 canonical/duplicate 位置，`duplicates.csv` 是完全重复组，`acquisition_attempts.csv` 是统一复用/下载回执，`duplicate_cleanup_events.csv` 是用户选择回收副本的 append-only 审计读模型，`index.md` 提供汇总统计。

## 增量与恢复语义

- 相同 root/path 且 size+mtime 未变：复用已有 hash/manifest；
- 内容相同但路径不同：新增 location，不重复 normalized/summary；
- 路径消失：标 `missing`，不删除 source、document 或历史派生物；
- 路径内容改变：location 指向新 source identity，旧 source 保留；
- parser/summary version 变化或 `--force`：原子替换项目内派生文件并更新 artifact；
- worker 被关机、注销或异常终止：已提交的单份结果保留，下次从首个 pending 文档继续；
- 无解析器、加密、空输出或解析错误：仍生成 truthful Markdown stub，状态为 `unsupported`/`partial`/`failed`，不能伪装成功。

## 格式支持

- PDF：dayu Docling（sidecar hash 与原 PDF 一致时优先）或 page-aware PyMuPDF。PyMuPDF fallback 现在把 physical page、页内 paragraph、全局 normalized char range、空页和可验证表格 cell locator 交给 canonical `IngestService`；先按 table bbox 排除正文中的重复表格 block。table API/geometry 不可用时只保留带 `layout_ambiguous` 的正文，不猜 cell；损坏、加密或文档级打开失败仍生成 truthful unsupported stub 和零 EvidenceSpan；
- DOCX/DOC：python-docx / antiword；
- XLSX/XLS：openpyxl / xlrd；
- PPTX：python-pptx；
- HTML/HTM/MHT：BeautifulSoup + markdownify / MIME parser；
- TXT/MD/CSV/JSON/XML/XSD：确定性文本 adapter；
- 旧 PPT、图片 OCR：当前没有可信 parser，生成 `unsupported_format` stub 并保留索引位置。
