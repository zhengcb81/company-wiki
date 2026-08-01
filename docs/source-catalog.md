# 分布式原始资料目录与 Markdown 索引

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

## 命令

```powershell
# 只统计，不创建 .source_catalog
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --dry-run

# 增量扫描与 hash；未变化的 size+mtime 直接复用
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan

# 只续跑一个 root（例如云盘长任务）
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml scan --root-id dropbox_stock

# 规范化与 EvidenceSpan，可用 --limit 分批执行
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml normalize

# 手工生成确定性 extractive 摘要（后台 worker 默认改用配置 LLM）
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml summarize

# 导出完整索引表
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml export

# 一次顺序执行全部阶段（适合小样本；不建议对初始 2 万份 backlog 使用）
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml run

# 查询
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml query --entity 中微公司 --document-kind annual_report

# 用精确 source_id + canonical locator 读取一个已验证 EvidenceSpan（机器可读 JSON）
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml evidence --source-id urn:company-wiki:source:sha256:<64位小写hash> --locator loc:v1/page:1/paragraph:0/chars:0-20

# 按 source 或 document 稳定枚举 locator；limit 最大 500，支持 offset
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml evidence-list --source-id urn:company-wiki:source:sha256:<64位小写hash> --limit 100 --offset 0

# 对精确 source/document 做只读提取质量诊断；只返回状态、原因、计数与locator引用
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml extraction-quality --document-id urn:company-wiki:document:sha256:<64位小写hash> --locator-limit 100

# 首次使用或需要更新时，按市场刷新官方证券主数据缓存并识别公司
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml identify --query 中微公司 --market CN --refresh

# 独立小工具；可输入公司名、简称或 ticker，输出机器可读 JSON
company-wiki-identify --cache-dir .source_catalog/security_master 小米
company-wiki-identify --cache-dir .source_catalog/security_master AMD

# 默认只读：按公司/财期解析现有来源，不调用 downloader
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml resolve --entity 中微公司 --security-id 688012 --market CN --document-kind annual_report --fiscal-year 2025 --as-of-date 2026-07-18

# 模糊公司名先经过同一身份层；只有唯一验证结果才进入现有来源 resolver
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml resolve --company-query 中微 --market CN --document-kind annual_report --fiscal-year 2025 --as-of-date 2026-07-19

# 确认缺失后显式允许下载；A 股走 StockInfo，港股/美股走 dayu
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml ensure --entity 中微公司 --security-id 688012 --market CN --document-kind annual_report --fiscal-year 2025 --as-of-date 2026-07-18 --allow-download
```

`query` 继续用于标题、实体、类型与路径等 metadata 搜索；`evidence`/`evidence-list` 是独立的精确 locator 接口，不做模糊匹配，也不猜“最近一段”。它们只返回 catalog 中已存在并重新通过 EvidenceSpan v1 校验的 span、source/document metadata 和同 source 的原件位置引用，不读取整份二进制、不触发 normalize/download/LLM、不生成研究结论。数据库以 SQLite `mode=ro` + `query_only` 打开；静态 catalog 使用 immutable snapshot 避免生成 WAL/SHM，活动 WAL 缺少既有 SHM 时直接 unavailable。缺库不会创建 `.source_catalog`，损坏 span 或 identity 列冲突会明确失败关闭。详细合同见 [Evidence Query v1](contracts/evidence-query-v1.md)。

`extraction-quality` 是与正文查询分离的确定性技术质检接口：精确读取 current normalizer artifact、source/location status 与 canonical span metadata，返回 `usable/review_required/unavailable`、reason codes、计数和 bounded locator references。结果不含 `raw_text`、整份派生正文或 artifact error 全文，不包含投资结论；unknown、ambiguous 或 integrity conflict 均失败关闭。它沿用同一 SQLite 物理只读政策，不创建 catalog、不触发 normalize/download/LLM，也不回写质量状态。详细合同见 [Extraction Quality Diagnostic v1](contracts/extraction-quality-v1.md)。

### Source-only scheduler policy

登录自启动的 live worker 使用不可由 YAML 扩展的固定顺序：`scanning → normalizing → fingerprinting → summarizing → exporting`。每次调用 catalog 前，policy 都校验 stage 与精确方法名；unknown、错配或 research/valuation/assessment/wiki writer token 一律 fail-closed，且在 catalog 或 LLM 调用前停止。worker 不导入 legacy `scripts/scheduler.py`，不调度投资研究、评估、估值或 Wiki writer。

其中 summarizing 只使用既有来源整理 prompt 和投资语义输出拦截，LLMClient 的职责标签固定为 workload=`source`；provider、model、base URL、credential 与fallback仍由既有配置控制。`extraction-quality` 目前保持 on-demand 的只读API/CLI：没有bounded quality queue前，live worker不会每轮无界遍历全部文档。单线程、pause/stop、AC-only、低优先级、失败退避、自适应poll与现有状态字段保持不变。

`ensure` 的 adapter 命令、版本、外部项目 cwd、timeout 与 staging 路径在 `config/source_acquisition.yaml` 中版本化。港股/美股适配器不导入或修改 Dayu：它调用 Dayu 已有 `python -m dayu.cli download`，传入 `--ticker/--forms/--start/--end/--base/--config/--quiet`，让 Dayu 仅写入 company-wiki 分配的隔离临时 `--base`；本项目只按退出码和该临时目录中的公开 `portfolio/{ticker}/filings/{document_id}/meta.json` 读取结果，导入主原件后清理临时 workspace。Dayu 的长期 portfolio、源码和仓库状态均不写回。

证券身份缓存位于 `.source_catalog/security_master/{cn,hk,us}.json`，每个市场独立原子更新。CN 使用 CNINFO；HK 优先使用 HKEXnews 中文证券表与 HKEX Full List 的 Equity 交集，Full List 异常过小时改用 HKEX Standard Transfer Form 代码交集；US 使用 SEC company tickers 与 Nasdaq Trader symbol directory 交集。生产刷新要求每个市场至少 1,000 条，低于门槛的解析结果不得覆盖旧快照。港股 canonical name 保留 HKEX 官方繁体名称，`catalog` extra 中的 OpenCC 只生成简体 alias。刷新某一市场失败时保留该市场旧快照；没有对应快照时返回 unavailable，不把“主数据不可用”误报成“公司不存在”。不指定 market 的跨市场识别要求三份快照齐全。LLM 不参与身份确认；ticker exact、官方名称/alias exact 或唯一强模糊匹配以外的情况都返回候选并停止。

整体流程固定为：下载前查索引 → adapter discovery → 带 provider ID 再查索引 → 只写 request staging → SHA/MIME/路径校验 → 下载后再按 SHA 去重 → 新内容原子写入 company raw 并创建 immutable `*.source.json` provenance → 定向重扫与 provider 强身份复验。相同字节已存在时不会创建第二份 canonical 原件；结果仍进入 `acquisition_attempts.jsonl/csv`。

默认没有自动“猜缺什么并批量下载”的任务。revenue-forecast 等上层只能先调用 read-only resolve，并在明确缺口时显式调用 ensure。Pause 状态会拒绝带 `--allow-download` 的 ensure，因此在不希望占用网络/磁盘/浏览器资源时，双击控制中心选择 Pause 即可同时阻止后台处理和统一下载入口。

## 日常后台运行

后台配置位于 `config/source_catalog_worker.yaml`。默认行为：

- 每 60 分钟扫描三个来源根并更新原件索引；
- 普通检查间隔为 30 秒；若本轮实际完成了 Markdown 规范化或 LLM 摘要，下一轮仅等待 `active_poll_interval_seconds`（默认 2 秒），无产出、在电池上、provider 全局失败/退避或周期异常时仍等待 30 秒；
- 单线程每循环最多规范化 1 份、用 LLM 摘要 1 份；可在控制中心随时 pause 或 stop；
- `require_user_idle: true` 可恢复“连续空闲 `idle_seconds_required` 秒后才处理”的兼容模式；
- LLM 或密钥不可用时不生成伪摘要，保留 pending，并在 60 分钟后重试；
- 进程使用低调度优先级，不在电池供电时后处理。

worker 配置 schema 1.2 新增 `active_poll_interval_seconds`。schema 1.0/1.1 仍可加载，并自动令 active interval 等于普通 `poll_interval_seconds`，因此旧配置不会突然加速。自适应等待只改变单线程循环间隔，不改变每轮 batch（仍各1份）、线程数、LLM 模型、失败退避或原始资料。控制中心在 worker 等待时显示 `Next wake`、等待秒数、原因和时间；Pause/Stop 仍由可中断的0.5秒控制检查优先处理。

最方便的入口是直接双击 `scripts/source_catalog_control.cmd`。控制中心会同时显示：登录自启动是否安装、用户意图是 ENABLED 还是 PAUSED、后台进程是否运行、PID、worker 阶段及最近心跳。菜单中的动作语义如下：

- **Pause**：立即结束当前 worker，并把暂停状态持久保存；重启或重新登录后仍不运行，后台不留常驻 worker；
- **Resume**：清除持久暂停并立即隐藏启动；以后登录也会照常自启动；
- **Stop**：只结束当前这一次运行，不改变登录自启动；下次登录会重新启动；
- **Start**：在 ENABLED 状态下立即启动；重复点击不会产生第二个 worker；
- **Browse exact duplicates**：按公司、标题、日期、类型或路径搜索完全相同内容的重复组；canonical 以 `KEEP` 显示且不可操作，只能逐个选择非 canonical 副本移入 Windows 回收站；
- **Refresh status**：只读取很小的控制/状态文件，不打开大索引、不扫描原件。

重复资料界面没有自动清理、全选删除或任意路径输入。用户选中一个编号后，控制中心会显示“要回收的 COPY”和“必须保留的 KEEP”、文件大小与 SHA-256，并要求逐字输入本次确认短语；若副本位于 Dropbox，还会提醒这次移除可能同步到其他设备。真正执行时，Python 服务在 catalog 单写锁内重新计算 duplicate 关系，验证 location ID 仍属配置 root、canonical 与副本都存在且 SHA-256 相同，才调用 Windows 回收站。成功后只把该 location 标为 `missing`，source/document/解析历史继续保留；从回收站恢复文件后，下次扫描会重新标为 active。失败不会把 location 标成 missing。

每次已确认动作会在 `.source_catalog/duplicate_cleanup_events.jsonl` 追加 `requested → recycled/failed` 审计事件，并在下次 export 进入 `duplicate_cleanup_events.csv`。因此后台仍然绝不自动删除资料；唯一例外是用户在控制中心明确选择并确认的 exact-copy 副本。

```powershell
# 安装“登录后启动”的 Windows 计划任务；只安装，不立即运行
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml install-startup

# 查看自启动、持久意图、运行进程和调度进度
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml startup-status
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-status

# 持久暂停（同时结束当前 worker）
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-pause

# 恢复并立即后台启动
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-resume

# 仅停止本次运行，下次登录仍自启动
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-stop

# ENABLED 状态下立即启动；单实例、重复执行安全
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker-start

# 只读列出重复组；日常建议直接使用控制中心菜单 6
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml duplicates --limit 20

# 调试时只运行一个调度循环；它仍遵守电池门控和可选的用户空闲门控
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml worker --once

# 不再需要时移除登录任务
python -m company_wiki.source_catalog.cli --config config/source_catalog.yaml uninstall-startup
```

安装器优先创建 Windows Task Scheduler 的 ONLOGON 任务；若当前用户策略拒绝（例如 `Access is denied`），自动回退到当前用户 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`，并在 worker 注册运行时身份后做两分钟可中断等待。等待期间 Pause/Stop 也会立即生效。两种方式都不会在安装命令执行时立即启动，`startup-status` 会显示实际 method。LLM 密钥只从项目根目录 `.env` 或安全运行环境中的 `MINIMAX_API_KEY` / `MIMO_API_KEY` 读取，不写入 YAML、SQLite、Markdown 或 worker 日志。对这两个托管 key，项目 `.env` 是权威来源：即使 Windows 用户环境中已有旧值，source-catalog worker 也必须用项目 `.env` 覆盖，确保交互启动和下次登录自启动采用同一份配置。

控制层使用独立单实例租约。运行时记录 PID、Python 可执行文件和 Windows 进程创建时间；优雅停止短时间内没有完成时，只有三项身份仍完全匹配才允许强制结束，避免 PID 被复用后误杀其他 Python 程序。worker 在普通或active等待期间都每0.5秒检查控制状态，并每10秒刷新heartbeat；长等待刷新不会丢失当前next-wake计划。Windows偶发占用控制JSON时，原子替换只对`PermissionError`做短暂、有上限重试，持续权限错误仍明确失败。扫描、解析或 LLM 请求属于同步单项操作；Pause/Stop 会先请求安全退出，默认 5 秒后使用上述身份校验终止，因此不会被长 PDF 或网络请求无限拖住。

LLM 摘要 frontmatter 记录 provider、实际 model、prompt version、source/normalized hash、截断标记和 `llm_generated_unverified` 质量状态。响应必须通过固定 JSON Schema 和禁用投资结论检查，否则不落盘。MiniMax/MiMo 均失败时由 worker 延迟重试，不退化成伪装的 LLM 成功。provider 级错误只附加实际 `provider/model` route 供诊断，不记录 key、header 或响应正文中的 secret。

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
